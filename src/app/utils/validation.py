import os


def validate_environment() -> None:
    """Validate required environment variables at startup."""
    required_vars = [
        "DB_USER",
        "DB_PASSWORD",
        "DB_HOST",
        "DB_PORT",
        "DB_NAME",
        "REDIS_URL",
        "JWT_SECRET_KEY",
    ]

    missing = [var for var in required_vars if not os.getenv(var)]

    if missing:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}. "
            f"Please set them or provide a .env file."
        )
