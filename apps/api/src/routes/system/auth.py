from __future__ import annotations

from datetime import datetime, timedelta, timezone

import hashlib
import jwt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from apps.api.src.config import Settings, get_settings
from apps.api.src.schemas.common import ErrorCode
from sqlalchemy import select
from apps.api.src.db.models import User
from apps.api.src.dependencies import get_db, get_request_id

router = APIRouter(tags=["Auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


def verify_password(stored_password: str, provided_password: str) -> bool:
    try:
        salt_hex, key_hex = stored_password.split(":")
        salt = bytes.fromhex(salt_hex)
        key = bytes.fromhex(key_hex)
        new_key = hashlib.pbkdf2_hmac(
            'sha256',
            provided_password.encode('utf-8'),
            salt,
            100000
        )
        return new_key == key
    except Exception:
        return False


@router.post("/mytasco/v1/auth/login")
async def login(
    body: LoginRequest,
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
):
    """Issue a local demo JWT for the AIE1 claim-based identity model."""
    if not body.username or not body.password:
        raise HTTPException(
            status_code=401,
            detail={
                "status": "error",
                "code": ErrorCode.UNAUTHORIZED.value,
                "message": "Username and password are required",
                "requestId": request_id,
            },
        )

    # Query the user using ORM model
    stmt = select(User).where((User.user_id == body.username) | (User.email == body.username))
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if user:
        if not verify_password(user.password, body.password):
            raise HTTPException(
                status_code=401,
                detail={
                    "status": "error",
                    "code": ErrorCode.UNAUTHORIZED.value,
                    "message": "Mật khẩu không chính xác.",
                    "requestId": request_id,
                },
            )
        sub = user.user_id
        roles = [user.role_en]
        departments = [user.department_id]
        user_data = {
            "id": user.user_id,
            "fullName": user.full_name,
            "department": user.department_id,
            "role": user.role_en,
            "email": user.email,
        }
    else:
        # Fallback for mock/test credentials (e.g. admin/admin)
        if body.username == "admin" and body.password == "admin":
            sub = "admin"
            roles = ["Admin"]
            departments = ["HR"]
            user_data = {
                "id": "admin",
                "fullName": "Administrator",
                "department": "HR",
                "role": "Admin",
                "email": "admin@demo.local",
            }
        else:
            raise HTTPException(
                status_code=401,
                detail={
                    "status": "error",
                    "code": ErrorCode.UNAUTHORIZED.value,
                    "message": "Tài khoản không tồn tại.",
                    "requestId": request_id,
                },
            )

    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "tenant_id": settings.DEFAULT_TENANT_ID,
        "roles": roles,
        "departments": departments,
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "iat": now,
        "exp": now + timedelta(hours=24),
        "policy_version": "v1",
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

    return {
        "status": "success",
        "message": "SUCCESS",
        "requestId": request_id,
        "body": {
            "token": token,
            "user": user_data,
        },
    }
