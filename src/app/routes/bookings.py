from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db, limiter
from app.models import Booking, Resource
from app.middleware.cache import cache_response, invalidate_cache
from app.utils.pagination import paginate

bookings_bp = Blueprint("bookings", __name__)

DATETIME_FMT = "%Y-%m-%dT%H:%M:%S"


def _parse_dt(value: str) -> datetime | None:
    """
    Safely parse a datetime string. Returns None if the format is wrong
    instead of raising an exception that would crash the request.
    """
    try:
        return datetime.strptime(value, DATETIME_FMT)
    except (ValueError, TypeError):
        return None


def _has_conflict(resource_id: int, start: datetime, end: datetime, exclude_id: int = None) -> bool:
    """
    Check if a time slot is already taken for a given resource.
    Uses half-open interval logic [start, end) so back-to-back bookings are allowed.
    """
    query = Booking.query.filter(
        Booking.resource_id == resource_id,
        Booking.status == "confirmed",
        Booking.start_time < end,
        Booking.end_time > start,
    )
    if exclude_id:
        query = query.filter(Booking.id != exclude_id)
    return query.first() is not None


@bookings_bp.get("")
@jwt_required()
@limiter.limit("60 per minute")
@cache_response(ttl=30, key_prefix="bookings")
def list_bookings():
    """
    List the current user's bookings.
    ---
    tags:
      - Bookings
    security:
      - Bearer: []
    parameters:
      - in: query
        name: page
        schema:
          type: integer
          default: 1
      - in: query
        name: per_page
        schema:
          type: integer
          default: 20
    responses:
      200:
        description: Paginated list of bookings
      401:
        description: Missing or invalid token
    """
    user_id = int(get_jwt_identity())
    query = Booking.query.filter_by(user_id=user_id).order_by(Booking.start_time)
    return jsonify(paginate(query)), 200


@bookings_bp.get("/<int:booking_id>")
@jwt_required()
@limiter.limit("60 per minute")
def get_booking(booking_id):
    """
    Get a single booking by ID.
    ---
    tags:
      - Bookings
    security:
      - Bearer: []
    parameters:
      - in: path
        name: booking_id
        required: true
        schema:
          type: integer
    responses:
      200:
        description: Booking found
      404:
        description: Booking not found
    """
    user_id = int(get_jwt_identity())
    booking = Booking.query.filter_by(id=booking_id, user_id=user_id).first_or_404()
    return jsonify(booking.to_dict()), 200


@bookings_bp.post("")
@jwt_required()
@limiter.limit("30 per hour")
def create_booking():
    """
    Create a new booking.
    ---
    tags:
      - Bookings
    security:
      - Bearer: []
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [resource_id, start_time, end_time]
            properties:
              resource_id:
                type: integer
                example: 1
              start_time:
                type: string
                example: "2026-06-01T09:00:00"
              end_time:
                type: string
                example: "2026-06-01T10:00:00"
              guests:
                type: integer
                example: 5
              notes:
                type: string
                example: Team standup
    responses:
      201:
        description: Booking confirmed
      409:
        description: Time slot already booked or resource unavailable
      422:
        description: Validation error
    """
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}

    resource_id = data.get("resource_id")
    start = _parse_dt(data.get("start_time"))
    end = _parse_dt(data.get("end_time"))
    guests = int(data.get("guests", 1))

    if not all([resource_id, start, end]):
        return jsonify({"error": "resource_id, start_time and end_time are required"}), 422

    if guests < 1:
        return jsonify({"error": "guests must be at least 1"}), 422

    if start < datetime.now():
        return jsonify({"error": "start_time cannot be in the past"}), 422

    if end <= start:
        return jsonify({"error": "end_time must be after start_time"}), 422

    resource = Resource.query.get_or_404(resource_id)

    if not resource.is_active:
        return jsonify({"error": "Resource is not available"}), 409

    if guests > resource.capacity:
        return jsonify({
            "error": f"Number of guests ({guests}) exceeds resource capacity ({resource.capacity})"
        }), 422

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

    invalidate_cache("bookings:*")
    invalidate_cache("availability:*")
    return jsonify(booking.to_dict()), 201


@bookings_bp.delete("/<int:booking_id>")
@jwt_required()
@limiter.limit("30 per hour")
def cancel_booking(booking_id):
    """
    Cancel a booking.
    ---
    tags:
      - Bookings
    security:
      - Bearer: []
    parameters:
      - in: path
        name: booking_id
        required: true
        schema:
          type: integer
    responses:
      200:
        description: Booking cancelled
      409:
        description: Booking is already cancelled
      404:
        description: Booking not found
    """
    user_id = int(get_jwt_identity())
    booking = Booking.query.filter_by(id=booking_id, user_id=user_id).first_or_404()

    if booking.status == "cancelled":
        return jsonify({"error": "Booking is already cancelled"}), 409

    booking.status = "cancelled"
    db.session.commit()

    invalidate_cache("bookings:*")
    invalidate_cache("availability:*")
    return jsonify(booking.to_dict()), 200


@bookings_bp.get("/availability/<int:resource_id>")
@jwt_required()
@limiter.limit("60 per minute")
@cache_response(ttl=30, key_prefix="availability")
def check_availability(resource_id):
    """
    Check if a resource is available for a given time slot.
    ---
    tags:
      - Bookings
    security:
      - Bearer: []
    parameters:
      - in: path
        name: resource_id
        required: true
        schema:
          type: integer
      - in: query
        name: start_time
        required: true
        schema:
          type: string
        example: "2026-06-01T09:00:00"
      - in: query
        name: end_time
        required: true
        schema:
          type: string
        example: "2026-06-01T10:00:00"
    responses:
      200:
        description: Availability status
      422:
        description: Missing query params
      404:
        description: Resource not found
    """
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
