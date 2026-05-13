# Notification Service

This worker polls `notification_messages` where `status='pending'` and `scheduled_for <= now`,
then attempts to deliver by channel (`email`, `sms`) and updates status to `sent` or `failed`.

## Environment variables
- `DATABASE_URL`
- `NOTIFICATION_DRY_RUN` (`true`/`false`)
- `NOTIFICATION_POLL_INTERVAL_SEC`
- `NOTIFICATION_BATCH_SIZE`
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM`
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM`

## Dev note
Set `NOTIFICATION_DRY_RUN=true` to avoid real delivery and just mark messages as sent.
