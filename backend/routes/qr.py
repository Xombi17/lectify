"""QR code generation, validation, and analytics endpoints."""
import io
from typing import List, Optional

import qrcode
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from qrcode.image.svg import SvgImage

from core.config import get_settings
from core.deps import get_current_user, require_teacher, require_teacher_or_admin
from core.rate_limiter import InMemoryRateLimiter
from models.academic import (
    QRAnalytics,
    QRCodeCreate,
    QRCodeDB,
    QRCodePublic,
)
from models.user import UserPublic
from repositories.class_repository import ClassRepository
from repositories.qr_code_repository import QRCodeRepository
from repositories.student_enrollment_repository import StudentEnrollmentRepository
from repositories.teacher_assignment_repository import TeacherAssignmentRepository
from services.storage_service import get_storage

settings = get_settings()
router = APIRouter(prefix="/qr", tags=["qr"])

# Per-process in-memory rate limiter (replace with Redis in Phase 5)
_limiter = InMemoryRateLimiter()


async def rate_limit_enroll(request: Request) -> None:
    """Rate limit enrollment-related endpoints per IP."""
    ip = request.client.host if request.client else "unknown"
    allowed = await _limiter.check(f"enroll:{ip}", 10, 60)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests",
            headers={"Retry-After": "60"},
        )


async def rate_limit_qr_generate(request: Request) -> None:
    """Rate limit QR generation/regeneration per user."""
    ip = request.client.host if request.client else "unknown"
    allowed = await _limiter.check(f"qr-gen:{ip}", 5, 60)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many QR generation requests",
            headers={"Retry-After": "60"},
        )


async def rate_limit_qr_scan(request: Request) -> None:
    """Rate limit QR scan endpoints per IP."""
    ip = request.client.host if request.client else "unknown"
    allowed = await _limiter.check(f"qr-scan:{ip}", 5, 60)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests",
            headers={"Retry-After": "60"},
        )


def _to_public(qr: QRCodeDB) -> QRCodePublic:
    """Convert QRCodeDB to QRCodePublic, resolving storage URLs."""
    svg_url = f"{settings.STORAGE_PUBLIC_BASE}/{qr.svg_key}"
    png_url = f"{settings.STORAGE_PUBLIC_BASE}/{qr.png_key}" if qr.png_key else None
    return QRCodePublic(
        id=qr.id,
        class_id=qr.class_id,
        svg_url=svg_url,
        png_url=png_url,
        scan_count=qr.scan_count,
        enrollment_count=qr.enrollment_count,
        is_active=qr.is_active,
        generated_at=qr.generated_at,
    )


def _compute_conversion_rate(scan_count: int, enrollment_count: int) -> float:
    """Compute conversion rate from scan count and enrollment count."""
    if scan_count == 0:
        return 0.0
    return round(enrollment_count / scan_count, 4)


def _app_base_url(request: Request) -> str:
    """Public URL students open. Explicit APP_URL wins; otherwise the browser's own origin, so a
    QR generated on the deployed site never points at localhost."""
    configured = (settings.APP_URL or "").rstrip("/")
    if configured:
        return configured
    origin = request.headers.get("origin")
    if origin:
        return origin.rstrip("/")
    host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme
    return f"{proto}://{host}" if host else "http://localhost:3000"


async def _assert_can_manage_class(class_id: str, user: UserPublic) -> None:
    """Class must exist; non-admins must hold an active assignment to it."""
    if not await ClassRepository().get_by_id(class_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class not found")
    if user.role != "admin":
        assignments = await TeacherAssignmentRepository().list_for_teacher(user.id)
        if class_id not in {a.class_id for a in assignments if a.active}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Teacher not assigned to this class",
            )


async def _create_qr_internal(class_id: str, user_id: str, base_url: str) -> QRCodePublic:
    """Internal helper to generate a QR code for a class. Does not verify permissions."""
    import uuid

    token_secret = str(uuid.uuid4())

    # Create enrollment URL
    from core.security import create_enrollment_token
    jwt_token = create_enrollment_token(class_id, token_secret)
    enrollment_url = f"{base_url}/enroll?token={jwt_token}"

    # Generate SVG QR code
    qr_img = qrcode.make(enrollment_url, image_factory=SvgImage)
    svg_buffer = io.BytesIO()
    qr_img.save(svg_buffer)
    svg_buffer.seek(0)

    # Create QR code DB record
    qr_repo = QRCodeRepository()
    qr_id = qr_repo.new_id()
    # Under classes/ so the API role (scoped to classes/*) can write and stream it
    svg_key = f"classes/{class_id}/qr/{qr_id}.svg"

    # Upload SVG to storage service
    storage = get_storage()
    await storage.save(svg_key, svg_buffer, "image/svg+xml")

    qr_db = QRCodeDB(
        id=qr_id,
        class_id=class_id,
        token_secret=token_secret,
        svg_key=svg_key,
        is_active=True,
        generated_by=user_id,
    )
    created = await qr_repo.create(qr_db)
    return _to_public(created)


