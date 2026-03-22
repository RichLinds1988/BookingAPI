from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db, limiter
from app.models import Booking, Resource
from app.middleware.cache import cache_response, invalidate_cache
from app.utils.pagination import paginate

bookings_bp = Blueprint("bookings", __name__)

# Expected datetime format for all booking times
DATETIME_FMT = "%Y-%m-%dT%H:%M:%S"


def _parse_dt(value: str) -> datetime | None:
    """
    Safely parse a datetime string. Returns None if the format is wrong
    instead of raising an exception that would crash the request.
    The leading underscore means this is a private helper — not a route.
    """
    try:
        return datetime.strptime(value, DATETIME_FMT)
    except (ValueError, TypeError):
        return None


def _has_conflict(resource_id: int, start: datetime, end: datetime, exclude_id: int = None) -> bool:
    """
    Check if a time slot is already taken for a given resource.

    Uses half-open interval logic [start, end) so back-to-back bookings are allowed.
    e.g. a booking ending at 10:00 and one starting at 10:00 do NOT conflict.

    The overlap condition is: existing.start < new.end AND existing.end > new.start
    This catches all overlap cases: partial overlap, full containment, and exact match.
    """
    query = Booking.query.filter(
        Booking.resource_id == resource_id,
        Booking.status == "confirmed",  # Cancelled bookings free up the slot
        Booking.start_time < end,
        Booking.end_time > start,
    )

    # When updating a booking we exclude itself from the conflict check
    if exclude_id:
        query = query.filter(Booking.id != exclude_id)

    # .first() returns the first match or None — more efficient than .all()
    # since we only care whether any conflict exists, not how many
    return query.first() is not None


@bookings_bp.get("")
@jwt_required()
@limiter.limit("60 per minute")
@cache_response(ttl=30, key_prefix="bookings")
def list_bookings():
    # get_jwt_identity() extracts the user ID we stored in the token during login
    # We stored it as a string so we convert back to int for the DB query
    user_id = int(get_jwt_identity())
    query = Booking.query.filter_by(user_id=user_id).order_by(Booking.start_time)
    # paginate() reads ?page=1&per_page=20 from the request and returns a standard envelope
    return jsonify(paginate(query)), 200


@bookings_bp.get("/<int:booking_id>")
@jwt_required()
@limiter.limit("60 per minute")
def get_booking(booking_id):
    user_id = int(get_jwt_identity())
    # Filter by both booking ID and user ID — prevents users from accessing other users' bookings
    booking = Booking.query.filter_by(id=booking_id, user_id=user_id).first_or_404()
    return jsonify(booking.to_dict()), 200


@bookings_bp.post("")
@jwt_required()
@limiter.limit("30 per hour")
def create_booking():
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}

    resource_id = data.get("resource_id")
    start = _parse_dt(data.get("start_time"))
    end = _parse_dt(data.get("end_time"))
    guests = int(data.get("guests", 1))

    # Validate all required fields — _parse_dt returns None for invalid/missing datetimes
    if not all([resource_id, start, end]):
        return jsonify({"error": "resource_id, start_time and end_time are required"}), 422

    if guests < 1:
        return jsonify({"error": "guests must be at least 1"}), 422

    # Prevent bookings in the past
    if start < datetime.now():
        return jsonify({"error": "start_time cannot be in the past"}), 422

    if end <= start:
        return jsonify({"error": "end_time must be after start_time"}), 422

    resource = Resource.query.get_or_404(resource_id)

    # Don't allow bookings on deactivated resources
    if not resource.is_active:
        return jsonify({"error": "Resource is not available"}), 409

    # Validate that the number of guests doesn't exceed the resource's capacity
    if guests > resource.capacity:
        return jsonify({
            "error": f"Number of guests ({guests}) exceeds resource capacity ({resource.capacity})"
        }), 422

    # Check for overlapping bookings before inserting
    if _has_conflict(resource_id, start, end):
        return jsonify({"error": "Resource already booked for that time slot"}), 409

    booking = Booking(
        user_id=user_id,
        resource_id=resource_id,
        start_time=start,
        end_time=end,
        notes=data.get("notes"),
        guests=guests,
    )
    db.session.add(booking)
    db.session.commit()

    # Clear cached booking lists and availability so they reflect the new booking
    invalidate_cache("bookings:*")
    invalidate_cache("availability:*")
    return jsonify(booking.to_dict()), 201


@bookings_bp.delete("/<int:booking_id>")
@jwt_required()
@limiter.limit("30 per hour")
def cancel_booking(booking_id):
    user_id = int(get_jwt_identity())
    booking = Booking.query.filter_by(id=booking_id, user_id=user_id).first_or_404()

    if booking.status == "cancelled":
        return jsonify({"error": "Booking is already cancelled"}), 409

    # Soft delete — mark as cancelled rather than removing the row
    # This preserves history and allows the slot to be rebooked
    booking.status = "cancelled"
    db.session.commit()

    # Clear availability cache so the freed slot shows as available immediately
    invalidate_cache("bookings:*")
    invalidate_cache("availability:*")
    return jsonify(booking.to_dict()), 200


@bookings_bp.get("/availability/<int:resource_id>")
@jwt_required()
@limiter.limit("60 per minute")
@cache_response(ttl=30, key_prefix="availability")
def check_availability(resource_id):
    # Verify the resource exists before checking availability
    Resource.query.get_or_404(resource_id)

    start = _parse_dt(request.args.get("start_time"))
    end = _parse_dt(request.args.get("end_time"))

    if not all([start, end]):
        return jsonify({"error": "start_time and end_time query params required (YYYY-MM-DDTHH:MM:SS)"}), 422

    available = not _has_conflict(resource_id, start, end)
    return jsonify({
        "resource_id": resource_id,
        "available": available,
        "start_time": start.isoformat(),
        "end_time": end.isoformat(),
    }), 200