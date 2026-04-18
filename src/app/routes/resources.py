from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import cache
from app.database import get_db
from app.limiter import limiter
from app.models import Resource
from app.schemas import CreateResourceRequest, ResourceResponse, UpdateResourceRequest
from app.utils.auth import get_current_user
from app.utils.dependencies import require_admin
from app.utils.pagination import paginate

router = APIRouter()


@router.get("")
@limiter.limit("60/minute")
@cache.cache_response(ttl=60, key_prefix="resources")
async def list_resources(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Resource).filter_by(is_active=True).order_by(Resource.name)
    return await paginate(stmt, db, page=page, per_page=per_page)


@router.get("/{resource_id}")
@limiter.limit("60/minute")
@cache.cache_response(ttl=60, key_prefix="resources")
async def get_resource(
    resource_id: int,
    request: Request,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Resource).filter_by(id=resource_id))
    resource = result.scalar_one_or_none()
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    return ResourceResponse(**resource.to_dict())


@router.post("", status_code=201)
@limiter.limit("30/hour")
async def create_resource(
    request: Request,
    body: CreateResourceRequest,
    current_user=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    resource = Resource(name=body.name, description=body.description, capacity=body.capacity)
    db.add(resource)
    await db.flush()
    await db.refresh(resource)

    await cache.invalidate_cache("resources:*")
    return ResourceResponse(**resource.to_dict())


@router.patch("/{resource_id}")
@limiter.limit("30/hour")
async def update_resource(
    resource_id: int,
    request: Request,
    body: UpdateResourceRequest,
    current_user=Depends(require_admin),
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