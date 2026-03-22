from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app import db, limiter
from app.models import Resource
from app.middleware.cache import cache_response, invalidate_cache
from app.utils.pagination import paginate

resources_bp = Blueprint("resources", __name__)


@resources_bp.get("")
@jwt_required()  # Request must include a valid Authorization: Bearer <token> header
@limiter.limit("60 per minute")
@cache_response(ttl=60, key_prefix="resources")  # Cache for 60 seconds
def list_resources():
    # Only return active resources — deactivated ones are hidden from regular users
    query = Resource.query.filter_by(is_active=True).order_by(Resource.name)
    # paginate() reads ?page=1&per_page=20 from the request and returns a standard envelope
    return jsonify(paginate(query)), 200


@resources_bp.get("/<int:resource_id>")
@jwt_required()
@limiter.limit("60 per minute")
@cache_response(ttl=60, key_prefix="resources")
def get_resource(resource_id):
    # get_or_404 returns the resource if found, or automatically returns a 404 response
    resource = Resource.query.get_or_404(resource_id)
    return jsonify(resource.to_dict()), 200


@resources_bp.post("")
@jwt_required()
@limiter.limit("30 per hour")
def create_resource():
    data = request.get_json(silent=True) or {}

    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 422

    resource = Resource(
        name=name,
        description=data.get("description"),
        capacity=int(data.get("capacity", 1)),
    )
    db.session.add(resource)
    db.session.commit()

    # Invalidate the resource list cache so the new resource shows up immediately
    invalidate_cache("resources:*")
    return jsonify(resource.to_dict()), 201


@resources_bp.patch("/<int:resource_id>")
@jwt_required()
@limiter.limit("30 per hour")
def update_resource(resource_id):
    resource = Resource.query.get_or_404(resource_id)
    data = request.get_json(silent=True) or {}

    # Only update fields that were actually sent in the request
    # This way a PATCH with just {"name": "x"} won't accidentally clear other fields
    if "name" in data:
        resource.name = data["name"].strip()
    if "description" in data:
        resource.description = data["description"]
    if "capacity" in data:
        resource.capacity = int(data["capacity"])
    if "is_active" in data:
        resource.is_active = bool(data["is_active"])

    db.session.commit()
    invalidate_cache("resources:*")
    return jsonify(resource.to_dict()), 200
