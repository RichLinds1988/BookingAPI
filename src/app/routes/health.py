from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app import cache
from app.database import get_db

router = APIRouter()


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    status: dict[str, Any] = {"status": "ok", "dependencies": {"database": "ok", "redis": "ok"}}
    http_status = 200

    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        status["dependencies"]["database"] = f"error: {e}"
        status["status"] = "degraded"
        http_status = 503

    try:
        if cache.redis_client is None:
            raise RuntimeError("Redis client not initialized")
        await cache.redis_client.ping()
    except Exception as e:
        status["dependencies"]["redis"] = f"error: {e}"
        status["status"] = "degraded"
        http_status = 503

    if http_status != 200:
        return JSONResponse(status_code=503, content=status)
    return status
