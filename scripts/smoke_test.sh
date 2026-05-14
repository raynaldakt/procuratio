#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "[smoke] Starting required services..."
docker compose up -d postgres redis api notification-service payment-webhook customer-web

echo "[smoke] Seeding demo accounts..."
docker compose exec -T api python scripts/seed_demo_accounts.py

echo "[smoke] Running API smoke flow..."
python3 scripts/smoke_test.py

echo "[smoke] Done."
