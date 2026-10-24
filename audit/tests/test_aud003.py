import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from main import app, get_current_user
import io
from PIL import Image

client = TestClient(app)

def override_user():
    async def _override():
        return {"id": "user_123", "role": "user", "is_active": True, "must_change_password": False, "team_id": "t1"}
    return _override

@patch("main.extract_slots_stub")
@patch("main.supabase")
def test_aud003_silent_cleanup_log(mock_storage, mock_extract):
    app.dependency_overrides[get_current_user] = override_user()

    img = Image.new('RGB', (10, 10))
    img_io = io.BytesIO()
    img.save(img_io, 'JPEG')
    img_io.seek(0)

    mock_remove = MagicMock()
    mock_remove.side_effect = Exception("S3 timeout")
    mock_storage.storage.from_.return_value.remove = mock_remove

    # We patch print to verify the error is logged and not swallowed completely
    with patch("builtins.print") as mock_print:
        res = client.post("/api/timetable/extract", files={"file": ("fake.jpg", img_io, "image/jpeg")})
        assert res.status_code == 200 # the endpoint succeeds normally if extraction works, just cleanup fails

        # We assert print was called with an error message because it's no longer just 'pass'
        mock_print.assert_any_call("Failed to clean up image from storage: S3 timeout")

    app.dependency_overrides.clear()
