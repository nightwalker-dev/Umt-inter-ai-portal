# Inter Club Portal - Security-First Implementation (P0)

This repository contains the completed P0 implementation of the Inter Club Portal. The application stack spans a FastAPI backend, Next.js frontend, and Supabase database configured strictly according to the PRD v0.2.

## Key Accomplishments

### Security & Architecture
1. **Deny by Default**: RLS policies applied globally. Direct reads/writes via Supabase REST API are blocked. All application logic passes through FastAPI.
2. **RBAC Validation**: Multi-layer RBAC logic implemented across Next.js Middleware, FastAPI endpoints (via `check_role`), and PostgreSQL functions.
3. **Audit Complete**: A read-only security audit was conducted. Findings included missing performance indexes (resolved via `002_add_indexes.sql`), missing Profile route (added), missing key rotation runbooks, and task history logging gaps (all remediated).
4. **Supabase Lints Fixed**: Resolved SECURITY DEFINER privilege escalation risks by explicitly revoking execution permissions from `anon` and `public` roles for all RPCs.
5. **Database Transaction Safety**: State transitions for tasks (including assigning, completing, and approving/rejecting) happen via atomic PostgreSQL functions (`create_task_with_history`, `transition_task_with_history`), preventing race conditions (such as double approvals).

### UI/UX Design (Stitch MCP)
- Designed using a "Calm Precision Portal" design language.
- Generated and verified 30 distinct UI designs (Desktop and Mobile) mapped to specific PRD use-cases (Dashboards, Event Management, Timetables, Availability filtering).
- Strict adherence to UI rules: no shadows, sharp corners, 1px hairlines, pure text clarity.
- Mappings and design assets are documented in `.stitch/metadata.json` and `docs/design/SCREENS.md`.

### Bug Fixes
- Critical: Repaired a bug where `POST /api/tasks` incorrectly targeted the `events` table. Rewired to hit the proper `create_task_with_history` Supabase RPC.
- Repaired Pytest relative path failures from executing tests globally.
- Both Frontend (`npm run build`) and Backend test suites pass cleanly.

## Outstanding Items / Open Decisions (for the Executive Body)
* **File size limits** for timetable uploads are hardcoded to 5MB, pending final approval.
* **Session timeout** is hardcoded to 30 mins with sliding expiration.
* **Password lengths** are enforced at a minimum of 12 characters.
* **Editing Tasks Assigned by Admins**: Currently, an Admin *can* edit tasks assigned by another Admin. Awaiting confirmation if this is the desired behavior.
* **File Cleanup Job**: Currently not implemented beyond immediate deletion after extraction (TT-08). A background cron is recommended for orphaned uploads if timeouts occur.
