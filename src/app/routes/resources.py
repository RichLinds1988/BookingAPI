from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app import db, limiter
from app.models import Resource
from app.middleware.cache import cache_response, invalidate_cache
from app.utils.pagination import paginate

resources_bp = Blueprint("resources", __name__)


@resources_bp.get("")
@jwt_required()
@limiter.limit("60 per minute")
@cache_response(ttl=60, key_prefix="resources")
def list_resources():
    """
    List all active resources.
    ---
    tags:
      - Resources
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
        description: Paginated list of resources
      401:
        description: Missing or invalid token
    """
    query = Resource.query.filter_by(is_active=True).order_by(Resource.name)
    return jsonify(paginate(query)), 200


@resources_bp.get("/<int:resource_id>")
@jwt_required()
@limiter.limit("60 per minute")
@cache_response(ttl=60, key_prefix="resources")
def get_resource(resource_id):
    """
    Get a single resource by ID.
    ---
    tags:
      - Resources
    security:
      - Bearer: []
    parameters:
      - in: path
        name: resource_id
        required: true
        schema:
          type: integer
    responses:
      200:
        description: Resource found
      404:
        description: Resource not found
    """
    resource = Resource.query.get_or_404(resource_id)
    return jsonify(resource.to_dict()), 200


@resources_bp.post("")
@jwt_required()
@limiter.limit("30 per hour")
def create_resource():
    """
    Create a new bookable resource.
    ---
    tags:
      - Resources
    security:
      - Bearer: []
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [name]
            properties:
              name:
                type: string
                example: Boardroom A
              description:
                type: string
                example: 10-person boardroom with projector
              capacity:
                type: integer
                example: 10
    responses:
      201:
        description: Resource created
      422:
        description: Validation error
    """
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

    invalidate_cache("resources:*")
    return jsonify(resource.to_dict()), 201


@resources_bp.patch("/<int:resource_id>")
@jwt_required()
@limiter.limit("30 per hour")
def update_resource(resource_id):
    """
    Update a resource.
    ---
    tags:
      - Resources
    security:
      - Bearer: []
    parameters:
      - in: path
        name: resource_id
        required: true
        schema:
          type: integer
    requestBody:
      content:
        application/json:
          schema:
            type: object
            properties:
              name:
                type: string
              description:
                type: string
              capacity:
                type: integer
              is_active:
                type: boolean
    responses:
      200:
        description: Resource updated
      404:
        description: Resource not found
    """
    resource = Resource.query.get_or_404(resource_id)
    data = request.get_json(silent=True) or {}

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
