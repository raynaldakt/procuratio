# Backoffice Web

Backoffice static web app connected to the Procuratio API for staff/manager/admin workflows.

## Current features
- Authentication and operational refresh
- KPI dashboard (stats overview + top items)
- Planning tab with day/week/month/year views
- Planning navigation + employee filter + visual timeline cards
- POS desk operations (ticket lifecycle + checkout)
- Campaign launch and birthday campaign trigger
- Notification queue review and status updates
- Gift voucher creation/list/redeem operations
- Customer profile and staff notes tools
- Paid loyalty subscription management (create/list/cancel)

## Run

```bash
docker compose up -d api backoffice-web
```

Open: `http://localhost:3001`