@router.post(
    "/classes/{class_id}/generate",
    response_model=QRCodePublic,
    status_code=status.HTTP_201_CREATED,
)
async def generate_qr(
    class_id: str,
    request: Request,
    user: UserPublic = Depends(require_teacher_or_admin),
    _ = Depends(rate_limit_qr_generate),
):
    """Generate a QR code for a class. Requires teacher role and class assignment."""
    from core.deps import AUDIT_GENERATE_QR, log_audit

    # Verify class exists
    cls = await ClassRepository().get_by_id(class_id)
    if not cls:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Class not found",
        )

    # Verify teacher is assigned to this class (admins can bypass)
    if user.role != "admin":
        ta_repo = TeacherAssignmentRepository()
        assignments = await ta_repo.list_for_teacher(user.id)
        class_ids = {a.class_id for a in assignments if a.active}
        if class_id not in class_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Teacher not assigned to this class",
            )

    # If an active QR already exists for this class, deactivate it before creating a new one
    qr_repo = QRCodeRepository()
    current = await qr_repo.get_active_for_class(class_id)
    if current:
        await qr_repo.deactivate(current.id)

    qr_result = await _create_qr_internal(class_id, user.id, _app_base_url(request))

    await log_audit(
        action=AUDIT_GENERATE_QR,
        entity_type="qr_code",
        entity_id=qr_result.id,
        details=f"Generated QR code for class: {class_id}",
        admin_id=user.id,
    )

    return qr_result


@router.post(
    "/classes/{class_id}/regenerate",
    response_model=QRCodePublic,
    status_code=status.HTTP_201_CREATED,
)
async def regenerate_qr(
    class_id: str,
    request: Request,
    user: UserPublic = Depends(require_teacher_or_admin),
    _ = Depends(rate_limit_qr_generate),
):
    """Regenerate QR code for a class. Deactivates the old QR and creates a new one."""
    await _assert_can_manage_class(class_id, user)
    qr_repo = QRCodeRepository()

    # Deactivate current active QR
    current = await qr_repo.get_active_for_class(class_id)
    if current:
        await qr_repo.deactivate(current.id)

    # Generate new QR
    return await _create_qr_internal(class_id, user.id, _app_base_url(request))


@router.get(
    "/classes/{class_id}",
    response_model=QRCodePublic,
)
async def get_qr(
    class_id: str,
    user: UserPublic = Depends(require_teacher_or_admin),
):
    """Get the latest active QR code for a class."""
    # Verify teacher assignment for non-admin
    if user.role != "admin":
        ta_repo = TeacherAssignmentRepository()
        assignments = await ta_repo.list_for_teacher(user.id)
        class_ids = {a.class_id for a in assignments if a.active}
        if class_id not in class_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Teacher not assigned to this class",
            )

    qr_repo = QRCodeRepository()
    qr = await qr_repo.get_active_for_class(class_id)
    if not qr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No QR code found for this class",
        )
    return _to_public(qr)


@router.get(
    "/classes/{class_id}/download",
)
async def download_qr(
    class_id: str,
    fmt: str = Query("svg", pattern="^(svg|png)$"),
    user: UserPublic = Depends(require_teacher_or_admin),
):
    """Download QR code image for a class."""
    # Verify teacher assignment
    if user.role != "admin":
        ta_repo = TeacherAssignmentRepository()
        assignments = await ta_repo.list_for_teacher(user.id)
        class_ids = {a.class_id for a in assignments if a.active}
        if class_id not in class_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Teacher not assigned to this class",
            )

    qr_repo = QRCodeRepository()
    qr = await qr_repo.get_active_for_class(class_id)
    if not qr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No QR code found for this class",
        )

    storage = get_storage()
    if fmt == "png" and not qr.png_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PNG format not available for this QR code",
        )
    key = qr.svg_key if fmt == "svg" else qr.png_key
    iterator, content_length, content_type = await storage.stream(key)
    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        iterator,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="qr-{class_id}.{fmt}"',
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@router.get(
    "/classes/{class_id}/analytics",
    response_model=QRAnalytics,
)
async def qr_analytics(
    class_id: str,
    days: Optional[int] = Query(None, ge=1, le=365),
    user: UserPublic = Depends(require_teacher_or_admin),
):
    """Get QR analytics for a class."""
    # Verify teacher assignment
    if user.role != "admin":
        ta_repo = TeacherAssignmentRepository()
        assignments = await ta_repo.list_for_teacher(user.id)
        class_ids = {a.class_id for a in assignments if a.active}
        if class_id not in class_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Teacher not assigned to this class",
            )

    qr_repo = QRCodeRepository()
    qr = await qr_repo.get_active_for_class(class_id)
    if not qr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No QR code found for this class",
        )

    conversion_rate = _compute_conversion_rate(qr.scan_count, qr.enrollment_count)

    analytics = QRAnalytics(
        qr_id=qr.id,
        class_id=qr.class_id,
        scan_count=qr.scan_count,
        enrollment_count=qr.enrollment_count,
        conversion_rate=conversion_rate,
        generated_at=qr.generated_at,
        is_active=qr.is_active,
    )

    # If days param provided, include daily breakdown
    if days:
        analytics.scan_count_per_day = qr.scan_count // days
        analytics.enrollment_count_per_day = qr.enrollment_count // days

    return analytics


