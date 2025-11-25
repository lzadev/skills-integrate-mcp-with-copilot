"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
import json
import uuid
from pathlib import Path
from threading import Lock

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


# Simple in-memory admin sessions (token -> username)
_sessions = {}
_sessions_lock = Lock()


def _load_teachers():
    """Load teachers' credentials from `teachers.json` next to this file.
    The file format is expected to be:
    {"teachers": [{"username": "teacher1", "password": "secret"}, ...]}
    """
    try:
        p = Path(__file__).parent / "teachers.json"
        if not p.exists():
            return []
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("teachers", [])
    except Exception:
        return []


TEACHERS = _load_teachers()


def _check_admin_token(authorization: str | None) -> bool:
    """Check Authorization header of form: 'Bearer <token>' and validate session."""
    if not authorization:
        return False
    if not authorization.lower().startswith("bearer "):
        return False
    token = authorization.split(" ", 1)[1].strip()
    with _sessions_lock:
        return token in _sessions


def _create_session(username: str) -> str:
    token = uuid.uuid4().hex
    with _sessions_lock:
        _sessions[token] = username
    return token


def _destroy_session(token: str) -> None:
    with _sessions_lock:
        _sessions.pop(token, None)



class _LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/admin/login")
def admin_login(req: _LoginRequest):
    """Authenticate a teacher and return a short-lived token.

    The token is a simple UUID returned in JSON: {"token": "..."}.
    This is intentionally minimal for the exercise; consider stronger
    authentication in production.
    """
    for t in TEACHERS:
        if t.get("username") == req.username and t.get("password") == req.password:
            token = _create_session(req.username)
            return {"token": token}
    raise HTTPException(status_code=401, detail="Invalid username or password")


@app.post("/admin/logout")
def admin_logout(authorization: str | None = Header(None)):
    """Invalidate an admin session token provided via `Authorization: Bearer <token>`."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=400, detail="Missing or invalid Authorization header")
    token = authorization.split(" ", 1)[1].strip()
    _destroy_session(token)
    return {"message": "Logged out"}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str, authorization: str | None = Header(None)):
    """Sign up a student for an activity.

    This action is restricted to authenticated teachers (Admin Mode).
    Provide header `Authorization: Bearer <token>` obtained from `/admin/login`.
    """
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Require admin
    if not _check_admin_token(authorization):
        raise HTTPException(status_code=403, detail="Admin credentials required to sign up students")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str, authorization: str | None = Header(None)):
    """Unregister a student from an activity.

    This action is restricted to authenticated teachers (Admin Mode).
    Provide header `Authorization: Bearer <token>` obtained from `/admin/login`.
    """
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Require admin
    if not _check_admin_token(authorization):
        raise HTTPException(status_code=403, detail="Admin credentials required to unregister students")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}