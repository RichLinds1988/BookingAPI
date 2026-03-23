from flask import Blueprint, jsonify
from app import db, redis_client
from sqlalchemy import text

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health_check():
    """
    Health check endpoint.
    ---
    tags:
      - Health
    responses:
      200:
        description: All dependencies healthy
        content:
          application/json:
            schema:
              type: object
              properties:
                status:
                  type: string
                  example: ok
                dependencies:
                  type: object
                  properties:
                    database:
                      type: string
                      example: ok
                    redis:
                      type: string
                      example: ok
      503:
        description: One or more dependencies are down
    """
    status = {
        "status": "ok",
        "dependencies": {
            "database": "ok",
            "redis": "ok",
        }
    }
    http_status = 200

    try:
        db.session.execute(text("SELECT 1"))
    except Exception as e:
        status["dependencies"]["database"] = f"error: {str(e)}"
        status["status"] = "degraded"
        http_status = 503

    try:
        redis_client.ping()
    except Exception as e:
        status["dependencies"]["redis"] = f"error: {str(e)}"
        status["status"] = "degraded"
        http_status = 503

    return jsonify(status), http_status
