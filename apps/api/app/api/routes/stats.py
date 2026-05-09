from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_roles
from app.db.session import get_db
from app.models.user import User
from app.schemas.stats import StatsOverview, StatsPeriod, StatsTimeseries
from app.services.stats import get_overview, get_timeseries

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/overview", response_model=StatsOverview)
def overview(
    period: StatsPeriod = Query(default="month"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    _: User = Depends(require_roles("admin", "manager", "staff")),
    db: Session = Depends(get_db),
) -> StatsOverview:
    if (date_from and not date_to) or (date_to and not date_from):
        raise HTTPException(status_code=422, detail="date_from and date_to must be provided together")
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=422, detail="date_from must be before date_to")

    return get_overview(db, period=period, date_from=date_from, date_to=date_to)


@router.get("/timeseries", response_model=StatsTimeseries)
def timeseries(
    period: StatsPeriod = Query(default="month"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    _: User = Depends(require_roles("admin", "manager", "staff")),
    db: Session = Depends(get_db),
) -> StatsTimeseries:
    if (date_from and not date_to) or (date_to and not date_from):
        raise HTTPException(status_code=422, detail="date_from and date_to must be provided together")
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=422, detail="date_from must be before date_to")

    return get_timeseries(db, period=period, date_from=date_from, date_to=date_to)
