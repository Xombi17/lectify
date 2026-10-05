"""FastAPI dependency providers."""
from datetime import datetime, timezone
from typing import List, Optional

import jwt as jwt_lib
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt import PyJWTError

from core.security import decode_access_token
from models.user import UserPublic
from repositories.lecture_repository import LectureRepository
from repositories.student_enrollment_repository import StudentEnrollmentRepository
from repositories.teacher_assignment_repository import TeacherAssignmentRepository
from repositories.user_repository import UserRepository


# ── Audit action constants ─────────────────────────────────────
AUDIT_CREATE = "create"
AUDIT_UPDATE = "update"
AUDIT_DELETE = "delete"
AUDIT_PUBLISH = "publish"
AUDIT_UNPUBLISH = "unpublish"
AUDIT_GENERATE_QR = "generate"
AUDIT_ASSIGN_TEACHER = "assign_teacher"
AUDIT_UNASSIGN_TEACHER = "unassign_teacher"


# ── Audit logging helper ──────────────────────────────────────────────


async def log_audit(
    action: str,
    entity_type: str,
    entity_id: str,
    details: Optional[str] = None,
    admin_id: Optional[str] = None,
) -> None:
    """Record an audit log entry.

    Args:
        action: One of "create", "update", "delete", "publish", "unpublish", "generate"
        entity_type: The type of entity (e.g., "institution", "lecture", "qr_code")
        entity_id: The ID of the entity
        details: Optional human-readable details about the action
        admin_id: The admin who performed the action. If None, extracted from context.
    """
    from repositories.audit_log_repository import AuditLogRepository
    from models.academic import AuditLogDB

    repo = AuditLogRepository()
    entry = AuditLogDB(
        id=repo.new_id(),
        admin_id=admin_id or "system",
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
    )
    await repo.create(entry)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=True)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserPublic:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    from core.config import get_settings
    settings = get_settings()

    if settings.SERVICE_NAME == "interaction":
        import httpx
        try:
            async with httpx.AsyncClient() as client:
                headers = {"Authorization": f"Bearer {token}"}
                response = await client.get("http://auth-service:8001/api/auth/me", headers=headers, timeout=5.0)
                if response.status_code == 200:
                    return UserPublic(**response.json())
                else:
                    raise credentials_exc
        except Exception:
            raise credentials_exc

    try:
        payload = decode_access_token(token)
        user_id: str = payload.get("sub")
        jti: str = payload.get("jti")
        if not user_id:
            raise credentials_exc

        # Check blacklist
        if jti:
            from repositories.token_repository import TokenRepository
            repo = TokenRepository()
            if await repo.is_blacklisted(jti):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked",
                    headers={"WWW-Authenticate": "Bearer"},
                )
    except PyJWTError:
        raise credentials_exc

    repo = UserRepository()
    user = await repo.get_by_id(user_id)
    if user is None:
        raise credentials_exc
    return UserPublic(**user.model_dump(exclude={"password_hash"}))


async def extract_token_data(token: str = Depends(oauth2_scheme)) -> dict:
    """Extract raw JWT payload without requiring a valid user (for logout).

    Used before get_current_user to capture jti/exp before the token is consumed.
    Allows expired tokens through so they can still be blacklisted.
    """
    try:
        return decode_access_token(token)
    except jwt_lib.ExpiredSignatureError:
        # Allow expired tokens so the jti can be extracted for blacklisting
        from core.config import get_settings
        settings = get_settings()
        return jwt_lib.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_exp": False},
        )
    except PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


def require_teacher(user: UserPublic = Depends(get_current_user)) -> UserPublic:
    if user.role != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teacher role required",
        )
    return user


def require_admin(user: UserPublic = Depends(get_current_user)) -> UserPublic:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return user


def require_teacher_or_admin(user: UserPublic = Depends(get_current_user)) -> UserPublic:
    if user.role not in ("teacher", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teacher or admin role required",
        )
    return user


def require_student(user: UserPublic = Depends(get_current_user)) -> UserPublic:
    """Require student role for student-only endpoints."""
    if user.role != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student role required",
        )
    return user


def require_role(*roles: str):
    """Factory: returns a dependency that requires one of the given roles."""
    async def _check(user: UserPublic = Depends(get_current_user)) -> UserPublic:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of {roles} roles required",
            )
        return user
    return _check


async def get_admin_user(admin: UserPublic = Depends(require_admin)) -> UserPublic:
    """Require admin and return the admin user (for audit logging)."""
    return admin


async def verify_lecture_access(
    lecture_id: str,
    user: UserPublic = Depends(get_current_user),
):
    """Verify user can access a lecture with class-scoped fail-closed security.

    - Admin: granted full access.
    - Teacher: granted if owner or has active assignment to lecture.class_id. Else 403 Forbidden.
    - Student:
      - If lecture is not published: 404 Not Found (fail-closed).
      - If lecture.class_id is set: student must have active enrollment in that class;
        if not enrolled: 404 Not Found (fail-closed, prevents resource enumeration).
    """
    repo = LectureRepository()
    lecture = await repo.get_by_id(lecture_id)
    if not lecture:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lecture not found")

    if user.role == "admin":
        return lecture

    if user.role == "teacher":
        if lecture.teacher_id == user.id:
            return lecture
        if lecture.class_id:
            ta_repo = TeacherAssignmentRepository()
            assignment = await ta_repo.find_existing(lecture.class_id, user.id, active_only=True)
            if assignment:
                return lecture
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    if user.role == "student":
        if not lecture.published:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lecture not found")
        if lecture.class_id:
            se_repo = StudentEnrollmentRepository()
            enrollment = await se_repo.find_existing(lecture.class_id, user.id)
            if not enrollment:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lecture not found")
        return lecture

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


async def can_access_lecture(
    lecture_id: str,
    user: UserPublic = Depends(get_current_user),
):
    """Verify user can access a lecture. Delegates to verify_lecture_access."""
    return await verify_lecture_access(lecture_id, user)
