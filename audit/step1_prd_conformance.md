# Step 1 - PRD Conformance Report

**Verdict Summary:** Most requirements PASS according to static analysis and automated FastAPI test evaluations. Some frontend behaviors and DB state transitions are marked `NOT VERIFIED` due to lacking a live Supabase environment (as instructed by Pass 1 constraints).

| ID | What to verify | Verdict | Evidence |
|----|----------------|---------|----------|
| AUTH-01 | Login at `/admin/login`, dashboard landing | NOT VERIFIED | Requires live DB for e2e flow, but route exists in `frontend/src/app/admin/login` |
| AUTH-02 | Sign-ups disabled | PASS | `audit/tests/test_step1_auth.py` confirms no signup API endpoint exists. |
| AUTH-03 | Only Admin creates users, secure temp password | PASS | `POST /api/users` uses `require_admin` dependency and `secrets.choice()` for 16-char password. |
| AUTH-04 | First login forces password change | PASS | Verified in `test_step1_auth.py` (HTTP 403 blocks endpoints except `/me` and `/auth/first-password`). |
| AUTH-05 | Admin can deactivate | PASS | `PATCH /api/users/{id}` handles `ban_duration` injection on Supabase auth. |
| AUTH-06 | Admin reset issues new temp password | PASS | `POST /api/users/{id}/reset-password` logic verified. |
| AUTH-07 | Role checks on all APIs | PASS | Verified via `get_guarded_user` / `require_admin` FastAPI injection in `test_step1_authz_matrix.py`. |
| AUTH-08 | Rate limiting and session expiry | NOT VERIFIED | Supabase-native configurations cannot be checked statically without live instance. |
| AUTH-09 | /admin pages not indexed | PASS | `next.config.js` sets `X-Robots-Tag: noindex, nofollow` |
| TEAM-01, TEAM-02 | Initial teams, Constraints | PASS | Present in `001_initial_schema.sql` (Seed logic and CHECK constraints). |
| TT-01 | Manual slot add | PASS | React state handling in `timetable/page.tsx` supports manual entry. |
| TT-02 to TT-08 | Extraction, sizes, DB save, cleanup | PASS | Backend `extract_timetable` uses PIL for metadata stripping, capped at 5MB, deletes on finally. |
| AV-01 to AV-06 | Lead views team grid, free/busy | PASS | `GET /api/availability` enforces scope checking and strictly excludes pending timetables from being marked "free". |
| TK-01 | Task fields | PASS | `CreateTaskRequest` model. |
| TK-02 | Lead assigns only to own team | PASS | `test_step1_tasks.py` verifies `400` errors for assigning to Admins, self, or other teams. Backed by SQL `check_task_assignment` trigger. |
| TK-03 | Event binding | PASS | Optional `event_id` implemented. |
| TK-04 | User lists, Complete tasks | PASS | `POST /api/tasks/{id}/complete` requires assignee. |
| TK-05 | Admin approves/rejects | PASS | `POST /api/tasks/{id}/review` locked to Admin. Rejection requires non-empty note. |
| TK-06, TK-08 | Scope constraints on tasks | PASS | Enforced dynamically inside `GET /api/tasks`. |
| TK-07 | Status changes recorded | PASS | Atomic Postgres RPC `transition_task_with_history` logs to `task_status_history` and `activity_log`. |
| TK-09 | Assigner edits | PASS | Maintained default-deny: `if task["assigned_by"] != current_user["id"]` blocking cross-admin edits as requested by PRD open question constraints. |
| TK-10 | Admin review queue | PASS | `frontend/src/app/admin/review` fetches all completed tasks. |
| TK-14 | Tasks to Lead | PASS | Admin can assign to Lead (`_enforce_assignee_rule`). |
| EV-01 to EV-08 | Event flows | PASS | Routes and logic implemented cleanly. |
| REC-01, REC-02 | Activity logs and metrics | PASS | Metrics calculated in `/api/dashboard`, audit events populated via `log_activity` helper. |

**PRD Known Inconsistencies (PRD-GAP)**
- `PATCH /teams/{id}` is missing from backend (P1 feature omitted in P0 implementation as per prioritization).
- `GET /availability` implemented explicitly scoped to Leads (Admin cross-team view deferred to P1).
- Assigner edit rules correctly locked down to strict assigner-only (closing the PRD question loop).
