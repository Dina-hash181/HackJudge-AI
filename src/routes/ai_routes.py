from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, status, Depends, Request
from pydantic import BaseModel
from src.database import get_db
from src.auth import get_current_user, require_roles
from src.ai_judging import evaluate_project_with_ai, get_ai_evaluation_for_project, batch_evaluate_all_projects
from src.scoring import calculate_project_scores

router = APIRouter(prefix="/api/ai", tags=["AI Judging"])

class UpdateWeightsRequest(BaseModel):
    human_weight: float
    ai_weight: float
    ai_judging_enabled: Optional[bool] = True

@router.get("/overview")
def get_ai_overview(user: dict = Depends(get_current_user)):
    """Summary metrics of AI and human judging progress and comparison."""
    # Judges and admins can view AI overview
    if user["role"] not in ("judge", "admin", "organizer"):
        raise HTTPException(status_code=403, detail="Judging or admin role required.")

    with get_db() as conn:
        total_projects = conn.execute("SELECT COUNT(*) as c FROM projects").fetchone()["c"]
        ai_evaluated_count = conn.execute("SELECT COUNT(*) as c FROM ai_evaluations").fetchone()["c"]
        human_evaluated_count = conn.execute("SELECT COUNT(DISTINCT project_id) as c FROM scores").fetchone()["c"]
        
        avg_ai_row = conn.execute("SELECT AVG(overall_score) as a FROM ai_evaluations").fetchone()
        avg_ai_score = round(avg_ai_row["a"], 2) if avg_ai_row and avg_ai_row["a"] else 0.0

        avg_human_row = conn.execute("SELECT AVG(total_score) as a FROM scores").fetchone()
        avg_human_score = round(avg_human_row["a"], 2) if avg_human_row and avg_human_row["a"] else 0.0

        event = conn.execute("SELECT human_weight, ai_weight, ai_judging_enabled FROM events WHERE id = 'evt_01'").fetchone()

    # Calculate divergence count
    results = calculate_project_scores("evt_01")
    divergent_count = sum(1 for r in results if r["is_divergent"])

    return {
        "total_projects": total_projects,
        "ai_evaluated_count": ai_evaluated_count,
        "human_evaluated_count": human_evaluated_count,
        "ai_completion_pct": round(ai_evaluated_count / total_projects * 100, 1) if total_projects else 0.0,
        "human_completion_pct": round(human_evaluated_count / total_projects * 100, 1) if total_projects else 0.0,
        "avg_ai_score": avg_ai_score,
        "avg_human_score": avg_human_score,
        "divergent_count": divergent_count,
        "weights": {
            "human": event["human_weight"] if event else 0.80,
            "ai": event["ai_weight"] if event else 0.20,
            "enabled": bool(event["ai_judging_enabled"]) if event else True
        }
    }

@router.get("/evaluations")
def get_ai_evaluations(
    track: Optional[str] = None,
    filter_diff: Optional[str] = "all", # 'all', 'divergent', 'ai_higher', 'human_higher'
    search: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """List of all projects with their AI score, human score, and difference."""
    if user["role"] not in ("judge", "admin", "organizer"):
        raise HTTPException(status_code=403, detail="Judging or admin access required.")

    results = calculate_project_scores("evt_01")

    filtered = []
    for r in results:
        # Search
        if search:
            q = search.lower()
            if q not in r["project_title"].lower() and q not in r["team_name"].lower():
                continue
        # Track filter
        if track and track.lower() != "all":
            if r["track_name"].lower() != track.lower() and r["track_name"] != track:
                continue

        # Difference filter
        if filter_diff == "divergent" and not r["is_divergent"]:
            continue
        elif filter_diff == "ai_higher" and (r["ai_score"] is None or r["score_diff"] <= 0):
            continue
        elif filter_diff == "human_higher" and (r["ai_score"] is None or r["score_diff"] >= 0):
            continue

        filtered.append(r)

    return {
        "total": len(filtered),
        "evaluations": filtered
    }

@router.get("/evaluations/{project_id}")
def get_single_ai_evaluation(project_id: str, user: dict = Depends(get_current_user)):
    """Full detailed breakdown of an AI evaluation for a specific project."""
    if user["role"] not in ("judge", "admin", "organizer"):
        raise HTTPException(status_code=403, detail="Judging or admin access required.")

    eval_data = get_ai_evaluation_for_project(project_id)
    if not eval_data:
        raise HTTPException(status_code=404, detail="AI evaluation not found for this project.")

    with get_db() as conn:
        project = conn.execute("""
            SELECT p.*, t.name as team_name, trk.name as track_name,
                   (SELECT AVG(total_score) FROM scores s WHERE s.project_id = p.id) as avg_human_score,
                   (SELECT COUNT(*) FROM scores s WHERE s.project_id = p.id) as human_review_count
            FROM projects p
            JOIN teams t ON p.team_id = t.id
            LEFT JOIN tracks trk ON p.track_id = trk.id
            WHERE p.id = ?
        """, (project_id,)).fetchone()

    return {
        "evaluation": eval_data,
        "project": project
    }

@router.post("/evaluate/{project_id}")
def run_ai_evaluation(project_id: str, user: dict = Depends(get_current_user)):
    """Triggers on-demand AI evaluation for a project."""
    if user["role"] not in ("judge", "admin", "organizer"):
        raise HTTPException(status_code=403, detail="Judging or admin access required.")

    try:
        res = evaluate_project_with_ai(project_id)
        return {
            "status": "success",
            "message": f"AI evaluation completed for {project_id}.",
            "evaluation": res
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/batch-evaluate")
def run_batch_evaluation(user: dict = Depends(require_roles(["admin", "organizer"]))):
    """Triggers AI evaluation across all projects in the event."""
    count = batch_evaluate_all_projects("evt_01")
    return {
        "status": "success",
        "message": f"AI evaluation successfully completed for {count} projects.",
        "count": count
    }

@router.post("/weights")
def update_scoring_weights(req: UpdateWeightsRequest, user: dict = Depends(require_roles(["admin", "organizer"]))):
    """Updates the transparent Human vs AI scoring balance."""
    if req.human_weight < 0 or req.ai_weight < 0 or (req.human_weight + req.ai_weight == 0):
        raise HTTPException(status_code=400, detail="Invalid weight parameters. Weights must be non-negative and sum to > 0.")

    with get_db() as conn:
        conn.execute("""
            UPDATE events
            SET human_weight = ?, ai_weight = ?, ai_judging_enabled = ?
            WHERE id = 'evt_01'
        """, (req.human_weight, req.ai_weight, 1 if req.ai_judging_enabled else 0))

    return {
        "status": "success",
        "human_weight": req.human_weight,
        "ai_weight": req.ai_weight,
        "ai_judging_enabled": req.ai_judging_enabled
    }
