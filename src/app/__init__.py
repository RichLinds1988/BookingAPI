from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from flask_cors import CORS
from flasgger import Swagger
import redis as redis_lib

from config import Config
from app.utils.logging import configure_logging
from app.middleware.request_logger import register_request_logging

# These are created at module level so other files can import them directly
# e.g. "from app import db" in models.py
# They are not connected to any app yet — that happens in create_app() via init_app()
db = SQLAlchemy()
jwt = JWTManager()
migrate = Migrate()

# Rate limiter — get_remote_address means limits are tracked per IP address
limiter = Limiter(key_func=get_remote_address)

# Redis client — starts as None, assigned in create_app()
# The type hint tells editors and type checkers what type this will eventually be
redis_client: redis_lib.Redis = None

# Swagger UI configuration
# Accessible at /apidocs when the app is running
SWAGGER_CONFIG = {
    "headers": [],
    "specs": [
        {
            "endpoint": "apispec",
            "route": "/apispec.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/apidocs",
    "info": {
        "title": "Booking API",
        "description": "A RESTful booking API with JWT auth, Redis caching, and rate limiting.",
        "version": "1.0.0",
        "contact": {
            "name": "RichLinds1988",
            "url": "https://github.com/RichLinds1988/BookingAPI",
        },
    },
    "securityDefinitions": {
        # Tell Swagger UI how to pass the JWT token
        # Users can click 'Authorize' and enter their token once for all requests
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "Enter: Bearer <your_token>",
        }
    },
    "security": [{"Bearer": []}],
}


def create_app(config_class=Config):
    """
    App factory — creates and configures the Flask application.
    Accepting config_class as an argument lets us pass a TestConfig during tests
    without changing any other code.
    """
    app = Flask(__name__)

    # Load all config values from the Config class into app.config
    app.config.from_object(config_class)

    # Allow cross-origin requests from the frontend
    CORS(app)

    # Configure structured JSON logging — replaces Flask default plain text logs
    configure_logging(app)

    # Register before/after request hooks that log every HTTP request
    register_request_logging(app)

    # Connect each extension to this specific app instance
    db.init_app(app)
    jwt.init_app(app)
    limiter.init_app(app)
    migrate.init_app(app, db)

    # Initialize Swagger UI — serves interactive API docs at /apidocs
    Swagger(app, config=SWAGGER_CONFIG, merge=True)

    # Create the Redis client from the connection URL
    # decode_responses=True means Redis returns strings instead of raw bytes
    global redis_client
    redis_client = redis_lib.from_url(app.config["REDIS_URL"], decode_responses=True)

    # Store rate limit data in Redis so limits persist across app restarts
    app.config["RATELIMIT_STORAGE_URI"] = app.config["REDIS_URL"]

    # Import blueprints here (inside the function) rather than at the top of the file
    # to avoid circular imports — the routes import db and other globals from this file
    from app.routes.auth import auth_bp
    from app.routes.bookings import bookings_bp
    from app.routes.resources import resources_bp
    from app.routes.health import health_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(bookings_bp, url_prefix="/api/bookings")
    app.register_blueprint(resources_bp, url_prefix="/api/resources")

    # Health check is at the root — no /api prefix so load balancers can reach it
    app.register_blueprint(health_bp)

    _register_error_handlers(app)

    return app


def _register_error_handlers(app):
    """
    Override Flask's default HTML error pages with JSON responses.
    This is important for an API — clients expect JSON, not HTML.
    """

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
