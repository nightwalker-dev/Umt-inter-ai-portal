# Architecture Notes

- **Browser**: Admin, Lead, User. Opens `/admin`.
- **Next.js**: Serves the UI. Next.js middleware guards `/admin` checking for a valid session token.
- **FastAPI**: Holds business logic. Validates JWT, checks roles, handles all Supabase DB calls using the Service Role Key.
- **Supabase**: Auth, Postgres DB with RLS (default deny), Storage for timetables.
- **Extraction Service**: LLM/OCR to extract timetable data from images.

### Key Decisions
- No direct DB access from frontend.
- RLS provides a backstop security measure against DB introspection.
- JWTs are validated in FastAPI for all requests.
