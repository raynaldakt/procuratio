# Technical Documentation

## 1. Language and framework choice justification

### Constraints
- Broad functional scope (POS, stock, scheduling, CRM, loyalty, gifts, campaigns, e-commerce).
- Strong security/stability expectations.
- Solo development context requiring fast iteration and maintainable architecture.

### Stack
- Backend: Python 3.12 + FastAPI.
- ORM: SQLAlchemy 2.
- Validation: Pydantic.
- Auth: JWT access/refresh + RBAC.
- Database: PostgreSQL (runtime), SQLite (CI).
- Queue/cache foundation: Redis.
- Containerization: Docker Compose.
- Frontend: static HTML/CSS/JS apps for backoffice and customer channels.

### Why FastAPI
- Fast endpoint delivery with OpenAPI documentation.
- Strong typed validation for safer business workflows.
- Good fit for modular service-layer architecture.

## 2. Service architecture

### Runtime services
- `api`: core business API.
- `postgres`: relational persistence.
- `redis`: queue/cache foundation.
- `nginx`: reverse proxy entrypoint.
- `worker-jobs`: async jobs scaffold.
- `notification-service`: queue consumer for SMTP/Twilio sends.
- `payment-webhook`: Stripe webhook verification and forwarding.
- `backoffice-web`, `customer-web`: operational frontend channels.

### API layering
- `routes/`: transport + auth/role checks.
- `schemas/`: request/response contracts.
- `services/`: business invariants and workflows.
- `models/`: relational data model.
- `db/`: session/engine/bootstrap.

## 3. Database architecture

### Core entities
- `users`, `user_refresh_tokens`
- `customer_profiles`, `loyalty_transactions`, `loyalty_subscriptions`
- `service_offerings`, `employee_profiles`, `appointments`
- `product_items`, `sale_tickets`, `sale_ticket_lines`
- `shop_orders`, `shop_order_lines`, `product_reservations`
- `gift_vouchers`, `gift_voucher_redemptions`
- `marketing_campaigns`, `notification_messages`
- `payment_webhook_events`, `appointment_payment_webhook_events`, `appointment_payment_states`

### Integrity principles
- Explicit foreign keys across bounded contexts.
- Status-driven workflows (`draft`, `suspended`, `paid`, `reserved`, etc.).
- Immutable/auditable event-style rows for loyalty/redemption/webhook events.
- Stock mutation only at transactional operations (checkout/reservation/sweep).

## 4. Security design

### Authentication and sessions
- Password hashing with passlib/bcrypt.
- Access and refresh JWTs with separate token type semantics.
- Refresh token rotation persisted server-side.
- Logout invalidates refresh token server-side.

### Authorization
- Route-level RBAC (`customer`, `staff`, `manager`, `admin`).
- Least-privilege boundaries on sensitive actions (manual points, cancellations, internal endpoints).

### Hardening
- Pydantic validation on all payloads.
- Appointment overlap checks for customer and employee.
- Voucher validity checks (effective date, expiry, remaining value, status).
- Internal webhook token + Stripe signature verification with tolerance window.

### Secrets and hygiene
- `.env` excluded from VCS.
- `.env.example` template for required settings.
- CI secret scanning via Gitleaks.

## 5. Business flows implementation

### POS / Sales
- Ticket lifecycle: create -> lines -> customer -> discount -> suspend/resume -> checkout.
- Checkout updates stock and loyalty points.

### Appointments
- Service and employee profile setup.
- Availability search by duration and schedule window.
- Booking with overlap prevention.
- Cancellation controls.
- Optional Stripe checkout session for appointment payment.

### Planning
- Backoffice planning UI supports day/week/month/year views.
- Employee filter and date navigation.
- Visual appointment cards by status/duration.

### Loyalty
- Purchase earn, visit events, manual adjustment.
- Paid loyalty subscriptions with statuses (`scheduled`, `active`, `expired`, `cancelled`).
- Optional subscription bonus points credited in loyalty transactions.

### Gifts
- Amount/service voucher creation.
- Partial/full redemption tracking.
- Cancellation protections.
- Online customer voucher purchase with printable payload and queued email notification.

### Campaigns and notifications
- Targeting modes (`all_customers`, opt-ins, birthday, min_points).
- Notification queue persistence with status lifecycle (`pending`, `processing`, `sent`, `failed`).

### Shop
- Cart management.
- Purchase checkout.
- Reservation checkout + collect/cancel/sweep-expired.

### Statistics
- Overview KPIs (revenue, appointments, loyalty, voucher metrics, top items).
- Time-series endpoint for charts.

## 6. Mails/SMS architecture

### Implemented behavior
- API writes queued `notification_messages`.
- `notification-service` pulls queue and sends:
- Email via SMTP.
- SMS via Twilio.
- Delivery status is persisted.

### Current operational mode
- Works in dry-run or real mode based on env config.
- Real delivery depends on valid SMTP/Twilio credentials.

## 7. Deployment and operations

### Local/dev
- Docker Compose orchestration.
- Health checks on DB/Redis/API.
- API docs available at `/docs`.

### Quality gates
- API CI tests on push/PR.
- Secret scan on push/PR.
- Local smoke test scripts for end-to-end critical paths.

### Test tooling in containers
- `api` installs `requirements-dev.txt` in compose, ensuring `pytest` is available for local containerized validation.

## 8. Known limitations and roadmap

- No migration framework yet (`create_all` bootstrapping still used): migrate to Alembic for production-grade change management.
- Worker orchestration is single-process scaffold (no full job scheduler/monitoring stack yet).
- Real deliverability (SMTP/Twilio reputation, retries, observability) requires production ops setup.
- UI is static-app based (no SSR/PWA concerns addressed yet).
