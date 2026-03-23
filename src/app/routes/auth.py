from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from app import db, limiter
from app.models import User

# A Blueprint groups related routes together — similar to a controller in Symfony
# The first argument is the blueprint's name, used internally by Flask
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
        description: User registered successfully
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

    token = create_access_token(identity=str(user.id))
    return jsonify({"user": user.to_dict(), "access_token": token}), 201


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
        description: Login successful, returns JWT token
      401:
        description: Invalid credentials
    """
    data = request.get_json(silent=True) or {}

    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = User.query.filter_by(email=email).first()

    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid email or password"}), 401

    token = create_access_token(identity=str(user.id))
    return jsonify({"user": user.to_dict(), "access_token": token}), 200
