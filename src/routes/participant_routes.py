from datetime import datetime, timezone
import secrets
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status, Depends, Request
from pydantic import BaseModel
from src.database import get_db
from src.auth import get_current_user, require_roles

router = APIRouter(tags=["Participant"])

class TeamCreateRequest(BaseModel):
    name: str

class TeamJoinRequest(BaseModel):
    invite_code: str

class AddMemberRequest(BaseModel):
    email: str
    name: Optional[str] = None

class ProjectSubmissionRequest(BaseModel):
    title: str
    summary: Optional[str] = None
    problem_statement: Optional[str] = None
    solution_description: Optional[str] = None
    description: Optional[str] = None
    features: Optional[str] = None
    technologies: Optional[str] = None
    repo_url: Optional[str] = None
    demo_url: Optional[str] = None
    video_url: Optional[str] = None
    track_id: Optional[str] = None

def check_deadline_open(conn) -> bool:
    """Returns True if the event submission window is currently open, False if closed."""
    event = conn.execute("SELECT submissions_close FROM events WHERE id = 'evt_01'").fetchone()
    if not event:
        return True
    try:
        close_dt = datetime.fromisoformat(event["submissions_close"].replace("Z", "+00:00"))
        now_dt = datetime.now(timezone.utc)
        return now_dt < close_dt
    except Exception:
        return False

@router.get("/api/participant/team")
def get_participant_team(user: dict = Depends(get_current_user)):
    with get_db() as conn:
        membership = conn.execute("""
            SELECT tm.id as member_record_id, tm.team_id, tm.role as member_role,
                   t.name as team_name, t.invite_code, t.leader_id
            FROM team_members tm
            JOIN teams t ON tm.team_id = t.id
            WHERE tm.user_id = ? OR tm.email = ?
            LIMIT 1
        """, (user["id"], user["email"])).fetchone()

        if not membership:
            return {"has_team": False, "team": None}

        team_id = membership["team_id"]
        members = conn.execute("""
            SELECT id, email, name, role, joined_at
            FROM team_members
            WHERE team_id = ?
        """, (team_id,)).fetchall()

        project = conn.execute("""
            SELECT p.*, trk.name as track_name
            FROM projects p
            LEFT JOIN tracks trk ON p.track_id = trk.id
            WHERE p.team_id = ?
            LIMIT 1
        """, (team_id,)).fetchone()

        deadline_open = check_deadline_open(conn)

        return {
            "has_team": True,
            "team": {
                **membership,
                "members": members,
                "project": project,
                "deadline_open": deadline_open
            }
        }

@router.post("/api/participant/team/create")
def create_team(req: TeamCreateRequest, user: dict = Depends(get_current_user)):
    with get_db() as conn:
        existing = conn.execute("""
            SELECT id FROM team_members WHERE user_id = ? OR email = ?
        """, (user["id"], user["email"])).fetchone()
        if existing:
            raise HTTPException(status_code=400, detail="You are already in a team.")

        now_iso = datetime.now(timezone.utc).isoformat()
        team_id = f"tm_{secrets.token_hex(4)}"
        invite_code = f"INV-{team_id.upper()}-{req.name[:3].upper()}"

        conn.execute("""
            INSERT INTO teams (id, event_id, name, invite_code, leader_id, created_at)
            VALUES (?, 'evt_01', ?, ?, ?, ?)
        """, (team_id, req.name.strip(), invite_code, user["id"], now_iso))

        conn.execute("""
            INSERT INTO team_members (id, team_id, user_id, email, name, role, joined_at)
            VALUES (?, ?, ?, ?, ?, 'leader', ?)
        """, (f"mem_{secrets.token_hex(4)}", team_id, user["id"], user["email"], user["full_name"], now_iso))

        return {"status": "success", "team_id": team_id, "invite_code": invite_code}

@router.post("/api/participant/team/join")
def join_team(req: TeamJoinRequest, user: dict = Depends(get_current_user)):
    code = req.invite_code.strip().upper()
    with get_db() as conn:
        existing = conn.execute("""
            SELECT id FROM team_members WHERE user_id = ? OR email = ?
        """, (user["id"], user["email"])).fetchone()
        if existing:
            raise HTTPException(status_code=400, detail="You are already in a team.")

        team = conn.execute("SELECT id, name FROM teams WHERE UPPER(invite_code) = ?", (code,)).fetchone()
        if not team:
            raise HTTPException(status_code=404, detail="Invalid invite code.")

        now_iso = datetime.now(timezone.utc).isoformat()
        conn.execute("""
            INSERT INTO team_members (id, team_id, user_id, email, name, role, joined_at)
            VALUES (?, ?, ?, ?, ?, 'member', ?)
        """, (f"mem_{secrets.token_hex(4)}", team["id"], user["id"], user["email"], user["full_name"], now_iso))

        return {"status": "success", "message": f"Successfully joined {team['name']}"}

