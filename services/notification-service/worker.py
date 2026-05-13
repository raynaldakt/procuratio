from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import os
import smtplib
import time
from email.message import EmailMessage
from typing import Any
from urllib.parse import urlencode

import psycopg
import requests


@dataclass(frozen=True)
class Settings:
    database_url: str
    poll_interval_sec: int
    batch_size: int
    dry_run: bool

    smtp_host: str | None
    smtp_port: int
    smtp_user: str | None
    smtp_pass: str | None
    smtp_from: str

    twilio_account_sid: str | None
    twilio_auth_token: str | None
    twilio_from: str | None


def _normalize_db_url(url: str) -> str:
    return url.replace("postgresql+psycopg://", "postgresql://")


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


def load_settings() -> Settings:
    db_url = os.getenv("DATABASE_URL", "postgresql://procuratio:procuratio_dev@postgres:5432/procuratio")
    smtp_user = os.getenv("SMTP_USER")

    return Settings(
        database_url=_normalize_db_url(db_url),
        poll_interval_sec=_int_env("NOTIFICATION_POLL_INTERVAL_SEC", 5),
        batch_size=_int_env("NOTIFICATION_BATCH_SIZE", 20),
        dry_run=os.getenv("NOTIFICATION_DRY_RUN", "true").lower() == "true",
        smtp_host=os.getenv("SMTP_HOST"),
        smtp_port=_int_env("SMTP_PORT", 587),
        smtp_user=smtp_user,
        smtp_pass=os.getenv("SMTP_PASS"),
        smtp_from=os.getenv("SMTP_FROM", smtp_user or "no-reply@procuratio.local"),
        twilio_account_sid=os.getenv("TWILIO_ACCOUNT_SID"),
        twilio_auth_token=os.getenv("TWILIO_AUTH_TOKEN"),
        twilio_from=os.getenv("TWILIO_FROM"),
    )


def _fetch_batch(conn: psycopg.Connection, batch_size: int) -> list[dict[str, Any]]:
    with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        cur.execute(
            """
            WITH picked AS (
              SELECT nm.id
              FROM notification_messages nm
              WHERE nm.status = 'pending'
                AND nm.scheduled_for <= NOW()
              ORDER BY nm.created_at ASC
              FOR UPDATE SKIP LOCKED
              LIMIT %s
            )
            UPDATE notification_messages nm
            SET status = 'processing'
            FROM picked
            WHERE nm.id = picked.id
            RETURNING
              nm.id,
              nm.user_id,
              nm.channel,
              nm.subject,
              nm.message,
              (SELECT u.email FROM users u WHERE u.id = nm.user_id) AS user_email,
              (SELECT cp.phone FROM customer_profiles cp WHERE cp.user_id = nm.user_id) AS user_phone
            """,
            (batch_size,),
        )
        rows = cur.fetchall()
    conn.commit()
    return [dict(r) for r in rows]


def _mark_sent(conn: psycopg.Connection, notification_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE notification_messages
            SET status = 'sent',
                sent_at = NOW(),
                failure_reason = NULL
            WHERE id = %s
            """,
            (notification_id,),
        )
    conn.commit()


def _mark_failed(conn: psycopg.Connection, notification_id: int, reason: str) -> None:
    reason = reason[:250]
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE notification_messages
            SET status = 'failed',
                failure_reason = %s
            WHERE id = %s
            """,
            (reason, notification_id),
        )
    conn.commit()


def _send_email(settings: Settings, to_email: str, subject: str | None, body: str) -> None:
    if settings.dry_run:
        print(f"[DRY_RUN][EMAIL] to={to_email} subject={subject!r}")
        return

    if not settings.smtp_host:
        raise RuntimeError("SMTP_HOST is not configured")

    msg = EmailMessage()
    msg["From"] = settings.smtp_from
    msg["To"] = to_email
    msg["Subject"] = subject or "Procuratio Notification"
    msg.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as server:
        server.starttls()
        if settings.smtp_user and settings.smtp_pass:
            server.login(settings.smtp_user, settings.smtp_pass)
        server.send_message(msg)


def _send_sms(settings: Settings, to_phone: str, body: str) -> None:
    if settings.dry_run:
        print(f"[DRY_RUN][SMS] to={to_phone}")
        return

    if not settings.twilio_account_sid or not settings.twilio_auth_token or not settings.twilio_from:
        raise RuntimeError("Twilio credentials are not configured")

    url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.twilio_account_sid}/Messages.json"
    payload = {
        "From": settings.twilio_from,
        "To": to_phone,
        "Body": body,
    }
    response = requests.post(
        url,
        data=urlencode(payload),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        auth=(settings.twilio_account_sid, settings.twilio_auth_token),
        timeout=20,
    )
    if response.status_code >= 300:
        raise RuntimeError(f"Twilio send failed: {response.status_code} {response.text[:200]}")


def _process_one(settings: Settings, row: dict[str, Any]) -> tuple[bool, str | None]:
    channel = row.get("channel")
    subject = row.get("subject")
    message = row.get("message") or ""

    if channel == "email":
        to_email = row.get("user_email")
        if not to_email:
            return False, "Missing recipient email"
        _send_email(settings, to_email=to_email, subject=subject, body=message)
        return True, None

    if channel == "sms":
        to_phone = row.get("user_phone")
        if not to_phone:
            return False, "Missing recipient phone"
        _send_sms(settings, to_phone=to_phone, body=message)
        return True, None

    return False, f"Unsupported channel: {channel}"


def run_loop() -> None:
    settings = load_settings()
    print(
        "notification-service started",
        {
            "dry_run": settings.dry_run,
            "poll_interval_sec": settings.poll_interval_sec,
            "batch_size": settings.batch_size,
        },
    )

    conn = psycopg.connect(settings.database_url)
    try:
        while True:
            rows = _fetch_batch(conn, settings.batch_size)
            if not rows:
                time.sleep(settings.poll_interval_sec)
                continue

            for row in rows:
                notification_id = int(row["id"])
                try:
                    ok, reason = _process_one(settings, row)
                    if ok:
                        _mark_sent(conn, notification_id)
                    else:
                        _mark_failed(conn, notification_id, reason or "Unknown failure")
                except Exception as exc:  # noqa: BLE001
                    _mark_failed(conn, notification_id, str(exc))

    finally:
        conn.close()


if __name__ == "__main__":
    run_loop()
