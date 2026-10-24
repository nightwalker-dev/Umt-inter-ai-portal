import pytest
from fastapi.testclient import TestClient
from main import app
from unittest.mock import patch, MagicMock

client = TestClient(app)

def override_get_guarded_user(role="lead", user_id="lead_123", team_id="team_1"):
    async def _override():
        return {"id": user_id, "role": role, "is_active": True, "team_id": team_id}
    return _override

@patch("main.supabase.table")
def test_lead_cross_team_access_blocked(mock_table):
    # Test C12 #10: Lead views another team's availability -> Blocked (or scoped implicitly to their own team)
    # Our API doesn't accept a team_id param; it forces the scope server-side based on `current_user["team_id"]`.
    # We will verify that the supabase query uses eq("team_id", team_id)

    from main import get_guarded_user
    app.dependency_overrides[get_guarded_user] = override_get_guarded_user(role="lead", team_id="team_A")

    # Mocking the chain: supabase.table("profiles").select(...).eq("team_id", team_id)
    mock_select = MagicMock()
    mock_eq_team = MagicMock()
    mock_eq_active = MagicMock()

    mock_table.return_value.select.return_value = mock_select
    mock_select.eq.return_value = mock_eq_team

    # To handle the chain .eq("team_id", ...).eq("is_active", ...)
    def mock_eq(col, val):
        if col == "is_active":
            mock_res = MagicMock()
            mock_res.execute.return_value.data = [] # Return empty to short circuit the rest of the endpoint
            return mock_res
        return mock_eq_team

    mock_select.eq.side_effect = mock_eq
    mock_eq_team.eq.side_effect = mock_eq

    response = client.get("/api/availability")
    assert response.status_code == 200

    # Verify it checked team_id = team_A
    mock_select.eq.assert_any_call("team_id", "team_A")

    app.dependency_overrides.clear()

@patch("main.supabase.table")
def test_pending_timetable_not_free(mock_table):
    # Test AV-05: Pending timetables are never counted as free
    from main import get_guarded_user
    app.dependency_overrides[get_guarded_user] = override_get_guarded_user(role="lead", team_id="team_1")

    # Mock profiles (2 users)
    mock_profiles = MagicMock()
    mock_profiles.execute.return_value.data = [
        {"id": "u1", "full_name": "User 1"},
        {"id": "u2", "full_name": "User 2"}
    ]

    # Mock timetables (Only User 1 has a saved timetable)
    mock_timetables = MagicMock()
    mock_timetables.execute.return_value.data = [
        {"id": "tt1", "user_id": "u1"}
    ]

    # Mock slots (User 1 has NO busy slots overlapping)
    mock_slots = MagicMock()
    mock_slots.execute.return_value.data = []

    def table_side_effect(table_name):
        mock_chain = MagicMock()
        if table_name == "profiles":
            mock_chain.select.return_value.eq.return_value.eq.return_value = mock_profiles
        elif table_name == "timetables":
            mock_chain.select.return_value.eq.return_value.in_.return_value = mock_timetables
        elif table_name == "timetable_slots":
            mock_chain.select.return_value.eq.return_value.in_.return_value = mock_slots
        return mock_chain

    mock_table.side_effect = table_side_effect

    response = client.get("/api/availability/free?day=Monday&start_time=09:00&end_time=10:00")
    assert response.status_code == 200
    data = response.json()

    # User 1 should be free. User 2 has no timetable, so they MUST NOT be free.
    assert len(data) == 1
    assert data[0]["user_id"] == "u1"

    app.dependency_overrides.clear()
