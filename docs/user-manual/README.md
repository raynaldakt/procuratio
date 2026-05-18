# User Manual

## 1. Roles and access

### Available roles
- `customer`: account, appointments, shop cart/orders/reservations, gift voucher purchase.
- `staff`: POS operations, booking actions, campaigns, queue operations, voucher operations.
- `manager`: staff permissions + sensitive controls (manual loyalty adjustment, voucher/subscription cancellation).
- `admin`: full access.

### Login
1. Authenticate with your email and password.
2. Keep your access token in your session/client.

## 2. Product and service setup

### Add a product
1. Open stock/product management.
2. Create product with name, brand/type, price and stock quantity.
3. Verify it appears in search.

### Add a salon service
1. Open appointment service management.
2. Create service with duration and price.
3. Ensure `is_active=true`.

### Configure a bookable employee
1. Use employee role (`staff`, `manager`, `admin`).
2. Set profile (`workday_start_minute`, `workday_end_minute`, `slot_step_minutes`).
3. Enable `is_bookable`.

## 3. Cash register and invoicing (POS)

### Ticket workflow
1. Create sale ticket.
2. Add product/service lines.
3. Set customer (optional).
4. Apply discount.
5. Suspend/resume if needed.
6. Checkout with payment method.

### Effects
- Stock updates at checkout.
- Loyalty points are credited for linked customer.

## 4. Customer file and loyalty

### Customer profile
- Customer can update own profile (phone, birthdate, marketing consents).
- Staff can view customer profile and update staff notes.

### Loyalty points and visits
- Purchase points are automatic on paid transactions.
- Staff can register visit events.
- Manager/admin can apply manual point adjustments.

### Paid subscription loyalty plan
1. In backoffice `Client CRM`, enter customer user ID.
2. Create subscription (plan name, amount, duration, payment method, bonus points).
3. Track subscription list/status (`scheduled`, `active`, `expired`, `cancelled`).
4. Manager/admin can cancel subscription.

## 5. Appointments and planning

### Availability and booking
1. Select service, employee and date.
2. System computes available slots.
3. Book appointment.
4. Overlap conflicts are automatically blocked.

### Cancellation
- Customer can cancel own appointments.
- Staff/manager/admin can cancel operationally.

### Planning views (backoffice)
- Planning tab supports `day`, `week`, `month`, `year`.
- Date navigation: previous/today/next.
- Employee filter.
- Visual timeline cards with status and duration.

## 6. Campaigns and notifications

### Send campaign
1. Choose channel (`email`, `sms`, `both`).
2. Choose target mode (`all_customers`, `email_opt_in`, `sms_opt_in`, `birthday_today`, `min_points`).
3. Fill message (subject required for email).
4. Launch campaign.

### Notification queue
- Pending entries are persisted.
- Staff can mark entries as `sent` or `failed`.

## 7. Gift vouchers

### Staff gift workflow
1. Create voucher (`amount` or `service`).
2. Set purchaser/recipient info, effective date, duration.
3. Redeem partially or fully.
4. Check redemption history.

### Customer online gift purchase
1. In customer web, open shop tab.
2. Fill gift voucher purchase form.
3. Submit purchase.
4. Use `Imprimer le voucher` for printable output.
5. Voucher appears in `Mes gift vouchers`.

### Rules
- Voucher is blocked before effective date.
- Expired/cancelled vouchers cannot be redeemed.
- Fully redeemed vouchers cannot be cancelled.

## 8. Online shop and reservations

### Purchase flow
1. Create/get cart.
2. Add products.
3. Checkout purchase (card/transfer/wallet).
4. Order becomes paid and stock decreases.

### Reservation flow
1. Create/get cart.
2. Add products.
3. Checkout reservation with expiration window.
4. Stock is held until collect/cancel/expiry.

### Reservation lifecycle
- Staff can collect reservation.
- Staff can cancel active reservation (stock returned).
- Expired reservations are swept and restocked.

## 9. Statistics dashboard

### Overview
- Gross/net revenue and discounts.
- Paid tickets count.
- Appointments count.
- New customers.
- Loyalty points earned.
- Gift voucher sold/redeemed values.
- Top products and top services.

### Time series
- Daily points for revenue, tickets and appointments.
- Period filters: day/week/month/year or custom dates.

## 10. FAQ and troubleshooting

### Ticket cannot be edited
- Cause: ticket already paid or invalid status.
- Action: create a new ticket for changes.

### Appointment booking fails
- Cause: customer/employee overlap or employee not bookable.
- Action: choose another slot or update profile.

### Voucher purchase/redeem fails
- Cause: invalid payload, inactive service, expired/non-active voucher.
- Action: verify fields, effective date and remaining value.

### Notification not delivered
- Cause: SMTP/Twilio not configured or delivery failed.
- Action: check worker config and queue status.

### Security best practices
- Never share tokens.
- Use role-based accounts only.
- Keep `.env` private and never commit it.
