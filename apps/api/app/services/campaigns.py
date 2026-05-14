from datetime import date, datetime, timezone
from threading import Lock

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import engine
from app.models.customer_profile import CustomerProfile
from app.models.marketing_campaign import MarketingCampaign
from app.models.notification_message import NotificationMessage
from app.models.user import User
from app.services.customer import ensure_customer_schema

_schema_lock = Lock()
_schema_ready = False


def _twilio_is_configured() -> bool:
    settings = get_settings()
    return bool(settings.twilio_account_sid and settings.twilio_auth_token and settings.twilio_from)


def ensure_campaigns_schema() -> None:
    global _schema_ready
    if _schema_ready:
        return

    ensure_customer_schema()
    with _schema_lock:
        if _schema_ready:
            return
        Base.metadata.create_all(
            bind=engine,
            tables=[MarketingCampaign.__table__, NotificationMessage.__table__],
            checkfirst=True,
        )
        _schema_ready = True


def _target_user_ids(
    db: Session,
    target_mode: str,
    min_points: int | None,
    today: date | None = None,
) -> list[int]:
    ensure_campaigns_schema()

    stmt = (
        select(User.id)
        .join(CustomerProfile, CustomerProfile.user_id == User.id)
        .where(User.role == "customer", User.is_active.is_(True))
    )

    if target_mode == "email_opt_in":
        stmt = stmt.where(CustomerProfile.marketing_email_opt_in.is_(True))
    elif target_mode == "sms_opt_in":
        stmt = stmt.where(CustomerProfile.marketing_sms_opt_in.is_(True))
    elif target_mode == "birthday_today":
        day = today or date.today()
        stmt = stmt.where(CustomerProfile.birthdate.is_not(None))
        rows = db.execute(stmt).all()
        return [
            user_id
            for (user_id,) in rows
            if (profile := db.get(CustomerProfile, user_id)) is not None
            and profile.birthdate is not None
            and profile.birthdate.month == day.month
            and profile.birthdate.day == day.day
        ]
    elif target_mode == "min_points":
        if min_points is None:
            raise ValueError("min_points is required for this target mode")
        stmt = stmt.where(CustomerProfile.points_balance >= min_points)
    elif target_mode == "all_customers":
        pass
    else:
        raise ValueError("Unsupported target mode")

    rows = db.execute(stmt).all()
    return [user_id for (user_id,) in rows]


def send_campaign_now(
    db: Session,
    *,
    name: str,
    channel: str,
    target_mode: str,
    subject: str | None,
    message: str,
    min_points: int | None,
    created_by_user_id: int,
) -> tuple[MarketingCampaign, int]:
    ensure_campaigns_schema()

    if channel in {"email", "both"} and not subject:
        raise ValueError("subject is required for email channel")
    if channel in {"sms", "both"} and not _twilio_is_configured():
        raise ValueError("SMS channel is not available: Twilio is not configured")

    user_ids = _target_user_ids(db, target_mode, min_points)

    campaign = MarketingCampaign(
        name=name,
        channel=channel,
        target_mode=target_mode,
        subject=subject,
        message=message,
        min_points=min_points,
        status="queued",
        queued_count=0,
        created_by_user_id=created_by_user_id,
        launched_at=datetime.now(timezone.utc),
    )
    db.add(campaign)
    db.flush()

    queued_count = 0
    now = datetime.now(timezone.utc)
    for user_id in user_ids:
        channels = [channel] if channel in {"email", "sms"} else ["email", "sms"]
        for c in channels:
            db.add(
                NotificationMessage(
                    campaign_id=campaign.id,
                    user_id=user_id,
                    channel=c,
                    kind="campaign",
                    subject=subject if c == "email" else None,
                    message=message,
                    status="pending",
                    scheduled_for=now,
                )
            )
            queued_count += 1

    campaign.queued_count = queued_count
    campaign.status = "queued" if queued_count > 0 else "completed"
    db.commit()
    db.refresh(campaign)
    return campaign, queued_count


def list_campaigns(db: Session) -> list[MarketingCampaign]:
    ensure_campaigns_schema()
    stmt = select(MarketingCampaign).order_by(MarketingCampaign.created_at.desc()).limit(200)
    return list(db.scalars(stmt).all())


def list_notifications(db: Session, status: str | None) -> list[NotificationMessage]:
    ensure_campaigns_schema()
    stmt = select(NotificationMessage)
    if status:
        stmt = stmt.where(NotificationMessage.status == status)
    stmt = stmt.order_by(NotificationMessage.created_at.desc()).limit(400)
    return list(db.scalars(stmt).all())


def mark_notification_status(db: Session, notification_id: int, status: str, failure_reason: str | None) -> NotificationMessage | None:
    ensure_campaigns_schema()
    row = db.get(NotificationMessage, notification_id)
    if row is None:
        return None

    row.status = status
    if status == "sent":
        row.sent_at = datetime.now(timezone.utc)
        row.failure_reason = None
    else:
        row.failure_reason = failure_reason

    db.commit()
    db.refresh(row)
    return row


def queue_birthday_offers_today(
    db: Session,
    *,
    created_by_user_id: int,
    email_subject: str,
    message: str,
) -> tuple[MarketingCampaign, int]:
    channel = "both" if _twilio_is_configured() else "email"
    return send_campaign_now(
        db,
        name="Birthday Offer",
        channel=channel,
        target_mode="birthday_today",
        subject=email_subject,
        message=message,
        min_points=None,
        created_by_user_id=created_by_user_id,
    )
