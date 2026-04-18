import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # asyncpg driver for async SQLAlchemy — psycopg2 stays in requirements for alembic migrations
    DATABASE_URL = (
        f"postgresql+asyncpg://{os.getenv('DB_USER', 'booking_user')}:"
        f"{os.getenv('DB_PASSWORD', '')}@"
        f"{os.getenv('DB_HOST', 'localhost')}:"
        f"{os.getenv('DB_PORT', '5432')}/"
        f"{os.getenv('DB_NAME', 'booking_db')}"
    )

    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CACHE_TTL = 300

    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret")
    JWT_ALGORITHM = "HS256"
    # Stored as plain ints (seconds) — PyJWT doesn't use timedelta
    JWT_ACCESS_TOKEN_EXPIRES: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", 3600))
    JWT_REFRESH_TOKEN_EXPIRES: int = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRES_DAYS", 7)) * 86400
