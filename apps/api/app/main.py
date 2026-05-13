from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.appointments import router as appointments_router
from app.api.routes.auth import router as auth_router
from app.api.routes.campaigns import router as campaigns_router
from app.api.routes.customers import router as customers_router
from app.api.routes.gifts import router as gifts_router
from app.api.routes.health import router as health_router
from app.api.routes.loyalty import router as loyalty_router
from app.api.routes.sales import router as sales_router
from app.api.routes.shop import router as shop_router
from app.api.routes.stats import router as stats_router
from app.api.routes.users import router as users_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
)

raw_origins = settings.cors_allow_origins.strip()
if raw_origins == "*":
    allow_origins = ["*"]
else:
    allow_origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins or ["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
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
app.include_router(campaigns_router)
app.include_router(sales_router)
app.include_router(shop_router)
app.include_router(gifts_router)
app.include_router(stats_router)
app.include_router(users_router)
app.include_router(customers_router)
app.include_router(loyalty_router)
