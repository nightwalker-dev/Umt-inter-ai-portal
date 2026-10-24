import pytest
from fastapi.testclient import TestClient
from main import app
from unittest.mock import patch, MagicMock
import io
from PIL import Image

client = TestClient(app)

def override_get_guarded_user(role="user", user_id="user_123"):
    async def _override():
        return {"id": user_id, "role": role, "is_active": True}
    return _override

@patch("main.supabase")
def test_oversized_upload(mock_storage):
    # Test C12 #19: Upload oversized file -> Rejected
    from main import get_guarded_user
    app.dependency_overrides[get_guarded_user] = override_get_guarded_user()

    large_content = b"a" * (6 * 1024 * 1024) # 6 MB
    file = {"file": ("large.jpg", large_content, "image/jpeg")}

    response = client.post("/api/timetable/extract", files=file)
    assert response.status_code == 413
    assert "too large" in response.json()["detail"]

    app.dependency_overrides.clear()

@patch("main.supabase")
def test_invalid_image_upload(mock_storage):
    # Test C12 #19: Upload renamed non-image -> Rejected
    from main import get_guarded_user
    app.dependency_overrides[get_guarded_user] = override_get_guarded_user()

    fake_img = b"This is not a real image file, just a text file named .jpg"
    file = {"file": ("fake.jpg", fake_img, "image/jpeg")}

    response = client.post("/api/timetable/extract", files=file)
    assert response.status_code == 400
    assert "Invalid image" in response.json()["detail"]

    app.dependency_overrides.clear()

@patch("main.extract_slots_stub")
@patch("main.supabase")
def test_extraction_failure_cleanup(mock_storage, mock_extract):
    # Test C12 #20: Fail extraction on purpose -> Image deleted
    from main import get_guarded_user
    app.dependency_overrides[get_guarded_user] = override_get_guarded_user()

    # Create valid dummy image
    img = Image.new('RGB', (10, 10))
    img_io = io.BytesIO()
    img.save(img_io, 'JPEG')
    img_io.seek(0)

    # Mock extraction failing
    mock_extract.side_effect = Exception("Simulated timeout or LLM failure")

    # Mock storage remove
    mock_remove = MagicMock()
    mock_storage.storage.from_.return_value.remove = mock_remove

    file = {"file": ("real.jpg", img_io, "image/jpeg")}
    response = client.post("/api/timetable/extract", files=file)

    # Should fail cleanly
    assert response.status_code == 500
    assert "Extraction failed" in response.json()["detail"]

    # Ensure remove was called (C12 #20)
    mock_remove.assert_called_once()

    app.dependency_overrides.clear()

def test_save_timetable_validation():
    # Test validation (end after start)
    from main import get_guarded_user
    app.dependency_overrides[get_guarded_user] = override_get_guarded_user()

    payload = {
        "source": "manual",
        "slots": [
            {
                "day_of_week": "Monday",
                "start_time": "14:00",
                "end_time": "13:00", # Invalid: ends before starts
                "subject": "CS 101"
            }
        ]
    }

    response = client.put("/api/timetable/me", json=payload)
    assert response.status_code == 400
    assert "End time must be after start time" in response.json()["detail"]

    app.dependency_overrides.clear()
