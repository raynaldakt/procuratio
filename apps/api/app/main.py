from fastapi import FastAPI

from app.api.routes.appointments import router as appointments_router
from app.api.routes.auth import router as auth_router
from app.api.routes.customers import router as customers_router
from app.api.routes.health import router as health_router
from app.api.routes.loyalty import router as loyalty_router
from app.api.routes.users import router as users_router
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
app.include_router(auth_router)
app.include_router(appointments_router)
app.include_router(users_router)
app.include_router(customers_router)
app.include_router(loyalty_router)
