# Customer Web

Customer-facing static web app connected to the Procuratio API.

## Current features
- Authentication (login/logout)
- Product catalog with filters
- Cart creation/refresh and line add/remove
- Purchase checkout + reservation checkout
- Stripe checkout session generation for cart payment
- Appointment catalog loading (services + employees)
- Availability search, booking, cancellation
- Appointment Stripe checkout session generation
- Orders, reservations and appointments history panels
- Online gift voucher purchase flow
- Printable voucher output from browser
- Customer voucher history (`/shop/gift-vouchers/me`)

## Run

```bash
docker compose up -d api customer-web
```

Open: `http://localhost:3000`
