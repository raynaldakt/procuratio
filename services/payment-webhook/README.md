# payment-webhook

Internal service that receives Stripe webhooks, verifies signatures, then forwards normalized payment events to the API internal endpoint.

## Endpoints

- `GET /health`
- `POST /webhooks/stripe`

## Required environment variables

- `API_INTERNAL_URL` (example: `http://api:8000`)
- `PAYMENT_WEBHOOK_TOKEN` (must match API `PAYMENT_WEBHOOK_TOKEN`)
- `STRIPE_WEBHOOK_SECRET` (starts with `whsec_...`)
- `STRIPE_WEBHOOK_TOLERANCE_SEC` (default `300`)
