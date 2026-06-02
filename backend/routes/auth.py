"""Auth routes — signup, login, /me."""
from fastapi import APIRouter, Depends, HTTPException, status

from core.deps import get_current_user
from core.security import create_access_token, hash_password, verify_password
from models.user import AuthResponse, UserCreate, UserDB, UserLogin, UserPublic
from repositories.user_repository import UserRepository

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(payload: UserCreate):
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
