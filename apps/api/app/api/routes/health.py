from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.services.health import check_database, check_redis

router = APIRouter(tags=["health"])


@router.get("/health")
def healthcheck() -> JSONResponse:
    db_ok, db_detail = check_database()
    redis_ok, redis_detail = check_redis()

    services = {
        "database": {"ok": db_ok, "detail": db_detail},
        "redis": {"ok": redis_ok, "detail": redis_detail},
    }
    all_ok = all(service["ok"] for service in services.values())

    payload = {
        "status": "ok" if all_ok else "degraded",
        "services": services,
    }

    return JSONResponse(
        status_code=status.HTTP_200_OK if all_ok else status.HTTP_503_SERVICE_UNAVAILABLE,
        content=payload,
    )
