from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from app import db, limiter
from app.models import User

# A Blueprint groups related routes together — similar to a controller in Symfony
# The first argument is the blueprint's name, used internally by Flask
auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/register")
@limiter.limit("10 per hour")  # Prevent brute force account creation
def register():
    # get_json(silent=True) returns None instead of raising an error if the body isn't valid JSON
    # "or {}" ensures we always have a dict to work with even if the body is empty
    data = request.get_json(silent=True) or {}

    # .strip() removes leading/trailing whitespace
    # .lower() normalises the email so "Rich@Example.COM" and "rich@example.com" are treated the same
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    # Validate all required fields are present
    if not all([name, email, password]):
        return jsonify({"error": "name, email and password are required"}), 422

    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 422

    # Check for duplicate email before attempting to insert
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 409

    user = User(name=name, email=email)
    user.set_password(password)  # Hashes the password before storing
    db.session.add(user)
    db.session.commit()

    # Issue a JWT token immediately after registration so the user is logged in right away
    # identity must be a string — we store the user ID as the token subject
    token = create_access_token(identity=str(user.id))
    return jsonify({"user": user.to_dict(), "access_token": token}), 201


@auth_bp.post("/login")
@limiter.limit("20 per hour")  # Prevent brute force login attempts
def login():
    data = request.get_json(silent=True) or {}

    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    # Look up the user by email — returns None if not found
    user = User.query.filter_by(email=email).first()

    # Deliberately use the same error message for both wrong email and wrong password
    # Separate messages would reveal which emails are registered (user enumeration attack)
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid email or password"}), 401

    token = create_access_token(identity=str(user.id))
    return jsonify({"user": user.to_dict(), "access_token": token}), 200
