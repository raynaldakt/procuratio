# Customer Web (MVP)

Static customer interface for:

- login
- product selection
- cart composition
- Stripe Checkout Session creation
- appointment catalog loading (services + employees)
- availability search
- appointment booking and cancellation
- appointment history preview
- appointment online payment (Stripe session generation)

## Run with Docker

```bash
docker compose up -d api customer-web
```

Open `http://localhost:3000`.
