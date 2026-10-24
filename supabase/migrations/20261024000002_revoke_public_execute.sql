-- Revoke PUBLIC execution from the helper functions so they aren't exposed via REST API
REVOKE EXECUTE ON FUNCTION get_auth_user_role() FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION get_auth_user_team() FROM PUBLIC;
