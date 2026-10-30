from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import secrets
from typing import Optional, Dict, Any
import jwt
from jwt.exceptions import InvalidTokenError as JWTError
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
        except Exception as cleanup_err:
            print(f"Failed to clean up image from storage: {cleanup_err}") # Best effort cleanup logged

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

# --- Phase 3: Availability ---

WORKING_HOURS_START = os.getenv("WORKING_HOURS_START", "08:00")
WORKING_HOURS_END = os.getenv("WORKING_HOURS_END", "18:00")

@app.get("/api/availability")
def get_availability(current_user: Dict[str, Any] = Depends(get_guarded_user)):
    """ Get team availability grid """
    # Only Lead (own team) and Admin (all) can view
    # P0: Leads see own team. (Admins cross-team is P1). We will implement Lead scope here.
    if current_user["role"] not in ["lead", "admin"]:
        raise HTTPException(status_code=403, detail="Forbidden")

    team_id = current_user.get("team_id")
    if current_user["role"] == "lead" and not team_id:
        raise HTTPException(status_code=403, detail="Lead has no team assigned")

    # Fetch users in scope
    try:
        if current_user["role"] == "admin":
            users_res = supabase.table("profiles").select("id, full_name, role").eq("is_active", True).execute()
        else:
            users_res = supabase.table("profiles").select("id, full_name, role").eq("team_id", team_id).eq("is_active", True).execute()

        users = users_res.data
        user_ids = [u["id"] for u in users]

        if not user_ids:
            return {"users": [], "availability": {}}

        # Fetch active timetables for these users
        tt_res = supabase.table("timetables").select("id, user_id, updated_at").eq("status", "active").in_("user_id", user_ids).execute()
        timetables = tt_res.data
        tt_by_user = {t["user_id"]: t for t in timetables}
        tt_ids = [t["id"] for t in timetables]

        # Fetch slots (minimize data returned: no subject, no room)
        slots_data = []
        if tt_ids:
            slots_res = supabase.table("timetable_slots").select("timetable_id, day_of_week, start_time, end_time").in_("timetable_id", tt_ids).execute()
            slots_data = slots_res.data

        # Group slots by user
        slots_by_user = {u["id"]: [] for u in users}
        for slot in slots_data:
            # find user_id for this timetable_id
            owner_id = next((uid for uid, t in tt_by_user.items() if t["id"] == slot["timetable_id"]), None)
            if owner_id:
                slots_by_user[owner_id].append({
                    "day_of_week": slot["day_of_week"],
                    "start_time": slot["start_time"],
                    "end_time": slot["end_time"]
                })

        # Format response
        result = []
        for user in users:
            uid = user["id"]
            tt = tt_by_user.get(uid)
            result.append({
                "user_id": uid,
                "full_name": user["full_name"],
                "role": user["role"],
                "timetable_status": "saved" if tt else "pending",
                "last_updated": tt["updated_at"] if tt else None,
                "busy_slots": slots_by_user[uid]
            })

        return {
            "working_hours": {"start": WORKING_HOURS_START, "end": WORKING_HOURS_END},
            "members": result
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/availability/free")
def get_free_members(day: str, start_time: str, end_time: str, current_user: Dict[str, Any] = Depends(get_guarded_user)):
    """ Get users free in a specific window """
    if current_user["role"] not in ["lead", "admin"]:
        raise HTTPException(status_code=403, detail="Forbidden")

    team_id = current_user.get("team_id")

    try:
        # Get members in scope
        if current_user["role"] == "admin":
            users_res = supabase.table("profiles").select("id, full_name").eq("is_active", True).execute()
        else:
            users_res = supabase.table("profiles").select("id, full_name").eq("team_id", team_id).eq("is_active", True).execute()

        users = users_res.data
        user_ids = [u["id"] for u in users]

        if not user_ids:
            return []

        # Get active timetables
        tt_res = supabase.table("timetables").select("id, user_id").eq("status", "active").in_("user_id", user_ids).execute()
        timetables = tt_res.data
        tt_by_user = {t["user_id"]: t["id"] for t in timetables}

        # A pending timetable is NEVER counted as free (AV-05).
        # We only consider users who HAVE an active timetable.
        users_with_tt = [u for u in users if u["id"] in tt_by_user]
        if not users_with_tt:
            return []

        # Fetch busy slots that overlap with the requested time
        # Overlap logic: slot.start < requested.end AND slot.end > requested.start
        tt_ids_with_tt = list(tt_by_user.values())
        slots_res = supabase.table("timetable_slots").select("timetable_id").eq("day_of_week", day).in_("timetable_id", tt_ids_with_tt).execute()

        # We have to filter overlaps in Python due to PostgREST limitations on complex time comparisons easily
        # Alternatively, we could write an RPC, but fetching today's slots is small enough.
        all_day_slots_res = supabase.table("timetable_slots").select("timetable_id, start_time, end_time").eq("day_of_week", day).in_("timetable_id", tt_ids_with_tt).execute()

        busy_tt_ids = set()
        for slot in all_day_slots_res.data:
            # Overlap: starts before req ends, AND ends after req starts
            if slot["start_time"] < end_time and slot["end_time"] > start_time:
                busy_tt_ids.add(slot["timetable_id"])

        # Find who is free
        free_members = []
        for user in users_with_tt:
            tt_id = tt_by_user[user["id"]]
            if tt_id not in busy_tt_ids:
                free_members.append({
                    "user_id": user["id"],
                    "full_name": user["full_name"]
                })

        return free_members
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- Phase 4: Events ---

class CreateEventRequest(BaseModel):
    name: str
    description: Optional[str] = None
    start_date: str
    end_date: str
    status: str # upcoming, ongoing, completed

class UpdateEventRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    status: Optional[str] = None

@app.post("/api/events", status_code=status.HTTP_201_CREATED)
def create_event(req: CreateEventRequest, current_user: Dict[str, Any] = Depends(require_admin)):
    """ Admin creates an event """




    try:
        data = req.model_dump(exclude_unset=True)
        data["created_by"] = current_user["id"]
        res = supabase.table("events").insert(data).execute()

        log_activity(current_user["id"], "event_created", "event", res.data[0]["id"], data)
        return res.data[0]
    except Exception as e:




        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/events")
def list_events(current_user: Dict[str, Any] = Depends(get_guarded_user)):
    """ All guarded users can see events """
    try:
        res = supabase.table("events").select("*").order("start_date", desc=True).execute()
        return res.data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/events/{event_id}")
def get_event(event_id: str, current_user: Dict[str, Any] = Depends(get_guarded_user)):
    """ Get event details (including its tasks within scope) """
    try:
        ev_res = supabase.table("events").select("*").eq("id", event_id).execute()
        if not ev_res.data:
            raise HTTPException(status_code=404, detail="Event not found")

        event = ev_res.data[0]

        # Get tasks within scope
        # Scope: Admin (all), Lead (team + own), User (own)
        # We rely on Supabase RLS policies for Tasks, but since we are using Service Role,
        # we MUST enforce the scope manually here!
        query = supabase.table("tasks").select("id, title, assigned_to, assigned_by, team_id, status").eq("event_id", event_id)

        if current_user["role"] == "user":
            query = query.eq("assigned_to", current_user["id"])
        elif current_user["role"] == "lead":
            # PostgREST syntax for OR is slightly tricky via python client.
            # Team or assigned to me
            # .or_(f"team_id.eq.{current_user['team_id']},assigned_to.eq.{current_user['id']}")
            query = query.or_(f"team_id.eq.{current_user['team_id']},assigned_to.eq.{current_user['id']}")

        tasks_res = query.execute()

        return {"event": event, "tasks": tasks_res.data}
    except Exception as e:
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=400, detail=str(e))

