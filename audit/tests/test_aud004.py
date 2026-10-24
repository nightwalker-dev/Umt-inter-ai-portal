def test_aud004_rotation_runbook():
    with open("../README.md", "r") as f:
        content = f.read()
    assert "Secret Rotation" in content
    assert "SUPABASE_SERVICE_KEY" in content
    assert "JWT_SECRET" in content
