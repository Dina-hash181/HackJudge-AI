from datetime import datetime, timezone
import secrets
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends, Response, Request
from pydantic import BaseModel
from src.database import get_db
from src.auth import (
    hash_password,
    verify_password,
    create_session,
    get_current_user,
    get_optional_user
)
from src.config import (
    SESSION_ORGANIZER,
    SESSION_JUDGE_A,
    SESSION_JUDGE_B,
    SESSION_PARTICIPANT
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    full_name: str
    role: str = "participant" # 'participant' or 'judge'
    team_name: Optional[str] = None

class LoginRequest(BaseModel):
    username_or_email: str
    password: str

class SwitchDemoRequest(BaseModel):
    target: str # 'organizer', 'judge_a', 'judge_b', 'participant'

@router.post("/register")
def register(req: RegisterRequest, response: Response):
    username = req.username.strip().lower()
    email = req.email.strip().lower()
    role = req.role.lower()
    if role not in ("participant", "judge"):
        role = "participant"

    now_iso = datetime.now(timezone.utc).isoformat()
    user_id = f"usr_{secrets.token_hex(6)}"

    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM users WHERE username = ? OR email = ?",
            (username, email)
        ).fetchone()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with that username or email already exists."
            )

        conn.execute("""
            INSERT INTO users (id, username, email, password_hash, full_name, role, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, username, email, hash_password(req.password), req.full_name.strip(), role, now_iso))

        # If judge, create judge entry
        if role == "judge":
            jid = f"jdg_{secrets.token_hex(4)}"
            conn.execute("""
                INSERT INTO judges (id, user_id, name, email, tracks_json)
                VALUES (?, ?, ?, ?, '[]')
            """, (jid, user_id, req.full_name.strip(), email))

        # If participant with team_name, create team
        if role == "participant" and req.team_name:
            tmid = f"tm_{secrets.token_hex(4)}"
            code = f"INV-{tmid.upper()}-{req.team_name[:3].upper()}"
            conn.execute("""
                INSERT INTO teams (id, event_id, name, invite_code, leader_id, created_at)
                VALUES (?, 'evt_01', ?, ?, ?, ?)
            """, (tmid, req.team_name.strip(), code, user_id, now_iso))
            conn.execute("""
                INSERT INTO team_members (id, team_id, user_id, email, name, role, joined_at)
                VALUES (?, ?, ?, ?, ?, 'leader', ?)
            """, (f"mem_{secrets.token_hex(4)}", tmid, user_id, email, req.full_name.strip(), now_iso))

        token = secrets.token_hex(24)
        conn.execute(
            "INSERT OR REPLACE INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)",
            (token, user_id, now_iso)
        )
        response.set_cookie(
            key="session",
            value=token,
            httponly=True,
            samesite="lax",
            max_age=86400 * 7
        )

        return {
            "status": "success",
            "token": token,
            "user": {
                "id": user_id,
                "username": username,
                "email": email,
                "full_name": req.full_name,
                "role": role
            }
        }

@router.post("/login")
def login(req: LoginRequest, response: Response):
    ident = req.username_or_email.strip().lower()
    with get_db() as conn:
        user = conn.execute("""
            SELECT id, username, email, password_hash, full_name, role
            FROM users
            WHERE username = ? OR email = ?
        """, (ident, ident)).fetchone()

        valid = False
        if user:
            # Check cryptographic password hash
            if verify_password(user["password_hash"], req.password):
                valid = True
            # Also allow common demo credentials for seeded demo accounts
            elif user["username"] in ("organizer", "judge_a", "judge_b", "participant") and req.password in (
                "adminpassword", "judgepassword", "participantpassword", "dogfood2026", "password123", "password", "admin", "demo"
            ):
                valid = True

        if not user or not valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username/email or password."
            )

        token = secrets.token_hex(24)
        now_iso = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT OR REPLACE INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)",
            (token, user["id"], now_iso)
        )
        response.set_cookie(
            key="session",
            value=token,
            httponly=True,
            samesite="lax",
            max_age=86400 * 7
        )

        return {
            "status": "success",
            "token": token,
            "user": {
                "id": user["id"],
                "username": user["username"],
                "email": user["email"],
                "full_name": user["full_name"],
                "role": user["role"]
            }
        }

@router.post("/logout")
def logout(response: Response, user: dict = Depends(get_optional_user)):
    if user and "token" in user:
        with get_db() as conn:
            conn.execute("DELETE FROM sessions WHERE token = ?", (user["token"],))
    response.delete_cookie(key="session")
    return {"status": "success", "message": "Logged out successfully."}

@router.get("/me")
def get_me(user: dict = Depends(get_current_user)):
    with get_db() as conn:
        extra_info = {}
        # Fetch team info if participant
        if user["role"] == "participant":
            membership = conn.execute("""
                SELECT tm.team_id, tm.role as member_role, t.name as team_name, t.invite_code,
                       p.id as project_id, p.title as project_title, p.eligibility_status
                FROM team_members tm
                JOIN teams t ON tm.team_id = t.id
                LEFT JOIN projects p ON p.team_id = t.id
                WHERE tm.user_id = ? OR tm.email = ?
                LIMIT 1
            """, (user["id"], user["email"])).fetchone()
            if membership:
                extra_info["team"] = membership

        # Fetch judge info if judge
        elif user["role"] == "judge":
            j_info = conn.execute("""
                SELECT id as judge_id, name, email, tracks_json
                FROM judges
                WHERE user_id = ? OR email = ? OR id = ?
                LIMIT 1
            """, (user["id"], user["email"], user["username"])).fetchone()
            if j_info:
                extra_info["judge"] = j_info

        return {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "full_name": user["full_name"],
            "role": user["role"],
            "extra": extra_info
        }

@router.post("/switch-demo")
def switch_demo(req: SwitchDemoRequest, response: Response):
    """
    Fast demo helper allowing judges and reviewers to switch between
    Organizer, Judge A, Judge B, and Participant with 1 click.
    """
    token_map = {
        "organizer": SESSION_ORGANIZER,
        "judge_a": SESSION_JUDGE_A,
        "judge_b": SESSION_JUDGE_B,
        "participant": SESSION_PARTICIPANT
    }
    target = req.target.lower()
    token = token_map.get(target)
    if not token:
        raise HTTPException(status_code=400, detail="Invalid target role. Choose organizer, judge_a, judge_b, or participant.")

    with get_db() as conn:
        user = conn.execute("""
            SELECT u.id, u.username, u.email, u.full_name, u.role
            FROM sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.token = ?
        """, (token,)).fetchone()

        if not user:
            raise HTTPException(status_code=404, detail="Demo account not found in database.")

    response.set_cookie(
        key="session",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=86400 * 7
    )

    return {
        "status": "success",
        "switched_to": target,
        "token": token,
        "user": user
    }
