# Step 0: Inventory and Baseline Report

## Baseline
- Backend tests (`pytest`): Executed. 16/16 passed. No warnings or skipped tests indicating disabled features.
- Frontend build (`npm run build`): Executed. Compiled successfully. No fatal errors.

## Inventories vs PRD

### 1. Routes (Frontend)
Compared actual routes in `frontend/src/app/admin/` against PRD Section 13.
**Findings:**
- `DEFECT`: Missing PRD route `/admin/tasks/[id]`
- `DEFECT`: Missing PRD route `/admin/events/[id]`
- `DEFECT`: Missing PRD route `/admin/profile`

### 2. Endpoints (Backend)
Compared actual endpoints in `backend/main.py` against PRD Section 16.
**Findings:**
- `DEFECT`: Missing PRD endpoint `PATCH /users/{id}` (Implemented as `PATCH /users/{user_id}`)
- `DEFECT`: Missing PRD endpoint `POST /users/{id}/reset-password` (Implemented as `POST /users/{user_id}/reset-password`)
- `DEFECT`: Missing PRD endpoint `PATCH /teams/{id}`
- `DEFECT`: Missing PRD endpoint `PATCH /tasks/{id}` (Implemented as `PATCH /tasks/{task_id}`)
- `DEFECT`: Missing PRD endpoint `POST /tasks/{id}/complete` (Implemented as `POST /tasks/{task_id}/complete`)
- `DEFECT`: Missing PRD endpoint `POST /tasks/{id}/review` (Implemented as `POST /tasks/{task_id}/review`)
- `DEFECT`: Missing PRD endpoint `GET /tasks/{id}/history` (Implemented as `GET /tasks/{task_id}/history`)
- `DEFECT`: Missing PRD endpoint `GET /events/{id}` (Implemented as `GET /events/{event_id}`)
- `DEFECT`: Missing PRD endpoint `PATCH /events/{id}` (Implemented as `PATCH /events/{event_id}`)
*Note: Most of the backend "missing" endpoints are strictly naming deviations for path parameters (`{id}` vs `{entity_id}`). However, `PATCH /teams/{id}` is genuinely missing.*

### 3. Tables (Database)
Compared schema in `001_initial_schema.sql` against PRD Section 15.
**Findings:**
- All 8 tables exist correctly.
- *Note:* PRD conflict explicitly listed in Step 0 prompt (Section 14 says nobody can pull data directly via Supabase API, but Section 15 requires RLS).

## AI Traps & Leftovers
**Findings:**
- `backend/main.py:286`: `def extract_slots_stub(image_bytes: bytes) -> list:` (Extraction stub instead of real logic, though PRD says to defer provider decision).
- `backend/main.py:103`: Comment explicitly states `bypass the password change lock` (which is technically correct for `/api/me` per PRD, but matching the search regex).
