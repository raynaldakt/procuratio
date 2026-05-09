# Technical Documentation

## 1. Language and framework choice justification

### Project constraints
- Large business scope: stock, POS, appointments, loyalty, gifts, campaigns, e-commerce.
- Security and resilience are grading criteria.
- Solo development requires fast implementation and maintainability.

### Chosen stack
- Backend: Python 3.12 + FastAPI.
- ORM: SQLAlchemy 2.
- Validation: Pydantic.
- Auth: JWT access/refresh with role-based access control (RBAC).
- Database: PostgreSQL (runtime), SQLite (CI tests).
- Queue/cache foundation: Redis.
- Containerization: Docker Compose.

### Why FastAPI
- Fast endpoint delivery with automatic OpenAPI docs.
- Strong request validation and typing for safer business logic.
- Excellent fit with SQLAlchemy and modular service architecture.

## 2. Service architecture

### Runtime services
- `api`: core business API (FastAPI).
- `postgres`: primary relational database.
- `redis`: queue/cache foundation.
- `nginx`: reverse proxy entrypoint.
- `worker-jobs`: asynchronous jobs scaffold.
- `notification-service`: email/SMS scaffold.
- `payment-webhook`: payment event receiver scaffold.
- `backoffice-web` and `customer-web`: frontend scaffolds.

### API architectural pattern
- `routes/`: HTTP layer, role checks and response mapping.
- `schemas/`: input/output DTOs and validation.
- `services/`: business logic and invariants.
- `models/`: persistence models.
- `db/`: engine/session and base model.

### Key business modules implemented in API
- Authentication and RBAC.
- Customer profile and loyalty points.
- Appointments and availability engine.
- POS/Sales tickets and stock update at checkout.
- Campaigns and notification queue.
- Gift vouchers and redemptions.
- Online shop cart, purchase and product reservations.
- Dashboard statistics and time series.

## 3. Database architecture

### Core entities
- `users`: identities and roles (`admin`, `manager`, `staff`, `customer`).
- `user_refresh_tokens`: refresh token rotation persistence.
- `customer_profiles`: customer metadata, marketing opt-ins, loyalty aggregates.
- `loyalty_transactions`: immutable loyalty events.
- `service_offerings`: salon services (duration and price).
- `employee_profiles`: booking availability settings by employee.
- `appointments`: customer/staff schedule entries.
- `product_items`: stock and sellable products.
- `sale_tickets`, `sale_ticket_lines`: POS workflow and checkout lines.
- `marketing_campaigns`, `notification_messages`: campaign targeting and outbound queue.
- `gift_vouchers`, `gift_voucher_redemptions`: gift lifecycle and consumption tracking.
- `shop_orders`, `shop_order_lines`, `product_reservations`: online cart, purchase, pickup reservation.

### Data integrity principles
- Explicit foreign keys on all cross-domain relations.
- Status-based workflows (`draft`, `suspended`, `paid`, etc.).
- Immutable history tables where needed (`loyalty_transactions`, redemptions).
- Stock mutation only at transactional business steps (checkout, reservation, expiry sweep).

## 4. Security design

### Authentication and session model
- Password hashing with bcrypt/passlib.
- Access and refresh JWT separated by secret and type.
- Refresh token rotation with server-side hash storage.
- Logout invalidates current refresh token server-side.

### Authorization model
- RBAC guard applied at route level.
- Principle of least privilege is enforced for every role.
- `customer` can only act on own account/cart/orders.
- `staff` can operate POS and operational flows.
- `manager/admin` can access sensitive controls (manual loyalty adjustments, cancellation controls, etc.).

### Input and workflow hardening
- Strict payload validation with Pydantic.
- Ticket edit blocked after payment.
- Overlap checks in appointment booking (customer and employee).
- Voucher validity checks (effective date, expiry, remaining amount, status).
- Reservation sweep returns stock for expired reservations.

### Secrets and repository hygiene
- `.env` excluded from versioning.
- `.env.example` for safe configuration template.
- CI secret scanning enabled via Gitleaks.

## 5. Service architecture details by business flow

### POS and sales flow
- Create ticket -> add lines -> assign customer -> discount -> suspend/resume -> checkout.
- Checkout updates stock and generates loyalty points for linked customer.

### Appointment flow
- Service and employee profile setup.
- Availability search by duration and schedule window.
- Booking with overlap prevention.
- Controlled cancellation.

### Loyalty flow
- Automatic earn from purchases.
- Visit and manual adjustment events.
- Auditable transaction history and computed balance.

### Gift flow
- Voucher creation with expiration and type (amount/service).
- Partial/full redemption with traceability.
- Protected cancellation rules.

### Campaign flow
- Audience targeting by profile/points/birthday.
- Notification queue persistence for worker processing.
- Status update (`pending`, `sent`, `failed`).

### Online shop flow
- Cart management.
- Purchase checkout with paid order and stock decrement.
- Reservation checkout with stock hold and expiration sweep.

## 6. Mails/SMS and campaign architecture

### Current implementation state
- Campaign targeting and queue persistence are implemented in API.
- Delivery workers are scaffolded (`notification-service`, `worker-jobs`).

### Delivery model
- API creates `notification_messages` rows.
- Worker fetches pending messages and sends through SMTP/Twilio.
- Worker writes delivery status and timestamps back.

### Reminders and automatic events
- Architecture supports scheduled jobs for appointment reminders and birthday offers.
- Birthday campaign endpoint is already present as orchestration trigger.

## 7. Deployment and operations

### Local/dev operation
- Services launched with Docker Compose.
- Healthchecks on PostgreSQL, Redis and API.
- API available on `:8000` with docs at `/docs`.

### Quality gates
- CI runs API tests on every push/PR for API changes.
- Secret scan runs on push/PR.
- Current test suite validates cross-module business scenarios.

### Production hardening roadmap
- Migrate from auto `create_all` to versioned migrations (Alembic).
- Add non-root containers and stricter runtime policies.
- Add centralized logs/metrics and backup strategy.
- Connect real payment/webhook verification and notification workers.

## 8. Current scope and known limitations

- Frontend apps remain scaffold placeholders.
- Notification dispatch workers are scaffolded, not yet fully implemented.
- Payment provider and webhook signature verification are scaffold stage.
- Some workflows are currently API-first and need UI integration.
