# Inter Club Portal

Role-based web portal for timetable tracking and task assignment.

## Tech Stack
- Frontend: Next.js (TypeScript, Tailwind CSS)
- Backend: FastAPI (Python)
- Database/Auth: Supabase (Postgres)

## Security
- Deny by default principles applied.
- All roles checked on server.
- Service Role Keys kept only in FastAPI environment.
- RLS enabled on all tables with default deny.

## Development Phases
- **Phase 0:** Setup (Current)
- **Phase 1:** Auth and Users
- **Phase 2:** Timetable
- **Phase 3:** Availability
- **Phase 4:** Tasks and Events
- **Phase 5:** Polish and Launch

## Developers Notes
- `frontend/`: Next.js application.
- `backend/`: FastAPI application.
- `001_initial_schema.sql`: Initial Supabase migration for tables and RLS policies.
