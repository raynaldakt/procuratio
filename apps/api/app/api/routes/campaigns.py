from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_roles
from app.db.session import get_db
from app.models.user import User
from app.schemas.campaign import (
    CampaignPublic,
    CampaignSendRequest,
    CampaignSendResponse,
    NotificationMarkStatus,
    NotificationMessagePublic,
)
from app.services.campaigns import (
    list_campaigns,
    list_notifications,
    mark_notification_status,
    queue_birthday_offers_today,
    send_campaign_now,
)

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.post("/send", response_model=CampaignSendResponse, status_code=status.HTTP_201_CREATED)
def send_campaign(
    payload: CampaignSendRequest,
    current_user: User = Depends(require_roles("admin", "manager", "staff")),
    db: Session = Depends(get_db),
) -> CampaignSendResponse:
    try:
        campaign, queued = send_campaign_now(
            db,
            name=payload.name,
            channel=payload.channel,
            target_mode=payload.target_mode,
            subject=payload.subject,
            message=payload.message,
            min_points=payload.min_points,
            created_by_user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return CampaignSendResponse(campaign=CampaignPublic.model_validate(campaign), queued_notifications=queued)


@router.get("/", response_model=list[CampaignPublic])
def get_campaigns(
    _: User = Depends(require_roles("admin", "manager", "staff")),
    db: Session = Depends(get_db),
) -> list[CampaignPublic]:
    return [CampaignPublic.model_validate(row) for row in list_campaigns(db)]


@router.post("/birthday/send-today", response_model=CampaignSendResponse, status_code=status.HTTP_201_CREATED)
def send_birthday_today(
    current_user: User = Depends(require_roles("admin", "manager", "staff")),
    db: Session = Depends(get_db),
) -> CampaignSendResponse:
    campaign, queued = queue_birthday_offers_today(
        db,
        created_by_user_id=current_user.id,
        email_subject="Happy Birthday from Seanergy",
        message="Enjoy your birthday offer in our salon this week.",
    )
    return CampaignSendResponse(campaign=CampaignPublic.model_validate(campaign), queued_notifications=queued)


@router.get("/notifications", response_model=list[NotificationMessagePublic])
def get_notifications_queue(
    status_filter: str | None = Query(default=None, alias="status"),
    _: User = Depends(require_roles("admin", "manager", "staff")),
    db: Session = Depends(get_db),
) -> list[NotificationMessagePublic]:
    rows = list_notifications(db, status_filter)
    return [NotificationMessagePublic.model_validate(row) for row in rows]


@router.post("/notifications/{notification_id}/status", response_model=NotificationMessagePublic)
def update_notification_status(
    notification_id: int,
    payload: NotificationMarkStatus,
    _: User = Depends(require_roles("admin", "manager", "staff")),
    db: Session = Depends(get_db),
) -> NotificationMessagePublic:
    row = mark_notification_status(db, notification_id, payload.status, payload.failure_reason)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return NotificationMessagePublic.model_validate(row)
