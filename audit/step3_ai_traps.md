# Step 3 - AI Traps Search

## Analysis
1. **Missing Awaits:** The queries flagged (e.g., lines 40, 137, 411) are instances where the query builder is constructed and broken over multiple lines before `execute()` is called later, or they are synchronous calls relying on the Python Supabase client. (FastAPI endpoints are defined using `def` rather than `async def`, which aligns with the synchronous PostgREST client implementation in `supabase-py`).
2. **RLS `USING (true)`:** Detected on line 203 of `001_initial_schema.sql` for the `events` table: `CREATE POLICY events_select ON events FOR SELECT TO authenticated USING (true);`. This is actually consistent with PRD `EV-02` which states "Every event is visible to all Leads and Users".
3. **`except: pass` usage:**
   - Found at `backend/main.py:166` explicitly swallowing deletion errors if user rollback fails.
   - Found at `backend/main.py:352` swallowing storage removal errors (`Best effort cleanup`).
   - *Verdict:* This is a known AI trap. Swallowing exceptions leads to silent failures (e.g. orphaned images if storage is down).
4. **Client-side only auth:** No `isAdmin` or `hidden` props were found governing sensitive actions. FastAPI strictly validates roles.
5. **Leaked Service Keys:** None found in the frontend bundle or source.
6. **Unhandled Promises in Auth:** The endpoints use synchronous `def` for FastAPI routing while injecting asynchronous dependencies (`async def get_current_user`). FastAPI natively resolves `async` dependencies for synchronous endpoints safely.
