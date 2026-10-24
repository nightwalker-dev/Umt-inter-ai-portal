import os

def test_missing_indexes():
    # Assert that a migration file exists for adding indexes
    assert os.path.exists("002_add_indexes.sql"), "002_add_indexes.sql migration is missing"

    with open("002_add_indexes.sql", "r") as f:
        content = f.read().lower()

    assert "create index" in content
    assert "idx_tasks_assigned_to" in content
    assert "idx_tasks_team_id" in content
    assert "idx_tasks_event_id" in content
    assert "idx_tasks_status" in content
    assert "idx_timetable_slots_timetable_id" in content
