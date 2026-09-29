from datetime import datetime, timezone
import secrets
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from src.database import get_db
from src.auth import require_roles
from src.scoring import calculate_project_scores, get_judge_calibration_stats

router = APIRouter(prefix="/api/admin", tags=["Admin"], dependencies=[Depends(require_roles(["admin", "organizer"]))])

class EligibilityUpdateRequest(BaseModel):
    status: str # 'approved', 'rejected', 'pending'
    notes: Optional[str] = ""

class AssignmentRequest(BaseModel):
    judge_id: str
    project_id: str
    action: str = "assign" # 'assign' or 'unassign'

class AutoAssignRequest(BaseModel):
    reviews_per_project: int = 3

class EventSettingsRequest(BaseModel):
    name: Optional[str] = None
    submissions_close: Optional[str] = None
    results_published: Optional[int] = None
    is_archived: Optional[int] = None

class CriterionUpdateRequest(BaseModel):
    key: str
    name: str
    weight: float
    max_score: float = 5.0
    description: Optional[str] = ""

@router.get("/overview")
def get_admin_overview():
    with get_db() as conn:
        projects_count = conn.execute("SELECT COUNT(*) as c FROM projects").fetchone()["c"]
        teams_count = conn.execute("SELECT COUNT(*) as c FROM teams").fetchone()["c"]
        judges_count = conn.execute("SELECT COUNT(*) as c FROM judges").fetchone()["c"]
        scores_count = conn.execute("SELECT COUNT(*) as c FROM scores").fetchone()["c"]
        assignments_count = conn.execute("SELECT COUNT(*) as c FROM judge_assignments").fetchone()["c"]
        event = conn.execute("SELECT * FROM events WHERE id = 'evt_01'").fetchone()

        # AI stats
        ai_count = conn.execute("SELECT COUNT(*) as c FROM ai_evaluations").fetchone()["c"]
        avg_ai_row = conn.execute("SELECT AVG(overall_score) as a FROM ai_evaluations").fetchone()
        avg_ai_score = round(avg_ai_row["a"], 2) if avg_ai_row and avg_ai_row["a"] else 0.0

        avg_human_row = conn.execute("SELECT AVG(total_score) as a FROM scores").fetchone()
        avg_human_score = round(avg_human_row["a"], 2) if avg_human_row and avg_human_row["a"] else 0.0

        # Review completion rate
        completion_pct = round((scores_count / assignments_count * 100), 1) if assignments_count > 0 else 0.0

        # Eligibility breakdown
        eligibility = conn.execute("""
            SELECT eligibility_status, COUNT(*) as count
            FROM projects
            GROUP BY eligibility_status
        """).fetchall()

        # Track distribution
        track_dist = conn.execute("""
            SELECT COALESCE(trk.name, 'Unassigned') as track_name, COUNT(p.id) as project_count
            FROM projects p
            LEFT JOIN tracks trk ON p.track_id = trk.id
            GROUP BY p.track_id
        """).fetchall()

        return {
            "stats": {
                "projects": projects_count,
                "teams": teams_count,
                "judges": judges_count,
                "scores": scores_count,
                "assignments": assignments_count,
                "completion_pct": completion_pct,
                "ai_evaluated": ai_count,
                "avg_ai_score": avg_ai_score,
                "avg_human_score": avg_human_score
            },
            "event": event,
            "eligibility": eligibility,
            "track_distribution": track_dist
        }

@router.get("/submissions")
def get_admin_submissions(status_filter: Optional[str] = None, track_id: Optional[str] = None):
    with get_db() as conn:
        query = """
            SELECT p.*, t.name as team_name, trk.name as track_name,
                   (SELECT COUNT(*) FROM scores s WHERE s.project_id = p.id) as review_count,
                   (SELECT AVG(total_score) FROM scores s WHERE s.project_id = p.id) as avg_score
            FROM projects p
            JOIN teams t ON p.team_id = t.id
            LEFT JOIN tracks trk ON p.track_id = trk.id
            WHERE 1=1
        """
        params = []
        if status_filter:
            query += " AND p.eligibility_status = ?"
            params.append(status_filter)
        if track_id:
            query += " AND p.track_id = ?"
            params.append(track_id)

        query += " ORDER BY p.submitted_at DESC"
        projects = conn.execute(query, params).fetchall()

        for p in projects:
            p["avg_score"] = round(p["avg_score"], 2) if p["avg_score"] is not None else 0.0

        return {"count": len(projects), "projects": projects}

@router.post("/submissions/{project_id}/eligibility")
def update_project_eligibility(project_id: str, req: EligibilityUpdateRequest):
    with get_db() as conn:
        p = conn.execute("SELECT id, title FROM projects WHERE id = ?", (project_id,)).fetchone()
        if not p:
            raise HTTPException(status_code=404, detail="Project not found.")

        conn.execute("""
            UPDATE projects
            SET eligibility_status = ?, eligibility_notes = ?
            WHERE id = ?
        """, (req.status.lower(), req.notes, project_id))

        now_iso = datetime.now(timezone.utc).isoformat()
        conn.execute("""
            INSERT INTO audit_logs (id, user_id, action, entity_type, entity_id, details, created_at)
            VALUES (?, 'usr_organizer', 'ELIGIBILITY_UPDATE', 'PROJECT', ?, ?, ?)
        """, (f"audit_{secrets.token_hex(6)}", project_id, f"Eligibility changed to {req.status}. Note: {req.notes}", now_iso))

        return {"status": "success", "project_id": project_id, "new_status": req.status}

