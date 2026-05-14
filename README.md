# Procuratio

ERP/CRM web for Seanergy beauty and hairdressing salons.

## Monorepo layout

- `apps/backoffice-web`: staff interface (POS, stock, schedule, statistics)
- `apps/customer-web`: customer website (shop, online booking, account)
- `apps/api`: core business API
- `services/worker-jobs`: async jobs (reminders, campaigns, loyalty events)
- `services/notification-service`: email/SMS delivery service
- `services/payment-webhook`: secure payment webhook handler
- `packages/*`: shared code (UI, config, types, utilities)
- `infra/*`: Docker, compose, reverse proxy, database scripts
- `docs/*`: user and technical documentation
- `tests/*`: integration, e2e, performance

## Suggested stack (secure and realistic)

- Backend: Python + FastAPI
- Frontend: Next.js (TypeScript) for both web apps
- Database: PostgreSQL
- Cache/Queue: Redis + Celery (or RQ)
- Auth: JWT access/refresh + role-based access control
- Payments: Stripe
- Emails/SMS: Brevo + Twilio (or equivalent)
- Reverse proxy/TLS: Nginx

## Development principles

- Domain-driven modules (stock, sales, booking, customers, loyalty, gifts, campaigns)
- Strict validation (DTO/schema) on all API inputs
- Audit log on sensitive actions (payments, discounts, refunds, role changes)
- Separation between public APIs and staff APIs
- Containerized local and production environments

## Smoke test (recommended before every PR)

Run a full API smoke flow (auth, shop purchase, appointments, campaigns, stats):

```bash
./scripts/smoke_test.sh
```

Quick API-only run (if services are already up):

```bash
python3 scripts/smoke_test.py
```

## Next milestones

1. Scaffold API and both frontend apps
2. Define database schema and migrations
3. Implement authentication and roles
4. Implement stock/services and POS flows
5. Implement appointments and availability engine
6. Implement loyalty, gifts, campaigns
7. Add payments, webhooks, reminders (email/SMS)
8. Add statistics dashboards
9. Harden security and run test suite
10. Finalize technical and user documentation
