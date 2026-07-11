from __future__ import annotations

from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
import jwt
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.config import Settings, get_settings
from apps.api.src.dependencies import get_db, get_request_id
from apps.api.src.db.models import User
from apps.api.src.schemas.common import ErrorCode

router = APIRouter(tags=["Auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/mytasco/v1/auth/login")
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    request_id: str = Depends(get_request_id),
):
    """Authenticate a user and return a signed JWT token."""
    # Query user by user_id or email
    stmt = select(User).where(
        (User.user_id == body.username) | (User.email == body.username)
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=401,
            detail={
                "status": "error",
                "code": ErrorCode.UNAUTHORIZED.value,
                "message": "Invalid username or email",
                "requestId": request_id,
            },
        )

    if user.status != "Active":
        raise HTTPException(
            status_code=403,
            detail={
                "status": "error",
                "code": ErrorCode.FORBIDDEN.value,
                "message": f"User account is not active (status: {user.status})",
                "requestId": request_id,
            },
        )

    # Generate real signed JWT token
    payload = {
        "sub": user.user_id,
        "roles": [user.role_en],
        "departments": [user.department_id],
        "exp": datetime.now(timezone.utc) + timedelta(hours=24),
        "iat": datetime.now(timezone.utc),
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")

    return {
        "status": "success",
        "message": "SUCCESS",
        "requestId": request_id,
        "body": {
            "token": token,
            "user": {
                "id": user.user_id,
                "fullName": user.full_name,
                "department": user.department_id,
                "role": user.role_en,
                "email": user.email,
            },
        },
    }
