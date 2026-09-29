from datetime import datetime, timezone
import secrets
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, status, Depends, Request
from pydantic import BaseModel
from src.database import get_db
from src.auth import get_current_user

router = APIRouter(tags=["Judging"])

class EvaluationRequest(BaseModel):
    project_id: str
    criterion_scores: Dict[str, float] # e.g. {"functionality": 4.5, "innovation": 4.0, "quality": 5.0}
    comment: Optional[str] = ""

def resolve_judge_id(conn, user: dict) -> Optional[str]:
    """Helper to resolve the judge table ID from user profile."""
    row = conn.execute("""
        SELECT id FROM judges
        WHERE user_id = ? OR email = ? OR id = ?
        LIMIT 1
    """, (user["id"], user["email"], user["username"])).fetchone()
    return row["id"] if row else None

@router.get("/api/judge/scores")
def get_judge_scores(
    request: Request,
    judge: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """
    Dogfood Spec Route (T2):
    - Judge sees own scores (returns 200)
    - Judge cannot see peer scores (returns 403 Forbidden)
    - Participant is not a judge (returns 403 Forbidden)
    """
    # 1. Enforce that participant cannot access judge scores
    user_role = user.get("role")
    if user_role not in ("judge", "admin", "organizer"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Only judges and organizers may access judge scoring records."
        )

    with get_db() as conn:
        current_judge_id = resolve_judge_id(conn, user)

        # If a specific judge was requested via query param (e.g. ?judge=judge_a or ?judge=jdg_01):
        if judge:
            # Map username/id aliases
            requested_clean = judge.strip().lower()
            # Find the target judge ID
            target_judge = conn.execute("""
                SELECT id FROM judges
                WHERE LOWER(id) = ? OR LOWER(email) = ? OR LOWER(name) = ?
                LIMIT 1
            """, (requested_clean, requested_clean, requested_clean)).fetchone()

            target_id = target_judge["id"] if target_judge else requested_clean

            # Role Isolation Check: If logged in as judge, you CANNOT read another judge's scores!
            if user_role == "judge":
                # Check if target matches own judge ID or username
                is_self = (
                    (current_judge_id and target_id == current_judge_id) or
                    (user["username"].lower() == requested_clean)
                )
                if not is_self:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied: Role isolation prevents viewing peer judge evaluations."
                    )
            query_judge_id = target_id
        else:
            # Defaults to current judge's own scores
            query_judge_id = current_judge_id or user.get("id")

        scores = conn.execute("""
            SELECT s.id, s.project_id, s.total_score, s.comment, s.submitted_at,
                   p.title as project_title, t.name as team_name
            FROM scores s
            JOIN projects p ON s.project_id = p.id
            JOIN teams t ON p.team_id = t.id
            WHERE s.judge_id = ?
        """, (query_judge_id,)).fetchall()

        return {
            "status": "success",
            "judge_id": query_judge_id,
            "count": len(scores),
            "scores": scores
        }

@router.get("/api/judge/assigned")
def get_assigned_projects(user: dict = Depends(get_current_user)):
    user_role = user.get("role")
    if user_role not in ("judge", "admin", "organizer"):
        raise HTTPException(status_code=403, detail="Judging access required.")

    with get_db() as conn:
        judge_id = resolve_judge_id(conn, user)
        if not judge_id:
            return {"assigned": [], "message": "Judge profile not linked."}

        projects = conn.execute("""
            SELECT p.id as project_id, p.title, p.summary, p.technologies,
                   p.repo_url, p.demo_url, t.name as team_name, trk.name as track_name,
                   ja.assigned_at, s.total_score as my_score, s.comment as my_comment,
                   s.submitted_at as scored_at
            FROM judge_assignments ja
            JOIN projects p ON ja.project_id = p.id
            JOIN teams t ON p.team_id = t.id
            LEFT JOIN tracks trk ON p.track_id = trk.id
            LEFT JOIN scores s ON s.project_id = p.id AND s.judge_id = ja.judge_id
            WHERE ja.judge_id = ?
            ORDER BY ja.assigned_at DESC
        """, (judge_id,)).fetchall()

        # Rubric criteria
        criteria = conn.execute("SELECT key, name, weight, max_score, description FROM criteria WHERE event_id = 'evt_01'").fetchall()

        return {
            "judge_id": judge_id,
            "assigned_count": len(projects),
            "completed_count": sum(1 for p in projects if p["my_score"] is not None),
            "projects": projects,
            "criteria": criteria
        }

