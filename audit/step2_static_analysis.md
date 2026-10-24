# Static Security Analysis

## 2.1 Authentication and Sessions
- `must_change_password` locked on the server for all routes except `/me` and `/auth/first-password`? **Verified**.
- Role and team come from DB? **Verified**.
- Temporary password safe? **Verified**. `secrets.choice()` used, not logged, not cached.
- Signup disabled? **Verified** via Supabase (and no `/api/signup` exists).
- JWT Verification: Uses `PyJWT`. Decodes with strictly verified `sub`. **Verified**.

## 2.2 Authorization
- Mass assignment blocked? **Verified**. Testing proves `Pydantic` `exclude_unset=True` with rigid base models successfully truncates all unexpected properties during `PATCH`.
- IDOR checks? **Verified**. Endpoints referencing IDs explicitly fetch and execute scope validations (`current_user["id"] == assigned_to` or `team_id`) before operating. Returns `404` to prevent existence probing.
- Broken function level auth? **Verified**. Admin-only endpoints correctly invoke the `require_admin` dependency.
- Business logic abuse? **Verified**. Status changes locked to Admin (`review`), or constrained appropriately (`complete` requires `pending`/`rejected`). Rejection strictly enforces `note`.

## 2.3 Database and RLS
- RLS enabled on all 8 tables with default deny? **Verified** in `001_initial_schema.sql`.
- Parameterised queries? **Verified**. PostgREST via Supabase `supabase-py` abstracts parameterization, protecting against SQL injection.
- Append-only tables? **Verified**. `activity_log` and `task_status_history` have no `UPDATE` or `DELETE` endpoints, and RLS disables write access entirely for anon/users.

## 2.4 Frontend
- DangerouslySetInnerHTML? **Verified absent**.
- Security headers? **Verified**. `next.config.js` properly configures CSP, HSTS, `nosniff`, `X-Frame-Options`, and `X-Robots-Tag: noindex`.

## 2.5 Upload and Extraction
- Size limits and real file types? **Verified**. Max size set to 5MB, PIL used to decode and `verify()` raw bytes, stripped metadata by re-encoding to `JPEG`.
- Safe paths and cleanup? **Verified**. UUID generation prevents collision. `finally` block successfully executed in automated tests even on extraction crash.

## 2.6 API, Transport, Config
- CORS restrictive? **Verified**. Bound strictly to `FRONTEND_URL`.
- No public links? **Verified**.

## 2.7 Secrets, Supply Chain
- `pip-audit` & `npm audit` returned 0 vulnerabilities (Dependencies patched in earlier setup).
- Secret scans found no hardcoded keys outside `.env.example`.
