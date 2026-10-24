# Step 4 - Functional Bug Hunt Preparation

Because Pass 1 mandates a strictly read-only audit and I do not have a live Supabase environment provisioned (no DB URL, Service Keys, or synthetic users provided), I cannot manually walk the browser-based flows as requested in Step 4.

However, based on the static analysis and test suite, the following edge cases have been identified as `NOT VERIFIED` but prepared for execution once a staging environment is online:

## Edge Cases to Target
1. **Timetable Boundaries:**
   - Ensure saving slots that bridge `08:00` or exactly cap at `18:00` don't trigger off-by-one rendering errors in the availability grid.
   - Test non-English characters in the `subject` field to ensure JSON serialization / database collation handles it safely without crashing the Draft view.
2. **Availability:**
   - Verify that altering `WORKING_HOURS_START` triggers a dynamic re-render of the free/busy matrix for the Lead without requiring a hard refresh.
3. **Tasks:**
   - **PRD-GAP Discovered:** Assigning a task to a *deactivated user*. The code explicitly throws `400: Cannot assign task to deactivated user` in `_enforce_assignee_rule`. The PRD is silent on this edge case, so the application behavior is secure but undocumented.
   - The UI does not provide a facility for a User to see tasks inside a "Completed" event as read-only.
4. **General Flow:**
   - Submit forms with rapid double-clicks (Tasks / Review). The backend mitigates double-approvals via strict SQL `from_status` checking, but the frontend may not disable the submit button, causing harmless but annoying `409 Conflict` popup errors for the user.

**Status:** Awaiting live environment for E2E synthetic testing.
