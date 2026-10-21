"""Auth routes — signup, login, /me, logout, refresh."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from core.deps import extract_token_data, get_current_user
from core.security import (
    create_access_token,
    decode_reset_token,
    hash_password,
    password_fingerprint,
    verify_password,
)
from models.user import (
    AuthResponse,
    PasswordChange,
    PasswordReset,
    ProfileUpdate,
    UserCreate,
    UserDB,
    UserLogin,
    UserPublic,
)
from repositories.user_repository import UserRepository

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(payload: UserCreate):
    # Public signup creates students only; teacher/admin accounts are created by an admin.
    if payload.role != "student":
        raise HTTPException(status_code=403, detail="Role not permitted for public signup")

    repo = UserRepository()
    existing = await repo.get_by_email(payload.email.lower())
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = UserDB(
        id=repo.new_id(),
        name=payload.name.strip(),
        email=payload.email.lower(),
        role=payload.role,
        password_hash=hash_password(payload.password),
    )
    await repo.create(user)
    token = create_access_token(subject=user.id, role=user.role)
    return AuthResponse(access_token=token, user=UserPublic(**user.model_dump(exclude={"password_hash"})))


@router.post("/login", response_model=AuthResponse)
async def login(payload: UserLogin):
    repo = UserRepository()
    user = await repo.get_by_email(payload.email.lower())
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token(subject=user.id, role=user.role)
    return AuthResponse(access_token=token, user=UserPublic(**user.model_dump(exclude={"password_hash"})))


@router.get("/me", response_model=UserPublic)
async def me(user: UserPublic = Depends(get_current_user)):
    return user


@router.patch("/me", response_model=UserPublic)
async def update_profile(payload: ProfileUpdate, user: UserPublic = Depends(get_current_user)):
    updated = await UserRepository().update_name(user.id, payload.name.strip())
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    return UserPublic(**updated.model_dump(exclude={"password_hash"}))


async def _blacklist(token_data: dict) -> None:
    from repositories.token_repository import TokenRepository

    jti, exp = token_data.get("jti"), token_data.get("exp")
    if jti and exp:
        await TokenRepository().blacklist_token(jti, datetime.fromtimestamp(exp, tz=timezone.utc))


@router.post("/change-password", response_model=AuthResponse)
async def change_password(
    payload: PasswordChange,
    token_data: dict = Depends(extract_token_data),
    user: UserPublic = Depends(get_current_user),
):
    """Change own password. Revokes the current token and returns a fresh one."""
    repo = UserRepository()
    db_user = await repo.get_by_id(user.id)
    if not db_user or not verify_password(payload.current_password, db_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if payload.new_password == payload.current_password:
        raise HTTPException(status_code=400, detail="New password must differ from the current one")
    await repo.update_password_hash(user.id, hash_password(payload.new_password))
    await _blacklist(token_data)
    return AuthResponse(access_token=create_access_token(subject=user.id, role=user.role), user=user)


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(payload: PasswordReset):
    """Set a new password using an admin-issued reset link (single use: it dies when the password changes)."""
    claims = decode_reset_token(payload.token)
    repo = UserRepository()
    db_user = await repo.get_by_id(claims["sub"])
    if not db_user or claims.get("pf") != password_fingerprint(db_user.password_hash):
        raise HTTPException(status_code=400, detail="Reset link is no longer valid")
    await repo.update_password_hash(db_user.id, hash_password(payload.new_password))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    token_data: dict = Depends(extract_token_data),
    user: UserPublic = Depends(get_current_user),
):
    """Logout: blacklist the current JWT so it can't be reused."""
    from repositories.token_repository import TokenRepository

    repo = TokenRepository()
    jti = token_data.get("jti")
    exp = token_data.get("exp")
    if jti and exp:
        expires_at = datetime.fromtimestamp(exp, tz=timezone.utc)
        await repo.blacklist_token(jti, expires_at)


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(
    token_data: dict = Depends(extract_token_data),
    user: UserPublic = Depends(get_current_user),
):
    """Refresh the current token: blacklist the old one, issue a new one."""
    from repositories.token_repository import TokenRepository

    repo = TokenRepository()
    jti = token_data.get("jti")
    exp = token_data.get("exp")
    if jti and exp:
        expires_at = datetime.fromtimestamp(exp, tz=timezone.utc)
        await repo.blacklist_token(jti, expires_at)

    new_token = create_access_token(subject=user.id, role=user.role)
    return AuthResponse(access_token=new_token, user=user)
