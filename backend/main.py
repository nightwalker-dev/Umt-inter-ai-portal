from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from typing import Optional
import jwt # Note: Needs pyjwt or python-jose
from datetime import datetime

app = FastAPI(title="Inter Club Portal API")

# Setup CORS - deny by default, allow only specific origins
origins = [
    os.getenv("FRONTEND_URL", "http://localhost:3000"),
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# Authentication and Authorization stubs for Phase 0
# To be replaced with actual Supabase JWT validation and DB lookups
async def get_current_user(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = auth_header.split(" ")[1]
    # STUB: we would decode the token using Supabase JWT secret
    # and fetch the profile.
    # For Phase 0 compilation, returning a mock user.
    return {"id": "mock_id", "role": "admin", "is_active": True}

async def require_role(role: str, current_user = Depends(get_current_user)):
    if current_user.get("role") != role:
        raise HTTPException(status_code=403, detail="Forbidden")
    return current_user

async def require_active_user(current_user = Depends(get_current_user)):
    if not current_user.get("is_active"):
        raise HTTPException(status_code=403, detail="Deactivated user")
    return current_user

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

@app.get("/api/me", dependencies=[Depends(require_active_user)])
def get_me(current_user = Depends(get_current_user)):
    return {"profile": current_user}

@app.post("/api/auth/first-password")
def first_password(current_user = Depends(get_current_user)):
    return {"message": "password change flow not fully implemented yet"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
