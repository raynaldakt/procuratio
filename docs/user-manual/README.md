# User Manual

## 1. Roles and access

### Available roles
- `customer`: account, appointments, shop cart/orders/reservations.
- `staff`: operational actions (POS, bookings, campaigns, vouchers, queue handling).
- `manager`: staff permissions + higher controls (sensitive adjustments/cancellations).
- `admin`: full access.

### Login
- Authenticate with your email and password.
- After login, keep your access token in your client/session.

## 2. Product and service setup

### Add a product
1. Open stock/product management.
2. Create a product with name, brand/type, price and stock quantity.
3. Verify it appears in product search.

### Add a salon service
1. Open appointment service management.
2. Create service with duration and price.
3. Make sure the service is active.

### Configure a bookable employee
1. Set employee role (`staff` or `manager`).
2. Configure employee profile with workday start/end and slot step.
3. Enable `is_bookable`.

## 3. Cash register and invoicing (POS)

### Create and edit a ticket
1. Create a new sale ticket.
2. Add product and/or service lines.
3. Set customer if known.
4. Apply discount if needed.

### Suspend and resume
1. Suspend the ticket when customer is not ready.
2. Resume later from ticket list.

### Checkout
1. Choose payment method.
2. Confirm checkout.
3. Stock is updated automatically.
4. Loyalty points are credited if customer is attached.

## 4. Customer file and loyalty

### Customer profile
1. Customer can update own profile (phone, birthdate, marketing consents).
2. Staff can view customer profile and update staff notes.

### Loyalty operations
- Purchase points are automatic at paid checkout.
- Staff can register visits.
- Manager/admin can apply manual point adjustments.
- Transaction history is available for audit.

## 5. Appointments and schedule

### Find availability
1. Select service, employee and date.
2. System computes available start slots.

### Book appointment
1. Customer books directly.
2. Staff can book on behalf of a customer.
3. Overlapping bookings are automatically rejected.

### Cancel appointment
- Customer can cancel own appointment.
- Staff/manager/admin can cancel operationally.

## 6. Campaigns and notifications

### Send a campaign
1. Choose channel (`email`, `sms`, `both`).
2. Choose target mode (`all_customers`, `email_opt_in`, `sms_opt_in`, `birthday_today`, `min_points`).
3. Enter message (and subject for email).
4. Launch campaign.

### Notification queue
- Pending messages are stored in queue.
- Staff can mark messages as sent/failed.

## 7. Gift vouchers

### Create voucher
1. Choose type (`amount` or `service`).
2. Fill purchaser and recipient information.
3. Set effective date and validity duration.

### Redeem voucher
1. Redeem full or partial amount.
2. Remaining value updates automatically.
3. Voucher becomes `redeemed` at zero remaining value.

### Important rules
- Voucher cannot be redeemed before effective date.
- Expired/cancelled vouchers are blocked.
- Redeemed voucher cannot be cancelled.

## 8. Online shop and reservations

### Purchase flow
1. Create/get cart.
2. Add products.
3. Checkout purchase.
4. Order becomes paid and stock is decremented.

### Reservation flow (pickup)
1. Create/get cart.
2. Add products.
3. Checkout reservation with expiration window.
4. Stock is held until pickup or expiration.

### Reservation lifecycle
- Staff can mark reservation as collected.
- Staff can cancel active reservation (stock returned).
- Expired reservations are swept and automatically restocked.

## 9. Statistics dashboard

### Overview indicators
- Gross/net revenue and discounts.
- Number of paid tickets.
- Number of appointments.
- New customers.
- Loyalty points earned.
- Gift voucher sales and redemption values.
- Top products and top services.

### Time series
- Daily series for revenue, paid tickets and appointments.
- Period filters: day/week/month/year or custom date range.

## 10. FAQ and troubleshooting

### A ticket cannot be modified
- Cause: ticket already paid or invalid status.
- Action: create a new ticket for further changes.

### Appointment booking fails
- Cause: customer or employee overlap, or employee not bookable.
- Action: choose another slot or update employee profile.

### Voucher redemption fails
- Cause: voucher expired/not active/cancelled or insufficient remaining value.
- Action: verify validity dates and remaining balance.

### Reservation stock not released
- Action: run expired reservation sweep from staff tools.

### Security best practices
- Never share tokens.
- Use role-based accounts (no shared credentials).
- Keep `.env` secret and never commit it.
