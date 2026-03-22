from flask import request
from typing import Any


# Default and maximum page sizes — enforce a cap so clients can't
# request thousands of records in a single call
DEFAULT_PER_PAGE = 20
MAX_PER_PAGE = 100


def paginate(query, serializer=None) -> dict[str, Any]:
    """
    Apply pagination to a SQLAlchemy query and return a standard envelope.

    Reads 'page' and 'per_page' from the request query string.
    Returns a dict with the paginated items plus metadata so the client
    knows the total number of pages and whether there are more results.

    Usage:
        return jsonify(paginate(Booking.query.filter_by(user_id=user_id)))
    """
    # Clamp per_page between 1 and MAX_PER_PAGE to prevent abuse
    per_page = min(
        int(request.args.get("per_page", DEFAULT_PER_PAGE)),
        MAX_PER_PAGE
    )
    page = max(int(request.args.get("page", 1)), 1)  # page must be >= 1

    # SQLAlchemy's paginate() returns a Pagination object with items + metadata
    # error_out=False returns an empty list instead of 404 for out-of-range pages
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    items = pagination.items
    if serializer:
        items = [serializer(item) for item in items]
    else:
        items = [item.to_dict() for item in items]

    return {
        "items": items,
        "pagination": {
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total": pagination.total,
            "pages": pagination.pages,
            "has_next": pagination.has_next,
            "has_prev": pagination.has_prev,
        }
    }
