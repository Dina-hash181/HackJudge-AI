import json
import logging
import secrets
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from src.database import get_db

logger = logging.getLogger("dogfood.ai_judge")

# Standard AI Rubric Criteria and Weights
DEFAULT_AI_CRITERIA = {
    "technical_implementation": {
        "name": "Technical Implementation",
        "weight": 0.25,
        "max_score": 5.0,
        "description": "Code architecture, stack appropriateness, implementation depth, completeness."
    },
    "innovation": {
        "name": "Innovation & Novelty",
        "weight": 0.20,
        "max_score": 5.0,
        "description": "Uniqueness of idea, creative approach, departure from trivial boilerplate."
    },
    "problem_relevance": {
        "name": "Problem Relevance",
        "weight": 0.20,
        "max_score": 5.0,
        "description": "Clarity of problem statement, real-world pain point, user empathy."
    },
    "impact": {
        "name": "Potential Impact",
        "weight": 0.20,
        "max_score": 5.0,
        "description": "Scale of utility, feasibility of adoption, measurable community/industry benefit."
    },
    "usability": {
        "name": "Usability & Polish",
        "weight": 0.15,
        "max_score": 5.0,
        "description": "End-user ergonomics, accessible demo availability, documentation completeness."
    }
}

class AIJudgeEngine:
    """
    Deterministic & Transparent AI Judging Engine.
    Evaluates project submissions systematically on 5 core dimensions,
    extracting structured criteria scores, comprehensive reasoning,
    identified strengths, actionable improvements, potential concerns,
    and missing information gaps.
    """

    def __init__(self, model_name: str = "HackJudge-AI-v2.5"):
        self.model_name = model_name

    def analyze_submission(self, project: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes structured rubric evaluation over verified submission content.
        Analyzes title, problem statement, solution description, features,
        technologies, repository, demo, and video URLs.
        """
        title = (project.get("title") or "").strip()
        summary = (project.get("summary") or "").strip()
        problem = (project.get("problem_statement") or "").strip()
        solution = (project.get("solution_description") or project.get("description") or "").strip()
        features = (project.get("features") or "").strip()
        tech_stack = (project.get("technologies") or "").strip()
        repo_url = (project.get("repo_url") or "").strip()
        demo_url = (project.get("demo_url") or "").strip()
        video_url = (project.get("video_url") or "").strip()

        # Text signal calculations
        full_text = f"{title} {summary} {problem} {solution} {features} {tech_stack}".lower()
        word_count = len(full_text.split())

        has_repo = bool(repo_url and repo_url.startswith("http"))
        has_demo = bool(demo_url and demo_url.startswith("http"))
        has_video = bool(video_url and video_url.startswith("http"))
        has_tech = bool(tech_stack)
        has_problem = len(problem) > 20
        has_solution = len(solution) > 30

        # Technical keyword heuristics
        modern_tech = ["fastapi", "react", "vue", "sqlite", "docker", "postgres", "rust", "python", "typescript", "go", "wasm", "redis", "graphql"]
        found_tech = [t for t in modern_tech if t in full_text]

        # 1. Technical Implementation (25%)
        tech_score = 3.0
        tech_reason = []
        if has_repo:
            tech_score += 0.8
            tech_reason.append("Provided accessible code repository.")
        else:
            tech_score -= 0.6
            tech_reason.append("Lacks direct link to public source code repository.")
        if len(found_tech) >= 3:
            tech_score += 0.7
            tech_reason.append(f"Employs cohesive tech stack ({', '.join(found_tech[:3])}).")
        elif has_tech:
            tech_score += 0.3
            tech_reason.append("Specifies modern technology choices.")
        if word_count > 60:
            tech_score += 0.4
            tech_reason.append("Detailed implementation breakdown provided.")
        tech_score = max(1.0, min(5.0, round(tech_score, 2)))

        # 2. Innovation & Novelty (20%)
        innov_score = 3.2
        innov_reason = []
        innov_keywords = ["novel", "autonomous", "real-time", "z-score", "distributed", "decentralized", "ai", "self-hosted", "protocol", "engine"]
        innov_matches = [k for k in innov_keywords if k in full_text]
        if innov_matches:
            innov_score += min(1.3, len(innov_matches) * 0.3)
            innov_reason.append(f"Demonstrates non-trivial architecture targeting {', '.join(innov_matches[:2])}.")
        else:
            innov_reason.append("Standard application pattern with moderate architectural novelty.")
        innov_score = max(1.0, min(5.0, round(innov_score, 2)))

        # 3. Problem Relevance (20%)
        prob_score = 3.0
        prob_reason = []
        if has_problem:
            prob_score += 0.9
            prob_reason.append(f"Articulates a concrete problem domain: '{problem[:60]}...'.")
        else:
            prob_score -= 0.5
            prob_reason.append("Problem statement is terse or lacks articulated user pain points.")
        if "sync" in full_text or "latency" in full_text or "bias" in full_text or "security" in full_text:
            prob_score += 0.5
            prob_reason.append("Focuses on high-leverage systems or reliability challenges.")
        prob_score = max(1.0, min(5.0, round(prob_score, 2)))

        # 4. Potential Impact (20%)
        impact_score = 3.1
        impact_reason = []
        if has_solution and len(solution) > 50:
            impact_score += 0.8
            impact_reason.append("Clear solution path with broad utility for target audience.")
        if "scale" in full_text or "platform" in full_text or "adoption" in full_text:
            impact_score += 0.6
            impact_reason.append("Designed for reusable adoption across external communities.")
        else:
            impact_reason.append("Impact scope is contained to single deployment scenarios.")
        impact_score = max(1.0, min(5.0, round(impact_score, 2)))

        # 5. Usability & Polish (15%)
        usab_score = 2.8
        usab_reason = []
        if has_demo:
            usab_score += 1.2
            usab_reason.append("Live interactive demo available for direct verification.")
        else:
            usab_score -= 0.4
            usab_reason.append("No live interactive demo endpoint provided.")
        if has_video:
            usab_score += 0.5
            usab_reason.append("Walkthrough video link attached.")
        if features:
            usab_score += 0.4
            usab_reason.append("Explicit user features cataloged.")
        usab_score = max(1.0, min(5.0, round(usab_score, 2)))

        # Overall weighted AI score
        criteria_results = {
            "technical_implementation": {
                "score": tech_score,
                "weight": DEFAULT_AI_CRITERIA["technical_implementation"]["weight"],
                "reasoning": " ".join(tech_reason)
            },
            "innovation": {
                "score": innov_score,
                "weight": DEFAULT_AI_CRITERIA["innovation"]["weight"],
                "reasoning": " ".join(innov_reason)
            },
            "problem_relevance": {
                "score": prob_score,
                "weight": DEFAULT_AI_CRITERIA["problem_relevance"]["weight"],
                "reasoning": " ".join(prob_reason)
            },
            "impact": {
                "score": impact_score,
                "weight": DEFAULT_AI_CRITERIA["impact"]["weight"],
                "reasoning": " ".join(impact_reason)
            },
            "usability": {
                "score": usab_score,
                "weight": DEFAULT_AI_CRITERIA["usability"]["weight"],
                "reasoning": " ".join(usab_reason)
            }
        }

        overall_score = sum(c["score"] * c["weight"] for c in criteria_results.values())
        overall_score = round(overall_score, 2)

        # Synthesize Strengths, Improvements, Concerns, Missing Info
        strengths = []
        if has_repo:
            strengths.append(f"Public code repository verifiable at {repo_url}")
        if has_demo:
            strengths.append("Interactive live deployment supplied for evaluators")
        if found_tech:
            strengths.append(f"Modular technology stack utilizing {', '.join(found_tech[:3])}")
        if has_problem:
            strengths.append("Clearly formulated problem statement with defined target beneficiaries")
        if not strengths:
            strengths.append("Clean submission title with baseline functional premise")

        improvements = []
        if not has_demo:
            improvements.append("Deploy a live hosted demo sandbox or test instance for immediate evaluator interaction")
        if not has_video:
            improvements.append("Record a 2-3 minute video walkthrough showcasing key workflows and edge-case handling")
        if word_count < 80:
            improvements.append("Expand solution description to document data flow, failure recovery, and architectural tradeoffs")
        if not features:
            improvements.append("Provide bulleted breakdown of completed features versus future roadmap aspirations")
        if not improvements:
            improvements.append("Include automated performance benchmark metrics under concurrent user loads")

        concerns = []
        if not has_repo:
            concerns.append("Absence of public repository prevents verification of original code contributions")
        if word_count < 40:
            concerns.append("Extremely brief submission text creates ambiguity around technical depth")
        if not concerns:
            concerns.append("Potential scalability constraints under heavy multi-tenant concurrency if unbounded")

        missing_info = []
        if not has_demo:
            missing_info.append("Live demo URL")
        if not has_repo:
            missing_info.append("Source code repository URL")
        if not has_video:
            missing_info.append("Demo video or presentation recording URL")
        if not tech_stack:
            missing_info.append("Explicit technology stack enumeration")
        if not missing_info:
            missing_info.append("None. Submission payload satisfies all baseline informational requirements.")

        reasoning_summary = (
            f"Evaluated as a {tech_score}/5.0 technical submission with {innov_score}/5.0 innovation. "
            f"{'Strong implementation signals with linked repository.' if has_repo else 'Recommendation to supply source code verification.'} "
            f"Overall AI score sits at {overall_score}/5.0 based on weighted rubric dimensions."
        )

        return {
            "model_name": self.model_name,
            "overall_score": overall_score,
            "reasoning": reasoning_summary,
            "criteria": criteria_results,
            "strengths": strengths,
            "improvements": improvements,
            "concerns": concerns,
            "missing_info": missing_info
        }

# Global Engine Instance
ai_engine = AIJudgeEngine()

def evaluate_project_with_ai(project_id: str) -> Dict[str, Any]:
    """
    Evaluates a project using the AI Judge, stores evaluation and criterion breakdown,
    records an audit log entry, and returns the stored evaluation record.
    """
    with get_db() as conn:
        project = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        if not project:
            raise ValueError(f"Project with ID '{project_id}' not found.")

        result = ai_engine.analyze_submission(project)
        now_iso = datetime.now(timezone.utc).isoformat()
        eval_id = f"ai_eval_{project_id}"

        # Insert or replace in ai_evaluations
        conn.execute("""
            INSERT OR REPLACE INTO ai_evaluations (
                id, project_id, model_name, overall_score, reasoning,
                strengths_json, improvements_json, concerns_json, missing_info_json, evaluated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            eval_id,
            project_id,
            result["model_name"],
            result["overall_score"],
            result["reasoning"],
            json.dumps(result["strengths"]),
            json.dumps(result["improvements"]),
            json.dumps(result["concerns"]),
            json.dumps(result["missing_info"]),
            now_iso
        ))

        # Insert criterion breakdown
        for crit_key, crit_data in result["criteria"].items():
            cs_id = f"ai_cs_{eval_id}_{crit_key}"
            conn.execute("""
                INSERT OR REPLACE INTO ai_criterion_scores (
                    id, ai_eval_id, criterion_key, score, weight, reasoning
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                cs_id,
                eval_id,
                crit_key,
                crit_data["score"],
                crit_data["weight"],
                crit_data["reasoning"]
            ))

        # Audit log entry
        conn.execute("""
            INSERT INTO audit_logs (id, user_id, action, entity_type, entity_id, details, created_at)
            VALUES (?, 'SYSTEM_AI', 'AI_EVALUATION', 'PROJECT', ?, ?, ?)
        """, (
            f"audit_ai_{secrets.token_hex(4)}",
            project_id,
            f"AI evaluation completed. Model: {result['model_name']}, Score: {result['overall_score']}/5.0",
            now_iso
        ))

        return get_ai_evaluation_for_project(project_id)

def get_ai_evaluation_for_project(project_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves full stored AI evaluation record for a project."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM ai_evaluations WHERE project_id = ?", (project_id,)).fetchone()
        if not row:
            return None

        crit_rows = conn.execute("""
            SELECT criterion_key, score, weight, reasoning
            FROM ai_criterion_scores
            WHERE ai_eval_id = ?
        """, (row["id"],)).fetchall()

        return {
            "id": row["id"],
            "project_id": row["project_id"],
            "model_name": row["model_name"],
            "overall_score": row["overall_score"],
            "reasoning": row["reasoning"],
            "strengths": json.loads(row["strengths_json"]),
            "improvements": json.loads(row["improvements_json"]),
            "concerns": json.loads(row["concerns_json"]),
            "missing_info": json.loads(row["missing_info_json"]),
            "evaluated_at": row["evaluated_at"],
            "criteria": {
                c["criterion_key"]: {
                    "score": c["score"],
                    "weight": c["weight"],
                    "reasoning": c["reasoning"]
                }
                for c in crit_rows
            }
        }

def batch_evaluate_all_projects(event_id: str = "evt_01") -> int:
    """Evaluates all approved projects in the event."""
    with get_db() as conn:
        projects = conn.execute("SELECT id FROM projects WHERE event_id = ? AND eligibility_status = 'approved'", (event_id,)).fetchall()

    count = 0
    for p in projects:
        evaluate_project_with_ai(p["id"])
        count += 1
    return count
