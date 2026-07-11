from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from apps.api.src.config import Settings, get_settings
from apps.api.src.dependencies import get_request_id
from apps.api.src.schemas.common import ErrorCode

router = APIRouter(tags=["Auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/mytasco/v1/auth/login")
async def login(
    body: LoginRequest,
    settings: Settings = Depends(get_settings),
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

    now = datetime.now(timezone.utc)
    payload = {
        "sub": body.username,
        "tenant_id": settings.DEFAULT_TENANT_ID,
        "roles": ["Admin"],
        "departments": ["HR"],
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
            "user": {
                "id": body.username,
                "fullName": body.username,
                "department": "HR",
                "role": "Admin",
                "email": f"{body.username}@demo.local",
            },
        },
    }
