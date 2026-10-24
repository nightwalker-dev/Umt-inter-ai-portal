-- Harden SECURITY DEFINER functions based on Supabase Security Advisor
ALTER FUNCTION get_auth_user_role() SET search_path = public;
ALTER FUNCTION get_auth_user_team() SET search_path = public;
ALTER FUNCTION prevent_modifications() SET search_path = public;
ALTER FUNCTION check_task_assignment() SET search_path = public;

-- Revoke execute from anon (it should only be called by authenticated users or internally by RLS)
REVOKE EXECUTE ON FUNCTION get_auth_user_role() FROM anon;
REVOKE EXECUTE ON FUNCTION get_auth_user_team() FROM anon;
