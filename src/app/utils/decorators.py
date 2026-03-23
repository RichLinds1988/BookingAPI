from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt_identity
from app.models import User


def admin_required(f):
    """
    Decorator that restricts a route to admin users only.

    Must be used after @jwt_required() since it relies on get_jwt_identity()
    being available. Returns 403 Forbidden if the user is not an admin.

    Usage:
        @route.get("/admin-only")
        @jwt_required()
        @admin_required
        def admin_only_route():
            ...
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)

        # 403 Forbidden means the user is authenticated but not authorized
        # This is different from 401 Unauthorized which means not authenticated at all
        if not user or user.role != "admin":
            return jsonify({"error": "Admin access required"}), 403

        return f(*args, **kwargs)
    return wrapper