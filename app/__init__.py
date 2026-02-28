from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import redis as redis_lib

from config import Config

db = SQLAlchemy()
jwt = JWTManager()
limiter = Limiter(key_func=get_remote_address)

# Shared Redis client
redis_client: redis_lib.Redis = None


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Extensions
    db.init_app(app)
    jwt.init_app(app)
    limiter.init_app(app)

    # Redis
    global redis_client
    redis_client = redis_lib.from_url(app.config["REDIS_URL"], decode_responses=True)

    # Rate limiter storage — use Redis so limits survive restarts
    app.config["RATELIMIT_STORAGE_URI"] = app.config["REDIS_URL"]

    # Blueprints
    from app.routes.auth import auth_bp
    from app.routes.bookings import bookings_bp
    from app.routes.resources import resources_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(bookings_bp, url_prefix="/api/bookings")
    app.register_blueprint(resources_bp, url_prefix="/api/resources")

    # Create tables
    with app.app_context():
        db.create_all()

    return app


def _register_error_handlers(app):
    @app.errorhandler(404)
    def not_found(e):
        from flask import jsonify
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(429)
    def rate_limited(e):
        from flask import jsonify
        return jsonify({"error": "Too many requests", "retry_after": str(e.description)}), 429

    @app.errorhandler(500)
    def server_error(e):
        from flask import jsonify
        return jsonify({"error": "Internal server error"}), 500
