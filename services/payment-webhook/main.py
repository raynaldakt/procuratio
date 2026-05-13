from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import json
import os
import time
from typing import Any

import requests
from fastapi import FastAPI, Header, HTTPException, Request, status


@dataclass(frozen=True)
class Settings:
    api_internal_url: str
    payment_webhook_token: str
    stripe_webhook_secret: str
    stripe_webhook_tolerance_sec: int


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


def load_settings() -> Settings:
    return Settings(
        api_internal_url=os.getenv("API_INTERNAL_URL", "http://api:8000"),
        payment_webhook_token=os.getenv("PAYMENT_WEBHOOK_TOKEN", "change_me"),
        stripe_webhook_secret=os.getenv("STRIPE_WEBHOOK_SECRET", ""),
        stripe_webhook_tolerance_sec=_int_env("STRIPE_WEBHOOK_TOLERANCE_SEC", 300),
    )


def _parse_stripe_signature(sig_header: str) -> tuple[int | None, list[str]]:
    timestamp: int | None = None
    signatures: list[str] = []
    for part in sig_header.split(","):
        chunk = part.strip()
        if "=" not in chunk:
            continue
        k, v = chunk.split("=", 1)
        if k == "t":
            try:
                timestamp = int(v)
            except ValueError:
                timestamp = None
        elif k == "v1" and v:
            signatures.append(v)
    return timestamp, signatures


def verify_stripe_signature(raw_body: bytes, sig_header: str, secret: str, tolerance_sec: int) -> bool:
    timestamp, signatures = _parse_stripe_signature(sig_header)
    if timestamp is None or not signatures:
        return False

    now = int(time.time())
    if abs(now - timestamp) > tolerance_sec:
        return False

    signed_payload = f"{timestamp}.{raw_body.decode('utf-8')}"
    expected = hmac.new(secret.encode("utf-8"), signed_payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(expected, candidate) for candidate in signatures)


def _extract_order_id(obj: dict[str, Any]) -> int | None:
    metadata = obj.get("metadata") or {}
    candidates = [
        metadata.get("order_id"),
        obj.get("client_reference_id"),
    ]
    for raw in candidates:
        if raw is None:
            continue
        try:
            return int(raw)
        except (TypeError, ValueError):
            continue
    return None


def _extract_amount_total_cents(obj: dict[str, Any]) -> int | None:
    for key in ("amount_total", "amount_received", "amount"):
        value = obj.get(key)
        if isinstance(value, int) and value >= 0:
            return value
    return None


def normalize_stripe_event(event: dict[str, Any]) -> dict[str, Any] | None:
    event_id = event.get("id")
    event_type = event.get("type")
    if not isinstance(event_id, str) or not isinstance(event_type, str):
        return None

    obj = (event.get("data") or {}).get("object") or {}
    if not isinstance(obj, dict):
        return None

    success_types = {
        "checkout.session.completed",
        "checkout.session.async_payment_succeeded",
        "payment_intent.succeeded",
    }
    failure_types = {
        "checkout.session.async_payment_failed",
        "payment_intent.payment_failed",
    }

    if event_type in success_types:
        payment_status = "paid"
    elif event_type in failure_types:
        payment_status = "failed"
    else:
        return {
            "event_id": event_id,
            "event_type": event_type,
            "order_id": _extract_order_id(obj),
            "payment_status": "failed",
            "provider_payment_reference": str(obj.get("id") or ""),
            "amount_total_cents": _extract_amount_total_cents(obj),
            "ignored": True,
            "ignored_reason": "Unsupported event type",
        }

    reference = obj.get("payment_intent") or obj.get("id")
    return {
        "event_id": event_id,
        "event_type": event_type,
        "order_id": _extract_order_id(obj),
        "payment_status": payment_status,
        "provider_payment_reference": str(reference) if reference is not None else None,
        "amount_total_cents": _extract_amount_total_cents(obj),
        "ignored": False,
    }


settings = load_settings()
app = FastAPI(title="Procuratio Payment Webhook", version="0.1.0")
http = requests.Session()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request, stripe_signature: str | None = Header(default=None, alias="Stripe-Signature")) -> dict[str, Any]:
    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="STRIPE_WEBHOOK_SECRET is not configured")

    if stripe_signature is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing Stripe-Signature header")

    raw_body = await request.body()
    if not verify_stripe_signature(
        raw_body=raw_body,
        sig_header=stripe_signature,
        secret=settings.stripe_webhook_secret,
        tolerance_sec=settings.stripe_webhook_tolerance_sec,
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook signature")

    try:
        event = json.loads(raw_body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload") from exc

    normalized = normalize_stripe_event(event)
    if normalized is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Stripe event payload")

    if normalized.get("ignored"):
        return {"status": "ignored", "detail": normalized.get("ignored_reason", "Ignored")}

    try:
        response = http.post(
            f"{settings.api_internal_url}/shop/internal/payments/stripe/event",
            json={
                "event_id": normalized["event_id"],
                "event_type": normalized["event_type"],
                "order_id": normalized["order_id"],
                "payment_status": normalized["payment_status"],
                "provider_payment_reference": normalized["provider_payment_reference"],
                "amount_total_cents": normalized["amount_total_cents"],
            },
            headers={"X-Webhook-Token": settings.payment_webhook_token},
            timeout=20,
        )
    except requests.RequestException as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Internal API call failed: {exc}") from exc

    if response.status_code >= 300:
        detail = response.text[:400]
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Internal API rejected webhook: {response.status_code} {detail}",
        )

    payload = response.json()
    return {
        "status": payload.get("result", "processed"),
        "detail": payload.get("detail", ""),
    }
