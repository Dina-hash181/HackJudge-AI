import math
from typing import Dict, List, Any, Tuple, Optional
from src.database import get_db

def calculate_project_scores(event_id: str = "evt_01") -> List[Dict[str, Any]]:
    """
    Computes human scores (raw & Z-score normalized), AI-assisted scores,
    and the final blended score according to the event's configured weights.
    Returns sorted list by final_score descending, with rank.
    """
    with get_db() as conn:
        # Fetch event weights
        event = conn.execute("""
            SELECT human_weight, ai_weight, ai_judging_enabled
            FROM events
            WHERE id = ?
        """, (event_id,)).fetchone()

        w_human = float(event["human_weight"]) if event and event["human_weight"] is not None else 0.80
        w_ai = float(event["ai_weight"]) if event and event["ai_weight"] is not None else 0.20
        ai_enabled = bool(event["ai_judging_enabled"]) if event and event["ai_judging_enabled"] is not None else True

        # Normalize weights to sum to 1.0
        sum_w = w_human + w_ai
        if sum_w > 0:
            norm_w_human = w_human / sum_w
            norm_w_ai = w_ai / sum_w
        else:
            norm_w_human, norm_w_ai = 1.0, 0.0

        # Fetch criteria and weights
        criteria_rows = conn.execute(
            "SELECT key, weight, max_score FROM criteria WHERE event_id = ?",
            (event_id,)
        ).fetchall()

        # Fetch all human scores
        scores_rows = conn.execute("""
            SELECT s.id as score_id, s.judge_id, s.project_id, s.total_score, s.comment,
                   p.title as project_title, p.team_id, t.name as team_name,
                   p.track_id, trk.name as track_name, p.eligibility_status
            FROM scores s
            JOIN projects p ON s.project_id = p.id
            JOIN teams t ON p.team_id = t.id
            LEFT JOIN tracks trk ON p.track_id = trk.id
            WHERE p.event_id = ?
        """, (event_id,)).fetchall()

        # Fetch all AI evaluations
        ai_evals_rows = conn.execute("""
            SELECT project_id, overall_score, reasoning
            FROM ai_evaluations
        """).fetchall()
        ai_eval_map = {row["project_id"]: row for row in ai_evals_rows}

        # Fetch all projects
        all_projects = conn.execute("""
            SELECT p.id as project_id, p.title as project_title, p.team_id, t.name as team_name,
                   p.track_id, trk.name as track_name, p.eligibility_status, p.summary
            FROM projects p
            JOIN teams t ON p.team_id = t.id
            LEFT JOIN tracks trk ON p.track_id = trk.id
            WHERE p.event_id = ?
        """, (event_id,)).fetchall()

    # Calculate judge-level stats for Z-Score normalization
    judge_scores_map: Dict[str, List[float]] = {}
    all_scores_flat: List[float] = []

    for s in scores_rows:
        jid = s["judge_id"]
        val = float(s["total_score"])
        judge_scores_map.setdefault(jid, []).append(val)
        all_scores_flat.append(val)

    global_mean = sum(all_scores_flat) / len(all_scores_flat) if all_scores_flat else 3.0
    var_global = sum((x - global_mean) ** 2 for x in all_scores_flat) / len(all_scores_flat) if len(all_scores_flat) > 1 else 1.0
    global_std = math.sqrt(var_global) if var_global > 0.0001 else 1.0

    judge_stats: Dict[str, Tuple[float, float]] = {}
    for jid, s_list in judge_scores_map.items():
        j_mean = sum(s_list) / len(s_list)
        if len(s_list) > 1:
            j_var = sum((x - j_mean) ** 2 for x in s_list) / len(s_list)
            j_std = math.sqrt(j_var)
        else:
            j_std = 0.0
        judge_stats[jid] = (j_mean, j_std)

    # Accumulate by project
    project_evals: Dict[str, Dict[str, Any]] = {}
    for p in all_projects:
        project_evals[p["project_id"]] = {
            "project_id": p["project_id"],
            "project_title": p["project_title"],
            "team_name": p["team_name"],
            "track_name": p["track_name"] or "General",
            "eligibility_status": p["eligibility_status"],
            "raw_human_scores": [],
            "norm_human_scores": [],
            "human_comments": []
        }

    for s in scores_rows:
        pid = s["project_id"]
        jid = s["judge_id"]
        raw_val = float(s["total_score"])
        j_mean, j_std = judge_stats.get(jid, (global_mean, global_std))

        if j_std > 0.001 and len(judge_scores_map.get(jid, [])) >= 2:
            z_score = (raw_val - j_mean) / j_std
            norm_val = global_mean + (z_score * global_std)
        else:
            bias = j_mean - global_mean
            norm_val = raw_val - bias

        norm_val = max(0.0, min(5.0, norm_val))

        if pid in project_evals:
            project_evals[pid]["raw_human_scores"].append(raw_val)
            project_evals[pid]["norm_human_scores"].append(norm_val)
            if s["comment"]:
                project_evals[pid]["human_comments"].append(s["comment"])

    # Synthesize results
    results = []
    for pid, data in project_evals.items():
        raw_list = data["raw_human_scores"]
        norm_list = data["norm_human_scores"]
        n_reviews = len(raw_list)

        raw_human_avg = round(sum(raw_list) / n_reviews, 3) if n_reviews > 0 else 0.0
        norm_human_avg = round(sum(norm_list) / n_reviews, 3) if n_reviews > 0 else 0.0

        ai_record = ai_eval_map.get(pid)
        ai_score = round(float(ai_record["overall_score"]), 3) if ai_record else None

        # Blending formula
        if n_reviews > 0 and ai_score is not None and ai_enabled:
            final_score = round((norm_human_avg * norm_w_human) + (ai_score * norm_w_ai), 3)
            diff = round(ai_score - norm_human_avg, 2)
            divergent = abs(diff) >= 1.0
        elif n_reviews > 0:
            final_score = norm_human_avg
            diff = 0.0
            divergent = False
        elif ai_score is not None and ai_enabled:
            final_score = ai_score
            diff = 0.0
            divergent = False
        else:
            final_score = 0.0
            diff = 0.0
            divergent = False

        results.append({
            "project_id": pid,
            "project_title": data["project_title"],
            "team_name": data["team_name"],
            "track_name": data["track_name"],
            "raw_score": raw_human_avg,
            "normalized_score": norm_human_avg,
            "human_score": norm_human_avg,
            "ai_score": ai_score,
            "final_score": final_score,
            "score_diff": diff,
            "is_divergent": divergent,
            "review_count": n_reviews,
            "has_ai_eval": ai_score is not None,
            "eligibility_status": data["eligibility_status"],
            "weights": {
                "human": round(norm_w_human, 2),
                "ai": round(norm_w_ai, 2)
            }
        })

    # Sort descending by final_score, then normalized human score, then raw
    results.sort(key=lambda x: (x["final_score"], x["normalized_score"], x["raw_score"]), reverse=True)

    for rank, item in enumerate(results, 1):
        item["rank"] = rank

    return results

