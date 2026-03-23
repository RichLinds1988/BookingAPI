import os
from datetime import timedelta
from dotenv import load_dotenv

# Load values from the .env file into environment variables
# This must be called before any os.getenv() calls
load_dotenv()


class Config:
    # Used by Flask to sign session cookies — should be a long random string in production
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")

    # SQLAlchemy connection string — built from individual env vars
    # Format: driver://user:password@host:port/database
    # postgresql+psycopg2 tells SQLAlchemy to use Postgres with the psycopg2 driver
    SQLALCHEMY_DATABASE_URI = (
        f"postgresql+psycopg2://{os.getenv('DB_USER', 'booking_user')}:"
        f"{os.getenv('DB_PASSWORD', '')}@"
        f"{os.getenv('DB_HOST', 'localhost')}:"
        f"{os.getenv('DB_PORT', '5432')}/"
        f"{os.getenv('DB_NAME', 'booking_db')}"
    )

    # Disables a deprecated SQLAlchemy feature that watches for object changes
    # Always set this to False — it adds overhead and will be removed in a future version
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Redis connection URL — the /0 at the end refers to Redis database index 0
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # How long cached responses live in Redis before expiring (in seconds)
    CACHE_TTL = 300  # 5 minutes

    # Secret used to sign JWT tokens — different from SECRET_KEY intentionally
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret")

    # How long a JWT token is valid before the user needs to log in again
    # os.getenv always returns a string so we convert to int before passing to timedelta
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(seconds=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", 3600)))

    # Refresh tokens live much longer than access tokens — 7 days by default
    # When the access token expires, the client uses the refresh token to get a new one
    # without requiring the user to log in again
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=int(os.getenv("JWT_REFRESH_TOKEN_EXPIRES_DAYS", 7)))