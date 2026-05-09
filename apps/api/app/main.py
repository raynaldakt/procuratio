from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.get("/", tags=["meta"])
def root() -> dict[str, str]:
    return {
        "message": "Procuratio API is running",
        "environment": settings.app_env,
    }


app.include_router(health_router)
