from flask import Blueprint, jsonify
from app import db, redis_client
from sqlalchemy import text

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health_check():
    """
    Health check endpoint used by Kubernetes liveness/readiness probes and load balancers.
    Returns the status of each dependency so orchestrators know if the app is healthy.

    Returns 200 if all dependencies are up, 503 if any are down.
    503 (Service Unavailable) is the correct status for a degraded service —
    it tells the load balancer to stop sending traffic to this instance.
    """
    status = {
        "status": "ok",
        "dependencies": {
            "database": "ok",
            "redis": "ok",
        }
    }
    http_status = 200

    # Check database — execute a minimal query that touches the connection pool
    try:
        db.session.execute(text("SELECT 1"))
    except Exception as e:
        status["dependencies"]["database"] = f"error: {str(e)}"
        status["status"] = "degraded"
        http_status = 503

    # Check Redis — ping returns True if the connection is alive
    try:
        redis_client.ping()
    except Exception as e:
        status["dependencies"]["redis"] = f"error: {str(e)}"
        status["status"] = "degraded"
        http_status = 503

    return jsonify(status), http_status
