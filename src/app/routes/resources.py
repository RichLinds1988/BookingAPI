from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import cache
from app.database import get_db
from app.limiter import limiter
from app.models import Resource, User
from app.schemas import CreateResourceRequest, ResourceResponse, UpdateResourceRequest
from app.utils.auth import get_current_user
from app.utils.dependencies import require_admin
from app.utils.pagination import paginate

router = APIRouter()


@router.get(
    "",
    responses={
        200: {
            "description": "List of active resources",
            "content": {
                "application/json": {
                    "example": {
                        "items": [
                            {
                                "id": 1,
                                "name": "Conference Room A",
                                "description": "Large conference room with video conferencing",
                                "capacity": 20,
                                "is_active": True,
                            }
                        ],
                        "total": 1,
                        "page": 1,
                        "per_page": 20,
                        "pages": 1,
                    }
                }
            },
        },
        401: {
            "description": "Not authenticated",
            "content": {"application/json": {"example": {"detail": "Not authenticated"}}},
        },
    },
)
@limiter.limit("60/minute")
@cache.cache_response(ttl=60, key_prefix="resources")
async def list_resources(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Resource).filter_by(is_active=True).order_by(Resource.name)
    return await paginate(stmt, db, page=page, per_page=per_page)


@router.get(
    "/{resource_id}",
    responses={
        200: {
            "description": "Resource details",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "name": "Conference Room A",
                        "description": "Large conference room with video conferencing",
                        "capacity": 20,
                        "is_active": True,
                    }
                }
            },
        },
        404: {
            "description": "Resource not found",
            "content": {"application/json": {"example": {"detail": "Resource not found"}}},
        },
    },
)
@limiter.limit("60/minute")
@cache.cache_response(ttl=60, key_prefix="resources")
async def get_resource(
    resource_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Resource).filter_by(id=resource_id))
    resource = result.scalar_one_or_none()
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    return ResourceResponse(**resource.to_dict())


@router.post(
    "",
    status_code=201,
    responses={
        201: {
            "description": "Resource created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "name": "Conference Room A",
                        "description": "Large conference room with video conferencing",
                        "capacity": 20,
                        "is_active": True,
                    }
                }
            },
        },
        403: {
            "description": "Admin access required",
            "content": {"application/json": {"example": {"detail": "Admin access required"}}},
        },
    },
)
@limiter.limit("30/hour")
async def create_resource(
    request: Request,
    body: CreateResourceRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    resource = Resource(name=body.name, description=body.description, capacity=body.capacity)
    db.add(resource)
    await db.flush()
    await db.refresh(resource)

    await cache.invalidate_cache("resources:*")
    return ResourceResponse(**resource.to_dict())


@router.patch(
    "/{resource_id}",
    responses={
        200: {
            "description": "Resource updated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "name": "Conference Room A (Updated)",
                        "description": "Large conference room with video conferencing",
                        "capacity": 25,
                        "is_active": True,
                    }
                }
            },
        },
        403: {
            "description": "Admin access required",
            "content": {"application/json": {"example": {"detail": "Admin access required"}}},
        },
        404: {
            "description": "Resource not found",
            "content": {"application/json": {"example": {"detail": "Resource not found"}}},
        },
    },
)
@limiter.limit("30/hour")
async def update_resource(
    resource_id: int,
    request: Request,
    body: UpdateResourceRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Resource).filter_by(id=resource_id))
    resource = result.scalar_one_or_none()
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    if body.name is not None:
        resource.name = body.name.strip()
    if body.description is not None:
        resource.description = body.description
    if body.capacity is not None:
        resource.capacity = body.capacity
    if body.is_active is not None:
        resource.is_active = body.is_active

    await cache.invalidate_cache("resources:*")
    return ResourceResponse(**resource.to_dict())
