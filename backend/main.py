from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import secrets
from typing import Optional, Dict, Any
from jose import jwt, JWTError
from supabase import create_client, Client
from datetime import datetime

app = FastAPI(title="Inter Club Portal API")

# Configuration limits & secrets
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
SUPABASE_URL = os.getenv("SUPABASE_URL", "http://localhost:54321")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "placeholder_service_key")
JWT_SECRET = os.getenv("JWT_SECRET", "placeholder_jwt_secret")
ALGORITHM = "HS256"

# Minimum password length
MIN_PASSWORD_LENGTH = 12

# Initialize Supabase client with Service Role Key
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Setup CORS - deny by default, allow only specific origins
origins = [FRONTEND_URL]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

def log_activity(actor_id: str, action: str, entity_type: str, entity_id: str, details: dict = None):
    try:
        supabase.table("activity_log").insert({
            "actor_id": actor_id,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "details": details or {}
        }).execute()
    except Exception as e:
        print(f"Failed to log activity: {e}")

async def get_current_user(request: Request) -> Dict[str, Any]:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    token = auth_header.split(" ")[1]

    try:
        # We assume Supabase signs the JWT with the JWT_SECRET using HS256
        # In a real environment with JWKS, this would use RS256 and the public key
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM], options={"verify_aud": False})
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token signature")

    # Read role, team, active status strictly from profiles table, NOT token
    profile_res = supabase.table("profiles").select("*").eq("id", user_id).execute()
    if not profile_res.data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User profile not found")

    profile = profile_res.data[0]

    # Check if active
    if not profile.get("is_active"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Deactivated user")

    return profile

def enforce_password_change(current_user: Dict[str, Any], path: str):
    """ Enforce lock if must_change_password is True, except for /api/me and /api/auth/first-password """
    if current_user.get("must_change_password"):
        if path not in ["/api/me", "/api/auth/first-password"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Must change password first")

async def get_guarded_user(request: Request, current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """ Standard dependency for routes that checks the password lock """
    enforce_password_change(current_user, request.url.path)
    return current_user

async def require_admin(current_user: Dict[str, Any] = Depends(get_guarded_user)) -> Dict[str, Any]:
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: Admin role required")
    return current_user

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

@app.get("/api/me")
def get_me(current_user: Dict[str, Any] = Depends(get_current_user)):
    # Explicitly using get_current_user to bypass the password change lock for this route
    return {"profile": current_user}

# --- Phase 1 User Management Models & Endpoints ---

class CreateUserRequest(BaseModel):
    email: str
    full_name: str
    role: str # admin, lead, user
    team_id: Optional[str] = None

class UpdateUserRequest(BaseModel):
    role: Optional[str] = None
    team_id: Optional[str] = None
    is_active: Optional[bool] = None

@app.post("/api/users", status_code=status.HTTP_201_CREATED)
def create_user(req: CreateUserRequest, current_user: Dict[str, Any] = Depends(require_admin)):
    """ Create a user via Supabase Admin API and insert into profiles """
    # 1. Generate strong temporary password
    import string
    alphabet = string.ascii_letters + string.digits + string.punctuation
    temp_password = "".join(secrets.choice(alphabet) for _ in range(16))

    try:
        # 2. Create Auth user
        auth_res = supabase.auth.admin.create_user({
            "email": req.email,
            "password": temp_password,
            "email_confirm": True
        })
        new_user_id = auth_res.user.id

        # 3. Create Profile row
        supabase.table("profiles").insert({
            "id": new_user_id,
            "full_name": req.full_name,
            "email": req.email,
            "role": req.role,
            "team_id": req.team_id,
            "is_active": True,
            "must_change_password": True,
            "created_by": current_user["id"]
        }).execute()

        # 4. Log Activity
        log_activity(
            actor_id=current_user["id"],
            action="user_created",
            entity_type="profile",
            entity_id=new_user_id,
            details={"email": req.email, "role": req.role, "team_id": req.team_id}
        )

        # Return password ONLY this once
        return {"id": new_user_id, "email": req.email, "temp_password": temp_password}

    except Exception as e:
        # Very basic rollback if auth succeeded but profile failed
        try:
            if 'new_user_id' in locals():
                supabase.auth.admin.delete_user(new_user_id)
        except:
            pass
        raise HTTPException(status_code=400, detail=str(e))

@app.patch("/api/users/{user_id}")
def update_user(user_id: str, req: UpdateUserRequest, current_user: Dict[str, Any] = Depends(require_admin)):
    """ Admin updates user role, team, or active status """
    update_data = req.model_dump(exclude_unset=True)
    if not update_data:
        return {"status": "no changes"}

    try:
        res = supabase.table("profiles").update(update_data).eq("id", user_id).execute()
        if "is_active" in update_data and update_data["is_active"] is False:
            supabase.auth.admin.update_user_by_id(user_id, {"ban_duration": "87600h"}) # Ban for 10 years
        elif "is_active" in update_data and update_data["is_active"] is True:
            supabase.auth.admin.update_user_by_id(user_id, {"ban_duration": "none"})
        if not res.data:
            raise HTTPException(status_code=404, detail="User not found")

        # Log Activity
        log_activity(
            actor_id=current_user["id"],
            action="user_updated",
            entity_type="profile",
            entity_id=user_id,
            details=update_data
        )

        return res.data[0]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class FirstPasswordRequest(BaseModel):
    new_password: str

@app.post("/api/users/{user_id}/reset-password")
def reset_password(user_id: str, current_user: Dict[str, Any] = Depends(require_admin)):
    """ Admin resets a user's password to a new temporary password """
    import string
    alphabet = string.ascii_letters + string.digits + string.punctuation
    temp_password = "".join(secrets.choice(alphabet) for _ in range(16))

    try:
        # Update Auth password
        supabase.auth.admin.update_user_by_id(user_id, {"password": temp_password})

        # Enforce must_change_password flag
        supabase.table("profiles").update({"must_change_password": True}).eq("id", user_id).execute()

        # Log Activity
        log_activity(
            actor_id=current_user["id"],
            action="password_reset",
            entity_type="profile",
            entity_id=user_id,
        )

        return {"id": user_id, "temp_password": temp_password}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/auth/first-password")
def set_first_password(req: FirstPasswordRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    """ User sets their new password, clearing the lock """
    if len(req.new_password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(status_code=400, detail=f"Password must be at least {MIN_PASSWORD_LENGTH} characters")

    try:
        # Update Auth password
        supabase.auth.admin.update_user_by_id(current_user["id"], {"password": req.new_password})

        # Clear lock flag
        res = supabase.table("profiles").update({"must_change_password": False}).eq("id", current_user["id"]).execute()

        # Log Activity (optional for self-service password, but good practice)
        log_activity(
            actor_id=current_user["id"],
            action="first_password_set",
            entity_type="profile",
            entity_id=current_user["id"],
        )

        return {"status": "success", "profile": res.data[0]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/teams")
def list_teams(current_user: Dict[str, Any] = Depends(get_guarded_user)):
    """ List all teams, accessible to any guarded user """
    try:
        res = supabase.table("teams").select("*").execute()
        return res.data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/users")
def list_users(current_user: Dict[str, Any] = Depends(get_guarded_user)):
    """ List users within scope """
    role = current_user.get("role")
    try:
        if role == "admin":
            res = supabase.table("profiles").select("id, full_name, email, role, team_id, is_active").execute()
        elif role == "lead":
            team_id = current_user.get("team_id")
            res = supabase.table("profiles").select("id, full_name, email, role, team_id, is_active").eq("team_id", team_id).execute()
        else:
            raise HTTPException(status_code=403, detail="Forbidden")
        return res.data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