def get_judge_calibration_stats(event_id: str = "evt_01") -> List[Dict[str, Any]]:
    """Returns statistics on each judge (mean, std dev, reviews count, leniency rating)."""
    with get_db() as conn:
        scores = conn.execute("""
            SELECT s.judge_id, j.name as judge_name, s.total_score
            FROM scores s
            JOIN judges j ON s.judge_id = j.id
            JOIN projects p ON s.project_id = p.id
            WHERE p.event_id = ?
        """, (event_id,)).fetchall()

    if not scores:
        return []

    judge_map: Dict[str, Dict[str, Any]] = {}
    all_scores = []
    for row in scores:
        jid = row["judge_id"]
        val = float(row["total_score"])
        all_scores.append(val)
        if jid not in judge_map:
            judge_map[jid] = {"judge_id": jid, "judge_name": row["judge_name"], "scores": []}
        judge_map[jid]["scores"].append(val)

    overall_mean = sum(all_scores) / len(all_scores) if all_scores else 3.0

    stats = []
    for jid, d in judge_map.items():
        s_list = d["scores"]
        n = len(s_list)
        mean_score = sum(s_list) / n
        if n > 1:
            var = sum((x - mean_score) ** 2 for x in s_list) / n
            std_dev = math.sqrt(var)
        else:
            std_dev = 0.0

        diff = mean_score - overall_mean
        if diff > 0.4:
            bias = "Lenient"
        elif diff < -0.4:
            bias = "Strict"
        else:
            bias = "Calibrated"

        stats.append({
            "judge_id": jid,
            "judge_name": d["judge_name"],
            "review_count": n,
            "mean_score": round(mean_score, 2),
            "std_dev": round(std_dev, 2),
            "bias": bias
        })

    stats.sort(key=lambda x: x["mean_score"], reverse=True)
    return stats
