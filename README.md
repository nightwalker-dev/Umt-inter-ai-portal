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


## Setup and Installation

### Prerequisites
- Node.js (v18+)
- Python (3.12+)
- A Supabase Project

### Environment Variables
1. **Backend**: Create `backend/.env`.
   Required variables: `SUPABASE_URL`, `SUPABASE_KEY` (service role key), `JWT_SECRET`.
2. **Frontend**: Create `frontend/.env.local`.
   Required variables: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_API_URL` (usually `http://localhost:8000`).

### Backend Setup
```bash
cd backend
python -m virtualenv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend Setup
```bash
cd frontend
npm install
npm run start:dev
```

Access the portal at `http://localhost:3000/admin`.

## Secret Rotation Runbook
If an executive handover occurs or a key compromise is suspected, follow these steps to rotate secrets securely:
1. **SUPABASE_SERVICE_KEY**: Navigate to the Supabase Dashboard -> Project Settings -> API. Generate a new `service_role` secret and copy it. Update the FastAPI production environment variables with the new key.
2. **JWT_SECRET**: Generate a new cryptographically secure secret (`openssl rand -base64 32`). Update the Supabase Auth settings to use the new secret, then update the FastAPI environment variable. Note: this will invalidate all active user sessions.
3. **Extraction Provider Key**: Rotate the key via your OCR/LLM provider dashboard and deploy the new key to the FastAPI environment.