@router.get("/api/judge/project/{project_id}")
def get_judge_project_details(project_id: str, user: dict = Depends(get_current_user)):
    user_role = user.get("role")
    if user_role not in ("judge", "admin", "organizer"):
        raise HTTPException(status_code=403, detail="Judging access required.")

    with get_db() as conn:
        judge_id = resolve_judge_id(conn, user)

        # Check assignment if judge (admin can view any)
        if user_role == "judge":
            assignment = conn.execute("""
                SELECT id FROM judge_assignments WHERE judge_id = ? AND project_id = ?
            """, (judge_id, project_id)).fetchone()
            if not assignment:
                # Allow previewing if in active judging window
                pass

        proj = conn.execute("""
            SELECT p.*, t.name as team_name, trk.name as track_name
            FROM projects p
            JOIN teams t ON p.team_id = t.id
            LEFT JOIN tracks trk ON p.track_id = trk.id
            WHERE p.id = ?
        """, (project_id,)).fetchone()

        if not proj:
            raise HTTPException(status_code=404, detail="Project not found.")

        # Existing score by this judge
        existing_score = None
        if judge_id:
            existing_score = conn.execute("""
                SELECT id, total_score, comment, submitted_at, updated_at
                FROM scores
                WHERE judge_id = ? AND project_id = ?
            """, (judge_id, project_id)).fetchone()

            if existing_score:
                crit_scores = conn.execute("""
                    SELECT criterion_key, score FROM criterion_scores WHERE score_id = ?
                """, (existing_score["id"],)).fetchall()
                existing_score["criteria"] = {cs["criterion_key"]: cs["score"] for cs in crit_scores}

        criteria = conn.execute("SELECT key, name, weight, max_score, description FROM criteria WHERE event_id = 'evt_01'").fetchall()

        return {
            "project": proj,
            "existing_score": existing_score,
            "criteria": criteria
        }

@router.post("/api/judge/evaluate")
def evaluate_project(req: EvaluationRequest, user: dict = Depends(get_current_user)):
    user_role = user.get("role")
    if user_role not in ("judge", "admin", "organizer"):
        raise HTTPException(status_code=403, detail="Judging access required.")

    with get_db() as conn:
        judge_id = resolve_judge_id(conn, user)
        if not judge_id:
            raise HTTPException(status_code=400, detail="No judge record associated with this account.")

        # Fetch criteria to calculate weighted score
        criteria = conn.execute("SELECT key, weight, max_score FROM criteria WHERE event_id = 'evt_01'").fetchall()
        crit_map = {c["key"]: c for c in criteria}

        total_weighted = 0.0
        total_weight = 0.0

        for key, val in req.criterion_scores.items():
            c_info = crit_map.get(key)
            weight = c_info["weight"] if c_info else 1.0
            max_s = c_info["max_score"] if c_info else 5.0
            
            # Validation
            clean_val = max(0.0, min(max_s, float(val)))
            total_weighted += clean_val * weight
            total_weight += weight

        final_total = round(total_weighted / total_weight, 2) if total_weight > 0 else 3.0

        now_iso = datetime.now(timezone.utc).isoformat()
        score_id = f"sc_{judge_id}_{req.project_id}"

        # Audit log comparison
        prev_score = conn.execute("SELECT total_score FROM scores WHERE id = ?", (score_id,)).fetchone()
        old_val = prev_score["total_score"] if prev_score else None

        conn.execute("""
            INSERT OR REPLACE INTO scores (id, judge_id, project_id, total_score, comment, submitted_at, updated_at)
            VALUES (?, ?, ?, ?, ?, COALESCE((SELECT submitted_at FROM scores WHERE id = ?), ?), ?)
        """, (score_id, judge_id, req.project_id, final_total, req.comment, score_id, now_iso, now_iso))

        # Insert criterion breakdown
        for key, val in req.criterion_scores.items():
            cs_id = f"cs_{score_id}_{key}"
            conn.execute("""
                INSERT OR REPLACE INTO criterion_scores (id, score_id, criterion_key, score)
                VALUES (?, ?, ?, ?)
            """, (cs_id, score_id, key, float(val)))

        # Ensure assignment exists
        conn.execute("""
            INSERT OR IGNORE INTO judge_assignments (id, judge_id, project_id, assigned_at)
            VALUES (?, ?, ?, ?)
        """, (f"asgn_{judge_id}_{req.project_id}", judge_id, req.project_id, now_iso))

        # Audit log
        action = "SCORE_UPDATE" if old_val is not None else "SCORE_SUBMIT"
        conn.execute("""
            INSERT INTO audit_logs (id, user_id, action, entity_type, entity_id, details, created_at)
            VALUES (?, ?, ?, 'SCORE', ?, ?, ?)
        """, (
            f"audit_{secrets.token_hex(6)}",
            user["id"],
            action,
            score_id,
            f"Judge {judge_id} scored project {req.project_id}: {old_val} -> {final_total}. Comment: {req.comment}",
            now_iso
        ))

        return {
            "status": "success",
            "score_id": score_id,
            "total_score": final_total,
            "message": "Evaluation recorded successfully."
        }
