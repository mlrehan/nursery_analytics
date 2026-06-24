"""Authentication endpoints."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_user, get_user_permissions
from app.core.security import create_access_token, create_refresh_token, decode_token, verify_password
from app.models.auth import User
from app.schemas.auth import LoginRequest, ProfileUpdate, RefreshRequest, Token, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


async def _authenticate(db: AsyncSession, email: str, password: str) -> User:
    user = await db.scalar(
        select(User).where(User.email == email.lower()).options(selectinload(User.role))
    )
    if not user or not verify_password(password, user.hashed_password) or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    user.last_login_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    return user


def _tokens(user: User) -> Token:
    extra = {"role": user.role.slug if user.role else None}
    return Token(
        access_token=create_access_token(str(user.id), extra),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post("/login", response_model=Token)
async def login(form: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)) -> Token:
    """OAuth2 password flow (username field = email). Used by Swagger + frontend."""
    user = await _authenticate(db, form.username, form.password)
    return _tokens(user)


@router.post("/login-json", response_model=Token)
async def login_json(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> Token:
    user = await _authenticate(db, payload.email, payload.password)
    return _tokens(user)


@router.post("/refresh", response_model=Token)
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)) -> Token:
    data = decode_token(payload.refresh_token)
    if not data or data.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    user = await db.scalar(
        select(User).where(User.id == int(data["sub"])).options(selectinload(User.role))
    )
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    return _tokens(user)


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.put("/me/profile", response_model=UserOut)
async def update_profile(
    payload: ProfileUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Any signed-in user can maintain their own profile (contact, address, about, avatar)."""
    data = payload.model_dump(exclude_unset=True)
    if "email" in data and data["email"]:
        data["email"] = data["email"].lower()
        clash = await db.scalar(select(User).where(User.email == data["email"], User.id != user.id))
        if clash:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already in use")
    for field, value in data.items():
        setattr(user, field, value)
    await db.commit()
    await db.refresh(user, attribute_names=["role"])
    return user


@router.get("/me/permissions")
async def my_permissions(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    return {"permissions": sorted(await get_user_permissions(user, db))}
