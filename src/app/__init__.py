from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
import redis as redis_lib

from config import Config

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


def create_app(config_class=Config):
    """
    App factory — creates and configures the Flask application.
    Accepting config_class as an argument lets us pass a TestConfig during tests
    without changing any other code.
    """
    app = Flask(__name__)
    CORS(app)

    # Load all config values from the Config class into app.config
    app.config.from_object(config_class)

    # Connect each extension to this specific app instance
    # Extensions are created above without an app so they can be reused across
    # multiple app instances (important for testing)
    db.init_app(app)
    jwt.init_app(app)
    limiter.init_app(app)

    # Flask-Migrate manages database schema changes via versioned migration files
    # Instead of db.create_all() which can't handle changes to existing tables,
    # Migrate tracks what's changed and generates ALTER TABLE statements
    migrate.init_app(app, db)

    # Create the Redis client from the connection URL
    # decode_responses=True means Redis returns strings instead of raw bytes
    global redis_client
    redis_client = redis_lib.from_url(app.config["REDIS_URL"], decode_responses=True)

    # Store rate limit data in Redis so limits persist across app restarts
    # and work correctly when running multiple instances
    app.config["RATELIMIT_STORAGE_URI"] = app.config["REDIS_URL"]

    # Import blueprints here (inside the function) rather than at the top of the file
    # to avoid circular imports — the routes import db and other globals from this file
    from app.routes.auth import auth_bp
    from app.routes.bookings import bookings_bp
    from app.routes.resources import resources_bp
    from app.routes.health import health_bp

    # Register each blueprint with a URL prefix
    # All routes in auth_bp will be prefixed with /api/auth, etc.
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(bookings_bp, url_prefix="/api/bookings")
    app.register_blueprint(resources_bp, url_prefix="/api/resources")

    # Health check is at the root — no /api prefix so load balancers can reach it
    # without needing auth headers or knowing the API structure
    app.register_blueprint(health_bp)

    _register_error_handlers(app)

    return app


def _register_error_handlers(app):
    """
    Override Flask's default HTML error pages with JSON responses.
    This is important for an API — clients expect JSON, not HTML.
    The leading underscore signals this function is internal to this module.
    """

    @app.errorhandler(404)
    def not_found(e):
        from flask import jsonify
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(429)
    def rate_limited(e):
        from flask import jsonify
        # e.description contains the retry-after information from Flask-Limiter
        return jsonify({"error": "Too many requests", "retry_after": str(e.description)}), 429

    @app.errorhandler(500)
    def server_error(e):
        from flask import jsonify
        return jsonify({"error": "Internal server error"}), 500