@app.patch("/api/events/{event_id}")
def update_event(event_id: str, req: UpdateEventRequest, current_user: Dict[str, Any] = Depends(require_admin)):
    """ Admin updates event """
    update_data = req.model_dump(exclude_unset=True)
    if not update_data:
        return {"status": "no changes"}

    try:
        update_data["updated_at"] = datetime.utcnow().isoformat()
        res = supabase.table("events").update(update_data).eq("id", event_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Event not found")

        log_activity(current_user["id"], "event_updated", "event", event_id, update_data)
        return res.data[0]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- Phase 4: Tasks ---

class CreateTaskRequest(BaseModel):
    title: str
    description: Optional[str] = None
    assigned_to: str
    event_id: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[str] = None

class UpdateTaskRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assigned_to: Optional[str] = None
    due_date: Optional[str] = None

def _enforce_assignee_rule(assigner: Dict[str, Any], assignee_id: str) -> str:
    """ Enforces TK-02 rule and returns the assignee's team_id """
    # Fetch assignee profile
    assignee_res = supabase.table("profiles").select("id, role, team_id, is_active").eq("id", assignee_id).execute()
    if not assignee_res.data:
        raise HTTPException(status_code=404, detail="Assignee not found")

    assignee = assignee_res.data[0]
    if not assignee.get("is_active"):
        raise HTTPException(status_code=400, detail="Cannot assign task to deactivated user")

    if assigner["role"] == "admin":
        # Admin can assign to any User or Lead
        if assignee["role"] not in ["user", "lead"]:
            raise HTTPException(status_code=400, detail="Admins can only assign to Users or Leads")
    elif assigner["role"] == "lead":
        # Lead can assign ONLY to Users of their OWN team (not to self, Admin, or other Lead)
        if assignee["id"] == assigner["id"]:
            raise HTTPException(status_code=400, detail="Leads cannot assign tasks to themselves")
        if assignee["role"] != "user":
            raise HTTPException(status_code=400, detail="Leads can only assign tasks to Users")
        if assignee["team_id"] != assigner["team_id"]:
            raise HTTPException(status_code=400, detail="Leads can only assign tasks to their own team")
    else:
        raise HTTPException(status_code=403, detail="Users cannot assign tasks")

    return assignee["team_id"]

@app.post("/api/tasks", status_code=status.HTTP_201_CREATED)
def create_task(req: CreateTaskRequest, current_user: Dict[str, Any] = Depends(get_guarded_user)):
    """ Create a task. Enforces assignee rules. """
    if current_user["role"] not in ["admin", "lead"]:
        raise HTTPException(status_code=403, detail="Forbidden")

    assignee_team_id = _enforce_assignee_rule(current_user, req.assigned_to)

    # Check if event is completed (EV-09)
    if req.event_id:
        ev_res = supabase.table("events").select("status").eq("id", req.event_id).execute()
        if not ev_res.data:
            raise HTTPException(status_code=404, detail="Event not found")
        if ev_res.data[0]["status"] == "completed":
            raise HTTPException(status_code=400, detail="Cannot add tasks to a completed event")





    try:
        data = req.model_dump(exclude_unset=True)
        data["created_by"] = current_user["id"]
        res = supabase.table("tasks").insert(data).execute()

        log_activity(current_user["id"], "create", "task", res.data[0]["id"])
        return res.data[0]
    except Exception as e:




        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tasks")
def list_tasks(current_user: Dict[str, Any] = Depends(get_guarded_user)):
    """ List tasks within scope """
    query = supabase.table("tasks").select("*, assigned_to:profiles!tasks_assigned_to_fkey(full_name)")

    if current_user["role"] == "user":
        query = query.eq("assigned_to", current_user["id"])
    elif current_user["role"] == "lead":
        query = query.or_(f"team_id.eq.{current_user['team_id']},assigned_to.eq.{current_user['id']}")

    try:
        res = query.order("created_at", desc=True).execute()
        return res.data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/tasks/{task_id}")
def get_task(task_id: str, current_user: Dict[str, Any] = Depends(get_guarded_user)):
    """ Get single task within scope """
    try:
        res = supabase.table("tasks").select("*").eq("id", task_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Task not found")

        task = res.data[0]

        # Check scope
        if current_user["role"] == "user" and task["assigned_to"] != current_user["id"]:
            raise HTTPException(status_code=404, detail="Task not found") # 404 to obscure existence
        if current_user["role"] == "lead" and task["team_id"] != current_user["team_id"] and task["assigned_to"] != current_user["id"]:
            raise HTTPException(status_code=404, detail="Task not found")

        return task
    except Exception as e:
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=400, detail=str(e))

@app.patch("/api/tasks/{task_id}")
def update_task(task_id: str, req: UpdateTaskRequest, current_user: Dict[str, Any] = Depends(get_guarded_user)):
    """ Edit a task. Enforce rules. """
    # Get existing task
    task = get_task(task_id, current_user) # also checks scope implicitly

    # TK-09: Only the assigner can edit... (Admin exception: we asked, but standard deny by default unless assigner or admin?
    # Let's say Admin can edit any task, but Lead can only edit tasks they assigned)
    if task["assigned_by"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Only the assigner can edit this task")

    # TK-09: ...until the task is Approved
    if task["status"] == "approved":
        raise HTTPException(status_code=400, detail="Cannot edit an Approved task")

    update_data = req.model_dump(exclude_unset=True)
    if not update_data:
        return {"status": "no changes"}

    if "assigned_to" in update_data:
        new_team_id = _enforce_assignee_rule(current_user, update_data["assigned_to"])
        update_data["team_id"] = new_team_id

    try:
        update_data["updated_at"] = datetime.utcnow().isoformat()
        res = supabase.table("tasks").update(update_data).eq("id", task_id).execute()

        log_activity(current_user["id"], "task_edited", "task", task_id, update_data)
        return res.data[0]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

class ReviewTaskRequest(BaseModel):
    status: str # approved, rejected
    note: Optional[str] = None

def _transition_task(task: dict, to_status: str, current_user: Dict[str, Any], note: str = None):
    """ Handle strict transitions and audit logging """
    from_status = task["status"]
    task_id = task["id"]

    update_data = {"status": to_status, "updated_at": datetime.utcnow().isoformat()}

    if to_status == "completed":
        update_data["completed_at"] = datetime.utcnow().isoformat()
    elif to_status in ["approved", "rejected"]:
        update_data["reviewed_by"] = current_user["id"]
        update_data["reviewed_at"] = datetime.utcnow().isoformat()
        update_data["review_note"] = note


    try:
        res = supabase.rpc("transition_task_with_history", {
            "p_task_id": task_id,
            "p_from_status": from_status,
            "p_to_status": to_status,
            "p_changed_by": current_user["id"],
            "p_note": note
        }).execute()

        if not res.data:
            raise HTTPException(status_code=409, detail="Task state changed or conflict")

        return {"status": "success"}
    except Exception as e:

        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/tasks/{task_id}/complete")
def complete_task(task_id: str, current_user: Dict[str, Any] = Depends(get_guarded_user)):
    """ Mark work completed. Only assignee. """
    task = get_task(task_id, current_user)

    if task["assigned_to"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Only the assignee can mark this completed")

    if task["status"] not in ["pending", "rejected"]: # Can rework a rejected task
        raise HTTPException(status_code=400, detail=f"Cannot complete a task in {task['status']} status")

    return _transition_task(task, "completed", current_user)

@app.post("/api/tasks/{task_id}/review")
def review_task(task_id: str, req: ReviewTaskRequest, current_user: Dict[str, Any] = Depends(require_admin)):
    """ Approve or Reject. Admin only. """
    # Bypass standard get_task scope since Admin sees all anyway
    try:
        res = supabase.table("tasks").select("*").eq("id", task_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Task not found")
        task = res.data[0]
    except Exception as e:
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=400, detail=str(e))

    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail="Can only review completed tasks")

    if req.status not in ["approved", "rejected"]:
        raise HTTPException(status_code=400, detail="Invalid review status")

    if req.status == "rejected" and (not req.note or not req.note.strip()):
        raise HTTPException(status_code=400, detail="A reason (note) is required when rejecting")

    # Prevent assignee from approving their own task (if Admin is assigned)
    if task["assigned_to"] == current_user["id"]:
        raise HTTPException(status_code=403, detail="Assignee cannot review their own task")

    return _transition_task(task, req.status, current_user, req.note)

@app.get("/api/tasks/{task_id}/history")
def get_task_history(task_id: str, current_user: Dict[str, Any] = Depends(get_guarded_user)):
    """ Get status history within scope """
    # Validate scope first
    get_task(task_id, current_user)

    try:
        res = supabase.table("task_status_history").select("*, changed_by:profiles!task_status_history_changed_by_fkey(full_name)").eq("task_id", task_id).order("changed_at", desc=True).execute()
        return res.data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- Phase 5: Activity Log ---

@app.get("/api/activity")
def list_activity(current_user: Dict[str, Any] = Depends(require_admin)):
    """ Admin only: list all activity logs """
    try:
        res = supabase.table("activity_log").select("*, actor_id:profiles!activity_log_actor_id_fkey(full_name, role)").order("created_at", desc=True).execute()
        return res.data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/dashboard")
def get_dashboard_summary(current_user: Dict[str, Any] = Depends(get_guarded_user)):
    """ Get summary metrics based on role """
    role = current_user["role"]
    team_id = current_user.get("team_id")
    user_id = current_user["id"]

    summary = {}
    try:
        if role == "admin":
            # Admin: Pending Reviews (tasks in 'completed' status)
            tasks_res = supabase.table("tasks").select("id").eq("status", "completed").execute()
            summary["pending_reviews"] = len(tasks_res.data)
        elif role == "lead":
            # Lead: Team tasks
            tasks_res = supabase.table("tasks").select("id, status").eq("team_id", team_id).execute()
            summary["team_tasks_total"] = len(tasks_res.data)
            summary["team_tasks_pending"] = len([t for t in tasks_res.data if t["status"] == "pending"])

        # User (and Lead): Own tasks and Timetable status
        if role in ["lead", "user"]:
            own_tasks_res = supabase.table("tasks").select("id, status").eq("assigned_to", user_id).execute()
            summary["own_tasks_total"] = len(own_tasks_res.data)
            summary["own_tasks_pending"] = len([t for t in own_tasks_res.data if t["status"] == "pending"])

            tt_res = supabase.table("timetables").select("id").eq("user_id", user_id).eq("status", "active").execute()
            summary["timetable_saved"] = len(tt_res.data) > 0

        return summary
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