@router.get(
    "/classes/{class_id}/history",
    response_model=List[QRCodePublic],
)
async def qr_history(
    class_id: str,
    user: UserPublic = Depends(require_teacher_or_admin),
):
    """Get QR code history for a class (all generations)."""
    # Verify teacher assignment
    if user.role != "admin":
        ta_repo = TeacherAssignmentRepository()
        assignments = await ta_repo.list_for_teacher(user.id)
        class_ids = {a.class_id for a in assignments if a.active}
        if class_id not in class_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Teacher not assigned to this class",
            )

    qr_repo = QRCodeRepository()
    qrs = await qr_repo.list_for_class(class_id)
    return [_to_public(qr) for qr in qrs]


# ============================================================================
# Public Enrollment via QR Token
# ============================================================================


@router.get("/enroll/{token}")
async def enroll_via_qr(
    token: str,
    _ = Depends(rate_limit_qr_scan),
):
    """Validate an enrollment token and return enrollment info.

    This is a public endpoint — no auth required. It validates the JWT,
    checks the QR is still active, increments scan count, and returns
    a redirect URL for the frontend.
    """
    from core.security import decode_enrollment_token

    # Decode and validate token
    payload = decode_enrollment_token(token)
    class_id = payload["sub"]
    qr_secret = payload["qr_secret"]

    # Verify QR code exists and is active
    qr_repo = QRCodeRepository()
    qr = await qr_repo.get_active_for_class(class_id)
    if not qr or qr.token_secret != qr_secret or not qr.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="QR code expired or regenerated",
        )

    # Increment scan count
    await qr_repo.increment_scan(qr.id)

    cls = await ClassRepository().get_by_id(class_id)
    return {
        "valid": True,
        "class_id": class_id,
        "class_name": cls.name if cls and cls.name else "this class",
        "redirect_url": f"/enroll?token={token}",
    }


@router.post("/enroll/{token}")
async def enroll_via_qr_post(
    token: str,
    user: UserPublic = Depends(get_current_user),
    _ = Depends(rate_limit_enroll),
):
    """Validate an enrollment token and enroll the current user.

    Authenticated version — validates the JWT, checks QR is active,
    then enrolls the student in the class.
    """
    from core.security import decode_enrollment_token

    if user.role != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only student accounts can enroll in a class",
        )

    # Decode and validate token
    payload = decode_enrollment_token(token)
    class_id = payload["sub"]
    qr_secret = payload["qr_secret"]

    # Verify QR code exists and is active
    qr_repo = QRCodeRepository()
    qr = await qr_repo.get_active_for_class(class_id)
    if not qr or qr.token_secret != qr_secret or not qr.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="QR code expired or regenerated",
        )

    # Increment scan count
    await qr_repo.increment_scan(qr.id)

    # Check for existing enrollment
    se_repo = StudentEnrollmentRepository()
    existing = await se_repo.find_existing(class_id, user.id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Already enrolled in this class",
        )

    # Create enrollment
    from models.academic import StudentEnrollmentDB
    enrollment = StudentEnrollmentDB(
        id=se_repo.new_id(),
        class_id=class_id,
        student_id=user.id,
    )
    created = await se_repo.create(enrollment)

    # Increment enrollment count on QR (non-critical — enrollment already succeeded)
    try:
        await qr_repo.increment_enrollment(qr.id)
    except Exception:
        pass

    return {
        "valid": True,
        "class_id": class_id,
        "enrollment_id": created.id,
    }