@router.get("/judges")
def get_admin_judges():
    with get_db() as conn:
        judges = conn.execute("""
            SELECT j.*,
                   (SELECT COUNT(*) FROM judge_assignments ja WHERE ja.judge_id = j.id) as assigned_count,
                   (SELECT COUNT(*) FROM scores s WHERE s.judge_id = j.id) as completed_count
            FROM judges j
            ORDER BY j.name ASC
        """).fetchall()
        return {"count": len(judges), "judges": judges}

@router.post("/assignments")
def manage_assignment(req: AssignmentRequest):
    with get_db() as conn:
        now_iso = datetime.now(timezone.utc).isoformat()
        if req.action == "assign":
            conn.execute("""
                INSERT OR IGNORE INTO judge_assignments (id, judge_id, project_id, assigned_at)
                VALUES (?, ?, ?, ?)
            """, (f"asgn_{req.judge_id}_{req.project_id}", req.judge_id, req.project_id, now_iso))
            msg = "Assigned"
        else:
            conn.execute("""
                DELETE FROM judge_assignments WHERE judge_id = ? AND project_id = ?
            """, (req.judge_id, req.project_id))
            msg = "Unassigned"

        return {"status": "success", "message": f"{msg} judge {req.judge_id} for project {req.project_id}."}

@router.post("/assignments/auto")
def auto_assign_judges(req: AutoAssignRequest):
    """
    Intelligent judge assignment algorithm:
    Distributes projects across judges according to track match and balances judge review loads.
    """
    import json
    with get_db() as conn:
        projects = conn.execute("SELECT id, track_id FROM projects WHERE eligibility_status = 'approved'").fetchall()
        judges = conn.execute("SELECT id, tracks_json FROM judges").fetchall()

        if not judges or not projects:
            return {"status": "error", "message": "No judges or approved projects available."}

        now_iso = datetime.now(timezone.utc).isoformat()
        added_count = 0

        # Map judge track affinity
        judge_track_map = {}
        judge_load = {}
        for j in judges:
            jid = j["id"]
            try:
                tracks = json.loads(j["tracks_json"])
            except Exception:
                tracks = []
            judge_track_map[jid] = set(tracks)
            # Existing load
            curr = conn.execute("SELECT COUNT(*) as c FROM judge_assignments WHERE judge_id = ?", (jid,)).fetchone()["c"]
            judge_load[jid] = curr

        for p in projects:
            pid = p["id"]
            ptrk = p["track_id"]
            # Current assignments for this project
            existing_assigned = set(
                row["judge_id"] for row in conn.execute(
                    "SELECT judge_id FROM judge_assignments WHERE project_id = ?", (pid,)
                ).fetchall()
            )
            needed = max(0, req.reviews_per_project - len(existing_assigned))

            if needed > 0:
                # Rank available judges by track match, then by lowest load
                candidates = [j["id"] for j in judges if j["id"] not in existing_assigned]
                candidates.sort(key=lambda jid: (
                    -1 if ptrk in judge_track_map.get(jid, set()) else 0, # match track first
                    judge_load.get(jid, 0) # least loaded first
                ))

                chosen = candidates[:needed]
                for jid in chosen:
                    conn.execute("""
                        INSERT OR IGNORE INTO judge_assignments (id, judge_id, project_id, assigned_at)
                        VALUES (?, ?, ?, ?)
                    """, (f"asgn_{jid}_{pid}", jid, pid, now_iso))
                    judge_load[jid] = judge_load.get(jid, 0) + 1
                    added_count += 1

        return {
            "status": "success",
            "message": f"Successfully created {added_count} new assignments across {len(projects)} projects."
        }

@router.get("/criteria")
def get_criteria():
    with get_db() as conn:
        criteria = conn.execute("SELECT * FROM criteria WHERE event_id = 'evt_01'").fetchall()
        return {"criteria": criteria}

@router.post("/criteria")
def update_criterion(req: CriterionUpdateRequest):
    with get_db() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO criteria (id, event_id, key, name, weight, max_score, description)
            VALUES (?, 'evt_01', ?, ?, ?, ?, ?)
        """, (f"crit_{req.key}", req.key, req.name, req.weight, req.max_score, req.description))
        return {"status": "success", "message": f"Criterion {req.name} updated."}

@router.get("/calibration")
def get_calibration():
    stats = get_judge_calibration_stats("evt_01")
    return {"calibration": stats}

@router.post("/event/settings")
def update_event_settings(req: EventSettingsRequest):
    with get_db() as conn:
        updates = []
        params = []
        if req.name is not None:
            updates.append("name = ?")
            params.append(req.name)
        if req.submissions_close is not None:
            updates.append("submissions_close = ?")
            params.append(req.submissions_close)
        if req.results_published is not None:
            updates.append("results_published = ?")
            params.append(req.results_published)
        if req.is_archived is not None:
            updates.append("is_archived = ?")
            params.append(req.is_archived)

        if updates:
            params.append("evt_01")
            conn.execute(f"UPDATE events SET {', '.join(updates)} WHERE id = ?", params)

        now_iso = datetime.now(timezone.utc).isoformat()
        conn.execute("""
            INSERT INTO audit_logs (id, user_id, action, entity_type, entity_id, details, created_at)
            VALUES (?, 'usr_organizer', 'EVENT_CONFIG_UPDATE', 'EVENT', 'evt_01', ?, ?)
        """, (f"audit_{secrets.token_hex(6)}", str(req.model_dump(exclude_none=True)), now_iso))

        event = conn.execute("SELECT * FROM events WHERE id = 'evt_01'").fetchone()
        return {"status": "success", "event": event}

@router.get("/audit-logs")
def get_audit_logs(limit: int = 50):
    with get_db() as conn:
        logs = conn.execute("""
            SELECT a.*, u.full_name as user_name, u.role as user_role
            FROM audit_logs a
            LEFT JOIN users u ON a.user_id = u.id
            ORDER BY a.created_at DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return {"logs": logs}
