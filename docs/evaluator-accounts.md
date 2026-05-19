# Evaluator Accounts

Use these accounts to test the deployed Procuratio environment.

## Environment
- Demo URL (local run): `http://localhost`
- API docs (local run): `http://localhost/docs`
- Build/version: `b5f2221` (branch `main`)
- Public customer web URL: `https://customer-web-production-f032.up.railway.app`
- Public backoffice web URL: `https://backoffice-web-production-2b70.up.railway.app`
- Public API URL: `https://procuratio-production.up.railway.app`
- Public API docs URL: `https://procuratio-production.up.railway.app/docs`

## Account provisioning (recommended)

You can generate/reset demo accounts with:

```bash
cd ~/Projects/Procuratio
docker compose exec -T api python scripts/seed_demo_accounts.py
```

Default seeded credentials:
- `admin@procuratio.demo` / `Admin123!`
- `manager@procuratio.demo` / `Manager123!`
- `staff@procuratio.demo` / `Staff123!`
- `customer@procuratio.demo` / `Customer123!`

## 1. Admin account
- Email/Login: `admin@procuratio.demo`
- Password: `Admin123!`
- Role: `admin`
- Expected permissions:
- Full access to all modules and routes.
- Can perform manager/staff actions.

## 2. Manager account
- Email/Login: `manager@procuratio.demo`
- Password: `Manager123!`
- Role: `manager`
- Expected permissions:
- Access operational modules.
- Can run sensitive controls (examples: manual loyalty adjustment, voucher cancellation, employee scheduling settings).

## 3. Staff account
- Email/Login: `staff@procuratio.demo`
- Password: `Staff123!`
- Role: `staff`
- Expected permissions:
- POS operations (tickets, lines, suspend/resume, checkout).
- Appointment booking operations.
- Campaign launch and notification queue operations.
- Cannot access manager/admin-only controls.

## 4. Customer account
- Email/Login: `customer@procuratio.demo`
- Password: `Customer123!`
- Role: `customer`
- Expected permissions:
- Own profile and loyalty views.
- Own appointment booking/cancellation.
- Shop cart/purchase/reservation for own account.
- Cannot access staff backoffice controls.

## Quick Validation Scenarios

## Scenario A: POS + loyalty (staff)
1. Login with staff account.
2. Create ticket, add lines, set customer, checkout.
3. Confirm stock decreases and customer loyalty points increase.

## Scenario B: Appointments (customer + staff)
1. Customer searches availability and books an appointment.
2. Staff verifies appointment in list.
3. Customer cancels own appointment.

## Scenario C: Campaign queue (manager/staff)
1. Launch campaign with target mode.
2. Check notifications queue entries.
3. Mark one notification as sent/failed.

## Scenario D: Gift voucher
1. Create voucher (amount or service).
2. Redeem partial value then full value.
3. Confirm status transitions and redemption history.

## Scenario E: Online shop reservation
1. Customer adds product to cart.
2. Checkout as reservation.
3. Staff collects or cancels reservation.

## Notes for evaluators
- If a route returns `403`, this is expected when role restrictions apply.
- If a route returns `422`, verify business constraints (overlap, stock, voucher validity, etc.).
