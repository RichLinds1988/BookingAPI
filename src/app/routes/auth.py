from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.limiter import limiter
from app.models import User
from app.schemas import (
    LoginRequest,
    RegisterRequest,
    UpdateProfileRequest,
    UpdateRoleRequest,
    UserResponse,
)
from app.utils.auth import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    get_refresh_user,
)

router = APIRouter()


@router.post(
    "/register",
    status_code=201,
    responses={
        201: {
            "description": "User registered successfully",
            "content": {
                "application/json": {
                    "example": {
                        "user": {
                            "id": 1,
                            "email": "user@example.com",
                            "name": "John Doe",
                            "role": "user",
                        },
                        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIiwidHlwZSI6ImFjY2VzcyIsImV4cCI6MTYxNjIzOTAyMn0.signature",
                        "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIiwidHlwZSI6InJlZnJlc2giLCJleHAiOjE2MTY4OTUwMjJ9.signature",
                    }
                }
            },
        },
        409: {
            "description": "Email already registered",
            "content": {"application/json": {"example": {"detail": "Email already registered"}}},
        },
        422: {
            "description": "Validation error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["body", "password"],
                                "msg": "password must be at least 8 characters",
                                "type": "value_error",
                            }
                        ]
                    }
                }
            },
        },
    },
)
@limiter.limit("10/hour")
async def register(
    request: Request,
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    email = body.email.strip().lower()
    result = await db.execute(select(User).filter_by(email=email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(name=body.name, email=email)
    user.set_password(body.password)
    db.add(user)
    await db.flush()
    await db.refresh(user)

    return {
        "user": UserResponse(**user.to_dict()),
        "access_token": create_access_token(user.id),
        "refresh_token": create_refresh_token(user.id),
    }


@router.post(
    "/login",
    responses={
        200: {
            "description": "Login successful",
            "content": {
                "application/json": {
                    "example": {
                        "user": {
                            "id": 1,
                            "email": "user@example.com",
                            "name": "John Doe",
                            "role": "user",
                        },
                        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIiwidHlwZSI6ImFjY2VzcyIsImV4cCI6MTYxNjIzOTAyMn0.signature",
                        "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIiwidHlwZSI6InJlZnJlc2giLCJleHAiOjE2MTY4OTUwMjJ9.signature",
                    }
                }
            },
        },
        401: {
            "description": "Invalid email or password",
            "content": {"application/json": {"example": {"detail": "Invalid email or password"}}},
        },
    },
)
@limiter.limit("20/hour")
async def login(
    request: Request,
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    email = body.email.strip().lower()
    result = await db.execute(select(User).filter_by(email=email))
    user = result.scalar_one_or_none()

    # Same error for wrong email and wrong password — prevents user enumeration
    if not user or not user.check_password(body.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return {
        "user": UserResponse(**user.to_dict()),
        "access_token": create_access_token(user.id),
        "refresh_token": create_refresh_token(user.id),
    }


@router.post(
    "/refresh",
    responses={
        200: {
            "description": "New access token generated",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIiwidHlwZSI6ImFjY2VzcyIsImV4cCI6MTYxNjIzOTAyMn0.signature"
                    }
                }
            },
        },
        401: {
            "description": "Invalid or expired refresh token",
            "content": {"application/json": {"example": {"detail": "Invalid token"}}},
        },
    },
)
@limiter.limit("60/hour")
async def refresh(request: Request, current_user: User = Depends(get_refresh_user)):
    return {"access_token": create_access_token(current_user.id)}


@router.patch(
    "/users/{user_id}/role",
    responses={
        200: {
            "description": "User role updated",
            "content": {
                "application/json": {
                    "example": {
                        "message": "User promoted to admin",
                        "user": {
                            "id": 2,
                            "email": "admin@example.com",
                            "name": "Admin User",
                            "role": "admin",
                        },
                    }
                }
            },
        },
        403: {
            "description": "Admin access required",
            "content": {"application/json": {"example": {"detail": "Admin access required"}}},
        },
        404: {
            "description": "User not found",
            "content": {"application/json": {"example": {"detail": "User not found"}}},
        },
    },
)
@limiter.limit("10/hour")
async def update_user_role(
    user_id: int,
    request: Request,
    body: UpdateRoleRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    if user_id == current_user.id and body.role == "user":
        raise HTTPException(status_code=400, detail="You cannot remove your own admin access")

    result = await db.execute(select(User).filter_by(id=user_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    target.role = body.role
    action = "promoted to admin" if body.role == "admin" else "demoted to user"
    return {"message": f"{target.name} {action}", "user": UserResponse(**target.to_dict())}


@router.patch(
    "/me",
    responses={
        200: {
            "description": "Profile updated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "user": {
                            "id": 1,
                            "email": "user@example.com",
                            "name": "Updated Name",
                            "role": "user",
                        }
                    }
                }
            },
        },
        422: {
            "description": "Validation error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["body", "name"],
                                "msg": "name cannot be empty",
                                "type": "value_error",
                            }
                        ]
                    }
                }
            },
        },
    },
)
@limiter.limit("10/hour")
async def update_profile(
    request: Request,
    body: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.name is not None:
        current_user.name = body.name
    if body.password is not None:
        current_user.set_password(body.password)
    await db.flush()
    await db.refresh(current_user)
    return {"user": UserResponse(**current_user.to_dict())}
