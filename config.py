import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Flask
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")

    # MySQL via SQLAlchemy
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{os.getenv('MYSQL_USER', 'root')}:"
        f"{os.getenv('MYSQL_PASSWORD', '')}@"
        f"{os.getenv('MYSQL_HOST', 'localhost')}:"
        f"{os.getenv('MYSQL_PORT', '3306')}/"
        f"{os.getenv('MYSQL_DB', 'booking_db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Redis
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CACHE_TTL = 300  # seconds

    # JWT
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(seconds=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", 3600)))
