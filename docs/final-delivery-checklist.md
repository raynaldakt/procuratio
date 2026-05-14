# Final Delivery Checklist (Resit)

## 1. ZIP content (mandatory)

Include these at minimum:
- `apps/` (all source code)
- `services/` (worker/notification/webhook code)
- `infra/` (compose, nginx, db scripts)
- `packages/` (shared modules if used)
- `tests/` (integration/e2e/perf)
- `docs/technical/README.md`
- `docs/user-manual/README.md`
- `docs/diagrams/*`
- `README.md`
- `.env.example`
- `docker-compose.yml`

Do **not** include:
- `.env`
- secrets/keys/certificates
- heavy caches (`__pycache__`, `node_modules`, local DB files)

## 2. Public demo link (mandatory)

Prepare one working link where evaluators can test:
- backoffice features
- customer features
- login flows

Minimum recommendation:
- reverse-proxied API + web apps behind one domain
- HTTPS enabled
- stable environment during evaluation period

## 3. Test accounts to provide (mandatory)

Provide credentials in a safe doc for evaluators (example: `docs/evaluator-accounts.md`):
- `admin` account
- `manager` account
- `staff` account
- `customer` account

For each account, mention:
- email/login
- password
- expected permissions

## 4. Functional smoke test before packaging

Run these checks end-to-end:
- auth: register/login/refresh/logout
- stock/products: create/search/update stock impact
- POS: draft ticket -> lines -> discount -> suspend/resume -> checkout
- customer file: profile + notes + loyalty history
- loyalty: earn + manual adjustment + balance update
- appointments: availability + booking + overlap prevention + cancellation
- campaigns: create/send + queue visibility + status update
- gifts: create + redeem (partial/full) + expiry/cancel rules
- online shop: cart + purchase + reservation + expiration sweep
- stats: overview + timeseries data visible

Recommended one-command validation before final packaging:
- `./scripts/smoke_test.sh`

## 5. Security and quality checks before final push

Required:
- all CI checks green on `main`
- secret scan passing
- no `.env` or secrets committed
- role protections verified on sensitive routes
- health endpoint works

Recommended:
- rerun full test suite from clean state
- verify no debug/test-only credentials in code

## 6. Technical documentation validation

Ensure technical doc explicitly contains:
- language/framework choice justification
- database architecture and key entities
- service architecture and interaction model
- security design (auth, RBAC, token lifecycle, secrets)
- sales and booking architecture
- mails/SMS and campaign queue approach
- deployment/operations model
- known limitations and roadmap

## 7. User documentation validation

Ensure user manual contains:
- role explanation
- step-by-step tutorials for each business area
- common errors and recovery actions
- reservation/gift/appointment constraints

## 8. Git and release hygiene

Before final archive:
1. Merge all approved feature PRs into `main`.
2. Pull latest `main` locally.
3. Tag final submission commit:
   - `git tag -a resit-v1 -m "Procuratio resit submission"`
4. Push tag:
   - `git push origin resit-v1`

## 9. ZIP packaging steps

From project parent directory:
1. Create export folder copy (optional but safer).
2. Remove non-deliverable local artifacts.
3. Build ZIP:
   - `zip -r Procuratio-resit.zip Procuratio/`
4. Verify ZIP opens and contains docs + source + infra.

## 10. Oral/demo script (short)

Recommended sequence for presentation:
1. Architecture overview (2 min)
2. Security model (2 min)
3. Backoffice demo: POS + appointments + loyalty + gifts (6 min)
4. Customer demo: shop + booking + account (4 min)
5. Stats dashboard + campaigns queue (3 min)
6. CI/tests + docs + known limits (2 min)

## 11. Final go/no-go gate

Ship only if all are true:
- demo link reachable
- evaluator accounts work
- full critical flow works without manual DB edits
- CI green on final commit
- technical and user docs complete
