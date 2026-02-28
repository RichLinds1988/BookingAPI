from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from app import db, limiter
from app.models import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/register")
@limiter.limit("10 per hour")
def register():
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
    data = request.get_json(silent=True) or {}

    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid email or password"}), 401

    token = create_access_token(identity=str(user.id))
    return jsonify({"user": user.to_dict(), "access_token": token}), 200
