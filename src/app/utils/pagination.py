from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

DEFAULT_PER_PAGE = 20
MAX_PER_PAGE = 100


async def paginate(
    stmt, db: AsyncSession, page: int = 1, per_page: int = DEFAULT_PER_PAGE
) -> dict[str, Any]:
    """
    Execute a SELECT statement with pagination and return a standard envelope.

    Usage:
        stmt = select(Booking).filter_by(user_id=user_id).order_by(Booking.start_time)
        return await paginate(stmt, db, page=page, per_page=per_page)
    """
    per_page = min(per_page, MAX_PER_PAGE)
    page = max(page, 1)

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()

    result = await db.execute(stmt.offset((page - 1) * per_page).limit(per_page))
    items = result.scalars().all()

    pages = max((total + per_page - 1) // per_page, 1)

    return {
        "items": [item.to_dict() for item in items],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": pages,
            "has_next": page < pages,
            "has_prev": page > 1,
        },
    }
