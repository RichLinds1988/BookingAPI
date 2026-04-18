from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import cache
from app.database import get_db
from app.limiter import limiter
from app.models import Booking, Resource, User
from app.schemas import BookingResponse, CreateBookingRequest
from app.utils.auth import get_current_user
from app.utils.pagination import paginate

router = APIRouter()


async def _has_conflict(
    db: AsyncSession,
    resource_id: int,
    start: datetime,
    end: datetime,
    exclude_id: int | None = None,
) -> bool:
    """Half-open interval [start, end) — back-to-back bookings are allowed."""
    stmt = select(Booking).filter(
        Booking.resource_id == resource_id,
        Booking.status == "confirmed",
        Booking.start_time < end,
        Booking.end_time > start,
    )
    if exclude_id:
        stmt = stmt.filter(Booking.id != exclude_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


@router.get("")
@limiter.limit("60/minute")
@cache.cache_response(ttl=30, key_prefix="bookings")
async def list_bookings(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Booking).filter_by(user_id=current_user.id).order_by(Booking.start_time)
    return await paginate(stmt, db, page=page, per_page=per_page)


@router.get("", responses={
    200: {
        "description": "List of user's bookings",
        "content": {
            "application/json": {
                "example": {
                    "items": [
                        {
                            "id": 1,
                            "user_id": 1,
                            "resource_id": 1,
                            "resource_name": "Conference Room A",
                            "start_time": "2023-10-01T10:00:00",
                            "end_time": "2023-10-01T11:00:00",
                            "notes": "Team meeting",
                            "guests": 5,
                            "status": "confirmed",
                            "created_at": "2023-09-30T15:00:00"
                        }
                    ],
                    "total": 1,
                    "page": 1,
                    "per_page": 20,
                    "pages": 1
                }
            }
        }
    },
    401: {
        "description": "Not authenticated",
        "content": {
            "application/json": {
                "example": {"detail": "Not authenticated"}
            }
        }
    }
})
@router.get("/availability/{resource_id}", responses={
    200: {
        "description": "Availability check result",
        "content": {
            "application/json": {
                "example": {
                    "resource_id": 1,
                    "available": True,
                    "start_time": "2023-10-01T10:00:00",
                    "end_time": "2023-10-01T11:00:00"
                }
            }
        }
    },
    404: {
        "description": "Resource not found",
        "content": {
            "application/json": {
                "example": {"detail": "Resource not found"}
            }
        }
    },
    422: {
        "description": "Invalid datetime format",
        "content": {
            "application/json": {
                "example": {"detail": "Invalid datetime format, use YYYY-MM-DDTHH:MM:SS"}
            }
        }
    }
})
@limiter.limit("60/minute")
@cache.cache_response(ttl=30, key_prefix="availability")
async def check_availability(
    resource_id: int,
    request: Request,
    start_time: str = Query(...),
    end_time: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Resource).filter_by(id=resource_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Resource not found")

    try:
        start = datetime.fromisoformat(start_time)
        end = datetime.fromisoformat(end_time)
    except ValueError as err:
        raise HTTPException(
            status_code=422, detail="Invalid datetime format, use YYYY-MM-DDTHH:MM:SS"
        ) from err

    available = not await _has_conflict(db, resource_id, start, end)
    return {
        "resource_id": resource_id,
        "available": available,
        "start_time": start.isoformat(),
        "end_time": end.isoformat(),
    }


@router.get("/{booking_id}", responses={
    200: {
        "description": "Booking details",
        "content": {
            "application/json": {
                "example": {
                    "id": 1,
                    "user_id": 1,
                    "resource_id": 1,
                    "resource_name": "Conference Room A",
                    "start_time": "2023-10-01T10:00:00",
                    "end_time": "2023-10-01T11:00:00",
                    "notes": "Team meeting",
                    "guests": 5,
                    "status": "confirmed",
                    "created_at": "2023-09-30T15:00:00"
                }
            }
        }
    },
    404: {
        "description": "Booking not found",
        "content": {
            "application/json": {
                "example": {"detail": "Booking not found"}
            }
        }
    }
})
@limiter.limit("60/minute")
async def get_booking(
    booking_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Booking).filter_by(id=booking_id, user_id=current_user.id))
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return BookingResponse(**booking.to_dict())


@router.post("", status_code=201, responses={
    201: {
        "description": "Booking created successfully",
        "content": {
            "application/json": {
                "example": {
                    "id": 1,
                    "user_id": 1,
                    "resource_id": 1,
                    "resource_name": "Conference Room A",
                    "start_time": "2023-10-01T10:00:00",
                    "end_time": "2023-10-01T11:00:00",
                    "notes": "Team meeting",
                    "guests": 5,
                    "status": "confirmed",
                    "created_at": "2023-09-30T15:00:00"
                }
            }
        }
    },
    409: {
        "description": "Resource already booked or unavailable",
        "content": {
            "application/json": {
                "example": {"detail": "Resource already booked for that time slot"}
            }
        }
    },
    422: {
        "description": "Validation error",
        "content": {
            "application/json": {
                "example": {"detail": [{"loc": ["body", "guests"], "msg": "guests must be at least 1", "type": "value_error"}]}
            }
        }
    }
})
async def create_booking(
    request: Request,
    body: CreateBookingRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Resource).filter_by(id=body.resource_id))
    resource = result.scalar_one_or_none()
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    if not resource.is_active:
        raise HTTPException(status_code=409, detail="Resource is not available")

    if body.guests > resource.capacity:
        raise HTTPException(
            status_code=422,
            detail=f"Number of guests ({body.guests}) exceeds resource capacity ({resource.capacity})",
        )

    if await _has_conflict(db, body.resource_id, body.start_time, body.end_time):
        raise HTTPException(status_code=409, detail="Resource already booked for that time slot")

    booking = Booking(
        user_id=current_user.id,
        resource_id=body.resource_id,
        start_time=body.start_time,
        end_time=body.end_time,
        notes=body.notes,
        guests=body.guests,
    )
    db.add(booking)
    await db.flush()
    await db.refresh(booking)

    await cache.invalidate_cache("bookings:*")
    await cache.invalidate_cache("availability:*")
    return BookingResponse(**booking.to_dict())


@router.delete("/{booking_id}", responses={
    200: {
        "description": "Booking cancelled successfully",
        "content": {
            "application/json": {
                "example": {
                    "id": 1,
                    "user_id": 1,
                    "resource_id": 1,
                    "resource_name": "Conference Room A",
                    "start_time": "2023-10-01T10:00:00",
                    "end_time": "2023-10-01T11:00:00",
                    "notes": "Team meeting",
                    "guests": 5,
                    "status": "cancelled",
                    "created_at": "2023-09-30T15:00:00"
                }
            }
        }
    },
    404: {
        "description": "Booking not found",
        "content": {
            "application/json": {
                "example": {"detail": "Booking not found"}
            }
        }
    },
    409: {
        "description": "Booking already cancelled",
        "content": {
            "application/json": {
                "example": {"detail": "Booking is already cancelled"}
            }
        }
    }
})
@limiter.limit("30/hour")
async def cancel_booking(
    booking_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Booking).filter_by(id=booking_id, user_id=current_user.id))
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking.status == "cancelled":
        raise HTTPException(status_code=409, detail="Booking is already cancelled")

    booking.status = "cancelled"

    await cache.invalidate_cache("bookings:*")
    await cache.invalidate_cache("availability:*")
    return BookingResponse(**booking.to_dict())