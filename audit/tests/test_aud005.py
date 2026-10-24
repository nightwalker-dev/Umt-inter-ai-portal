import os

def test_aud005_profile_route_exists():
    assert os.path.exists("../frontend/src/app/admin/profile/page.tsx")
