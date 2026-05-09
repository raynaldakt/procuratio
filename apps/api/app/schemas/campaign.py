from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

CampaignChannel = Literal["email", "sms", "both"]
CampaignTargetMode = Literal[
    "all_customers",
    "email_opt_in",
    "sms_opt_in",
    "birthday_today",
    "min_points",
]


class CampaignSendRequest(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    channel: CampaignChannel
    target_mode: CampaignTargetMode
    subject: str | None = Field(default=None, max_length=160)
    message: str = Field(min_length=3, max_length=2000)
    min_points: int | None = Field(default=None, ge=0)


class CampaignPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    channel: str
    target_mode: str
    subject: str | None
    message: str
    min_points: int | None
    status: str
    queued_count: int
    created_by_user_id: int
    launched_at: datetime | None
    created_at: datetime


class NotificationMessagePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    campaign_id: int | None
    user_id: int
    channel: str
    kind: str
    subject: str | None
    message: str
    status: str
    scheduled_for: datetime
    created_at: datetime
    sent_at: datetime | None
    failure_reason: str | None


class NotificationMarkStatus(BaseModel):
    status: Literal["sent", "failed"]
    failure_reason: str | None = Field(default=None, max_length=255)


class CampaignSendResponse(BaseModel):
    campaign: CampaignPublic
    queued_notifications: int
