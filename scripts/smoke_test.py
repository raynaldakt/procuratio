#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
import sys
import time
from urllib import error, parse, request
from uuid import uuid4


API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")


def _request_json(method: str, path: str, payload: dict | None = None, token: str | None = None) -> dict:
    url = f"{API_BASE}{path}"
    data = None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    req = request.Request(url=url, data=data, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {path} failed with HTTP {exc.code}: {detail}") from exc


def _wait_health(max_seconds: int = 90) -> None:
    deadline = time.time() + max_seconds
    last_error = "unknown"
    while time.time() < deadline:
        try:
            payload = _request_json("GET", "/health")
            if payload.get("status") == "ok":
                return
            last_error = f"health status={payload.get('status')}"
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
        time.sleep(2)
    raise RuntimeError(f"API healthcheck did not become ready in time: {last_error}")


def _login(email: str, password: str) -> str:
    body = _request_json("POST", "/auth/login", {"email": email, "password": password})
    token = body.get("access_token")
    if not isinstance(token, str) or not token:
        raise RuntimeError(f"Login response missing access_token for {email}")
    return token


def _pick_first_available_slot(customer_token: str, service_id: int, employee_id: int) -> str:
    target_date = (datetime.now(timezone.utc) + timedelta(days=1)).date().isoformat()
    query = parse.urlencode(
        {
            "service_offering_id": service_id,
            "target_date": target_date,
            "employee_user_id": employee_id,
        }
    )
    slots = _request_json("GET", f"/appointments/availability?{query}", token=customer_token)
    if not isinstance(slots, list) or not slots:
        raise RuntimeError("No appointment slot returned by availability search")
    start_at = slots[0].get("start_at")
    if not isinstance(start_at, str):
        raise RuntimeError("Availability payload missing start_at")
    return start_at


def main() -> int:
    print(f"[smoke] API base: {API_BASE}")
    _wait_health()
    print("[smoke] API health OK")

    admin_token = _login("admin@procuratio.demo", "Admin123!")
    manager_token = _login("manager@procuratio.demo", "Manager123!")
    staff_token = _login("staff@procuratio.demo", "Staff123!")
    customer_token = _login("customer@procuratio.demo", "Customer123!")
    print("[smoke] Demo account logins OK")

    staff_me = _request_json("GET", "/auth/me", token=staff_token)
    staff_id = staff_me["id"]

    sku = f"SMOKE-{uuid4().hex[:10].upper()}"
    product = _request_json(
        "POST",
        "/sales/products",
        {
            "name": "Smoke Product",
            "brand": "Seanergy",
            "product_type": "care",
            "sku": sku,
            "description": "Smoke test product",
            "price_cents": 1900,
            "stock_quantity": 5,
        },
        token=staff_token,
    )
    product_id = product["id"]

    _request_json("POST", "/shop/cart", {}, token=customer_token)
    _request_json(
        "POST",
        "/shop/cart/lines",
        {"product_item_id": product_id, "quantity": 1},
        token=customer_token,
    )
    checkout = _request_json(
        "POST",
        "/shop/cart/checkout/purchase",
        {"payment_method": "transfer"},
        token=customer_token,
    )
    order_id = checkout["order"]["id"]
    print(f"[smoke] Shop flow OK (order #{order_id})")

    service = _request_json(
        "POST",
        "/appointments/services",
        {
            "name": f"Smoke Service {uuid4().hex[:6]}",
            "description": "Smoke test appointment service",
            "duration_minutes": 30,
            "price_cents": 2500,
        },
        token=staff_token,
    )
    service_id = service["id"]

    _request_json(
        "PUT",
        f"/appointments/employees/{staff_id}/profile",
        {
            "is_bookable": True,
            "workday_start_minute": 9 * 60,
            "workday_end_minute": 19 * 60,
            "slot_step_minutes": 15,
        },
        token=manager_token,
    )

    start_at = _pick_first_available_slot(customer_token, service_id, staff_id)
    appt = _request_json(
        "POST",
        "/appointments/book",
        {
            "service_offering_id": service_id,
            "start_at": start_at,
            "employee_user_id": staff_id,
            "notes": "Smoke booking",
            "pay_in_store": True,
        },
        token=customer_token,
    )
    appt_id = appt["id"]
    print(f"[smoke] Appointment flow OK (appointment #{appt_id})")

    campaign = _request_json(
        "POST",
        "/campaigns/send",
        {
            "name": f"Smoke Campaign {uuid4().hex[:6]}",
            "channel": "email",
            "target_mode": "email_opt_in",
            "subject": "Smoke Campaign",
            "message": "Smoke test campaign message",
        },
        token=manager_token,
    )
    print(f"[smoke] Campaign flow OK (queued={campaign['queued_notifications']})")

    _request_json("GET", "/stats/overview?period=month", token=staff_token)
    print("[smoke] Stats overview OK")

    print("[smoke] ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"[smoke] FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
