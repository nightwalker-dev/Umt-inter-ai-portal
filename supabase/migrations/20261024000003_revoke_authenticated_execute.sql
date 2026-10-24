-- Revoke execution from authenticated role as well, since RLS bypasses this when executed internally
REVOKE EXECUTE ON FUNCTION get_auth_user_role() FROM authenticated;
REVOKE EXECUTE ON FUNCTION get_auth_user_team() FROM authenticated;