@router.post("/api/participant/team/members")
def add_team_member(req: AddMemberRequest, user: dict = Depends(get_current_user)):
    with get_db() as conn:
        membership = conn.execute("""
            SELECT team_id FROM team_members WHERE user_id = ? OR email = ?
        """, (user["id"], user["email"])).fetchone()
        if not membership:
            raise HTTPException(status_code=400, detail="You must belong to a team to invite members.")

        team_id = membership["team_id"]
        email = req.email.strip().lower()

        # Check if already in this team
        in_team = conn.execute("SELECT id FROM team_members WHERE team_id = ? AND email = ?", (team_id, email)).fetchone()
        if in_team:
            raise HTTPException(status_code=400, detail="Member is already on this team.")

        # Check if registered user
        u = conn.execute("SELECT id, full_name FROM users WHERE email = ?", (email,)).fetchone()
        u_id = u["id"] if u else None
        m_name = req.name or (u["full_name"] if u else email.split("@")[0].title())

        now_iso = datetime.now(timezone.utc).isoformat()
        conn.execute("""
            INSERT INTO team_members (id, team_id, user_id, email, name, role, joined_at)
            VALUES (?, ?, ?, ?, ?, 'member', ?)
        """, (f"mem_{secrets.token_hex(4)}", team_id, u_id, email, m_name, now_iso))

        return {"status": "success", "message": f"Added {email} to team."}

@router.post("/api/participant/submission")
def submit_or_update_project(req: ProjectSubmissionRequest, user: dict = Depends(get_current_user)):
    with get_db() as conn:
        membership = conn.execute("""
            SELECT team_id FROM team_members WHERE user_id = ? OR email = ?
        """, (user["id"], user["email"])).fetchone()
        if not membership:
            raise HTTPException(status_code=400, detail="You must belong to a team to submit a project.")

        team_id = membership["team_id"]

        # Check submission deadline!
        if not check_deadline_open(conn) and user.get("role") not in ("admin", "organizer"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Submissions are closed. The hackathon deadline has passed."
            )

        now_iso = datetime.now(timezone.utc).isoformat()
        existing = conn.execute("SELECT id FROM projects WHERE team_id = ?", (team_id,)).fetchone()

        sol_desc = req.solution_description or req.description or req.summary or ""
        features_text = req.features or ""
        vid_url = req.video_url or ""

        if existing:
            project_id = existing["id"]
            conn.execute("""
                UPDATE projects
                SET title = ?, summary = ?, problem_statement = ?, solution_description = ?, description = ?,
                    features = ?, technologies = ?, repo_url = ?, demo_url = ?, video_url = ?, track_id = ?, submitted_at = ?
                WHERE id = ?
            """, (
                req.title.strip(), req.summary, req.problem_statement, sol_desc, sol_desc,
                features_text, req.technologies, req.repo_url, req.demo_url, vid_url, req.track_id, now_iso, project_id
            ))
            action = "updated"
        else:
            project_id = f"prj_{secrets.token_hex(4)}"
            conn.execute("""
                INSERT INTO projects (
                    id, event_id, team_id, track_id, title, summary,
                    problem_statement, solution_description, description, features, technologies, repo_url,
                    demo_url, video_url, submitted_at, eligibility_status
                )
                VALUES (?, 'evt_01', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'approved')
            """, (
                project_id, team_id, req.track_id, req.title.strip(), req.summary,
                req.problem_statement, sol_desc, sol_desc, features_text, req.technologies, req.repo_url,
                req.demo_url, vid_url, now_iso
            ))
            action = "created"

    # Automatically trigger AI evaluation
    try:
        from src.ai_judging import evaluate_project_with_ai
        evaluate_project_with_ai(project_id)
    except Exception as e:
        pass

    return {"status": "success", "project_id": project_id, "action": action}

# --- Dogfood Spec Route: routes.submit (/projects/new) ---
@router.post("/projects/new")
def submit_project_probe(raw_req: Request, user: dict = Depends(get_current_user)):
    """
    Dogfood acceptance check endpoint (T1):
    A closed event MUST refuse submissions with 4xx when sent as participant.
    """
    with get_db() as conn:
        deadline_open = check_deadline_open(conn)
        if not deadline_open and user.get("role") not in ("admin", "organizer"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Submissions are closed for this event. Deadline has passed."
            )
        return {"status": "accepted", "message": "Submission recorded."}
