from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
)
from app import db, limiter
from app.models import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/register")
@limiter.limit("10 per hour")
def register():
    """
    Register a new user.
    ---
    tags:
      - Auth
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [name, email, password]
            properties:
              name:
                type: string
                example: Rich
              email:
                type: string
                example: rich@example.com
              password:
                type: string
                example: supersecret
    responses:
      201:
        description: User registered successfully — returns access and refresh tokens
      409:
        description: Email already registered
      422:
        description: Validation error
    """
    data = request.get_json(silent=True) or {}

    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not all([name, email, password]):
        return jsonify({"error": "name, email and password are required"}), 422

    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 422

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 409

    user = User(name=name, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    # Issue both tokens on registration so the user is immediately logged in
    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))
    return jsonify({
        "user": user.to_dict(),
        "access_token": access_token,
        "refresh_token": refresh_token,
    }), 201


@auth_bp.post("/login")
@limiter.limit("20 per hour")
def login():
    """
    Login with email and password.
    ---
    tags:
      - Auth
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [email, password]
            properties:
              email:
                type: string
                example: rich@example.com
              password:
                type: string
                example: supersecret
    responses:
      200:
        description: Login successful — returns access and refresh tokens
      401:
        description: Invalid credentials
    """
    data = request.get_json(silent=True) or {}

    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = User.query.filter_by(email=email).first()

    # Deliberately use the same error for wrong email and wrong password
    # to prevent user enumeration attacks
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid email or password"}), 401

    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))
    return jsonify({
        "user": user.to_dict(),
        "access_token": access_token,
        "refresh_token": refresh_token,
    }), 200


@auth_bp.post("/refresh")
@jwt_required(refresh=True)  # This endpoint requires a refresh token, not an access token
@limiter.limit("60 per hour")
def refresh():
    """
    Get a new access token using a refresh token.
    ---
    tags:
      - Auth
    security:
      - Bearer: []
    description: |
      Pass your refresh token in the Authorization header.
      Returns a new short-lived access token without requiring re-login.
    responses:
      200:
        description: New access token issued
      401:
        description: Invalid or expired refresh token
    """
    # get_jwt_identity() works the same way for refresh tokens
    user_id = get_jwt_identity()
    new_access_token = create_access_token(identity=user_id)
    return jsonify({"access_token": new_access_token}), 200


@auth_bp.patch("/users/<int:user_id>/role")
@jwt_required()
@limiter.limit("10 per hour")
def update_user_role(user_id):
    """
    Update a user's role (promote to admin or demote to user).
    ---
    tags:
      - Auth
    security:
      - Bearer: []
    description: Only existing admins can change user roles. The first admin must be set directly in the database.
    parameters:
      - in: path
        name: user_id
        required: true
        schema:
          type: integer
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [role]
            properties:
              role:
                type: string
                enum: [user, admin]
                example: admin
    responses:
      200:
        description: User role updated
      400:
        description: Invalid role
      403:
        description: Only admins can change user roles
      404:
        description: User not found
    """
    from app.models import User

    # Check the requesting user is an admin
    requesting_user_id = int(get_jwt_identity())
    requesting_user = User.query.get(requesting_user_id)
    if not requesting_user or requesting_user.role != "admin":
        return jsonify({"error": "Admin access required"}), 403

    data = request.get_json(silent=True) or {}
    new_role = data.get("role")

    if new_role not in ("user", "admin"):
        return jsonify({"error": "role must be either 'user' or 'admin'"}), 400

    # Prevent admins from accidentally removing their own admin access
    if user_id == requesting_user_id and new_role == "user":
        return jsonify({"error": "You cannot remove your own admin access"}), 400

    target_user = User.query.get_or_404(user_id)
    target_user.role = new_role
    db.session.commit()

    action = "promoted to admin" if new_role == "admin" else "demoted to user"
    return jsonify({"message": f"{target_user.name} {action}", "user": target_user.to_dict()}), 200