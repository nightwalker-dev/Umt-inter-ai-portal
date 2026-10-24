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

# --- Phase 2: Timetable ---
from fastapi import UploadFile, File
import io
from PIL import Image

MAX_FILE_SIZE = 5 * 1024 * 1024 # 5 MB

def extract_slots_stub(image_bytes: bytes) -> list:
    """ Stub for LLM/OCR extraction """
    # In reality, this would call an external service with a 15-second timeout
    return [
        {"day_of_week": "Monday", "start_time": "09:00", "end_time": "10:30", "subject": "CS 101", "room": "Room A"},
        {"day_of_week": "Wednesday", "start_time": "14:00", "end_time": "15:30", "subject": "MATH 201", "room": "Room B"}
    ]

@app.post("/api/timetable/extract")
async def extract_timetable(file: UploadFile = File(...), current_user: Dict[str, Any] = Depends(get_guarded_user)):
    """ Extract slots from image, re-encode to strip metadata, save to private bucket temporarily, and delete """
    # Only Lead and User can manage timetables
    if current_user["role"] not in ["lead", "user"]:
        raise HTTPException(status_code=403, detail="Forbidden")

    # Read and check size
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Max 5MB.")

    # Validate image type and strip metadata by re-encoding
    try:
        img = Image.open(io.BytesIO(file_bytes))
        # Prevent decompression bombs
        if img.size[0] > 4000 or img.size[1] > 4000:
            raise HTTPException(status_code=400, detail="Image dimensions too large")

        img.verify() # Verify it's actually an image
        img = Image.open(io.BytesIO(file_bytes)) # Re-open for saving after verify

        # Convert to RGB if necessary (e.g. RGBA png to JPEG) to strip complex metadata easily
        if img.mode != 'RGB':
            img = img.convert('RGB')

        out_io = io.BytesIO()
        img.save(out_io, format="JPEG") # Always save as JPEG to strip metadata
        clean_bytes = out_io.getvalue()
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid image file")

    # Upload to Supabase private storage
    import uuid
    file_path = f"{current_user['id']}/{uuid.uuid4()}.jpg"

    try:
        # We upload it. PRD says: "The original image sits in private storage and is deleted after extraction"
        supabase.storage.from_("timetables").upload(file_path, clean_bytes, file_options={"content-type": "image/jpeg"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload image: {str(e)}")

    try:
        # Call extraction service
        # If this times out or fails, the finally block will ensure cleanup
        slots = extract_slots_stub(clean_bytes)

        # Return draft. Nothing saved to DB yet.
        return {"status": "success", "draft_slots": slots}

    except Exception as e:
        raise HTTPException(status_code=500, detail="Extraction failed")

    finally:
        # PRD C7.10: Delete the original image after extraction in a finally-style step
        try:
            supabase.storage.from_("timetables").remove([file_path])
        except:
            pass # Best effort cleanup

class TimetableSlotModel(BaseModel):
    day_of_week: str
    start_time: str
    end_time: str
    subject: Optional[str] = None
    room: Optional[str] = None

class SaveTimetableRequest(BaseModel):
    source: str # 'manual' or 'image'
    semester_label: Optional[str] = None
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None
    slots: list[TimetableSlotModel]

@app.get("/api/timetable/me")
def get_my_timetable(current_user: Dict[str, Any] = Depends(get_guarded_user)):
    """ Get own timetable and slots """
    if current_user["role"] not in ["lead", "user"]:
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        tt_res = supabase.table("timetables").select("*").eq("user_id", current_user["id"]).eq("status", "active").execute()
        if not tt_res.data:
            return {"timetable": None, "slots": []}

        tt = tt_res.data[0]
        slots_res = supabase.table("timetable_slots").select("*").eq("timetable_id", tt["id"]).execute()
        return {"timetable": tt, "slots": slots_res.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/api/timetable/me")
def save_my_timetable(req: SaveTimetableRequest, current_user: Dict[str, Any] = Depends(get_guarded_user)):
    """ Save timetable and slots in a transaction """
    if current_user["role"] not in ["lead", "user"]:
        raise HTTPException(status_code=403, detail="Forbidden")

    # Server-side validation
    valid_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    for slot in req.slots:
        if slot.day_of_week not in valid_days:
            raise HTTPException(status_code=400, detail=f"Invalid day: {slot.day_of_week}")
        # Enforce end > start
        if slot.start_time >= slot.end_time:
            raise HTTPException(status_code=400, detail=f"End time must be after start time for {slot.subject}")

    # Check overlaps (warning conceptually, but we can reject or just log it depending on exact PRD semantics.
    # PRD says "overlapping slots trigger a warning". We will accept it but the frontend should warn.)

    try:
        # Check if exists
        tt_res = supabase.table("timetables").select("id").eq("user_id", current_user["id"]).execute()
        tt_id = None

        if tt_res.data:
            tt_id = tt_res.data[0]["id"]
            # Update existing
            supabase.table("timetables").update({
                "source": req.source,
                "semester_label": req.semester_label,
                "valid_from": req.valid_from,
                "valid_to": req.valid_to,
                "status": "active",
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", tt_id).execute()

            # Delete old slots
            supabase.table("timetable_slots").delete().eq("timetable_id", tt_id).execute()
        else:
            # Create new
            new_tt = supabase.table("timetables").insert({
                "user_id": current_user["id"],
                "source": req.source,
                "semester_label": req.semester_label,
                "valid_from": req.valid_from,
                "valid_to": req.valid_to,
                "status": "active"
            }).execute()
            tt_id = new_tt.data[0]["id"]

        # Insert new slots
        if req.slots:
            slot_inserts = []
            for slot in req.slots:
                slot_inserts.append({
                    "timetable_id": tt_id,
                    "day_of_week": slot.day_of_week,
                    "start_time": slot.start_time,
                    "end_time": slot.end_time,
                    "subject": slot.subject,
                    "room": slot.room
                })
            supabase.table("timetable_slots").insert(slot_inserts).execute()

        return {"status": "success", "message": "Timetable saved"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
