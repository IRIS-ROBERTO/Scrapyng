from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DBSession
from app.core.logging import get_logger
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import (
    PasswordChange,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
log = get_logger(__name__)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, db: DBSession) -> User:
    """Create a new user account."""
    # Check for duplicate email
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    existing_username = await db.execute(select(User).where(User.username == payload.username))
    if existing_username.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken")

    user = User(
        email=payload.email,
        username=payload.username,
        hashed_password=get_password_hash(payload.password),
        full_name=payload.full_name,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    log.info("user_registered", user_id=str(user.id), email=user.email)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLogin, db: DBSession) -> dict:
    """Authenticate and return a JWT access token."""
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account deactivated")

    token = create_access_token(subject=str(user.id))
    log.info("user_logged_in", user_id=str(user.id))
    return {"access_token": token, "token_type": "bearer", "user": user}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: CurrentUser) -> User:
    """Return the currently authenticated user."""
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_me(payload: UserUpdate, current_user: CurrentUser, db: DBSession) -> User:
    """Update the currently authenticated user's profile."""
    if payload.full_name is not None:
        current_user.full_name = payload.full_name
    if payload.username is not None:
        existing = await db.execute(
            select(User).where(User.username == payload.username, User.id != current_user.id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken")
        current_user.username = payload.username
    await db.flush()
    await db.refresh(current_user)
    log.info("user_updated", user_id=str(current_user.id))
    return current_user


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def change_password(
    payload: PasswordChange, current_user: CurrentUser, db: DBSession
) -> None:
    """Change the current user's password."""
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Wrong current password")
    current_user.hashed_password = get_password_hash(payload.new_password)
    await db.flush()
    log.info("password_changed", user_id=str(current_user.id))
