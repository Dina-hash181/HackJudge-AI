import json
import os
import logging
from datetime import datetime, timezone
from src.config import (
    FIXTURES_PATH,
    SESSION_ORGANIZER,
    SESSION_JUDGE_A,
    SESSION_JUDGE_B,
    SESSION_PARTICIPANT
)
from src.database import get_db, init_db
from src.auth import hash_password

logger = logging.getLogger("dogfood.seed")

def seed_database(force: bool = False):
    init_db()
    with get_db() as conn:
        existing_event = conn.execute("SELECT id FROM events LIMIT 1").fetchone()
        if existing_event and not force:
            logger.info("Database already seeded. Skipping initial seeding.")
            return

        logger.info("Seeding database with fixtures and dogfood spec credentials...")

        # Load fixtures.json
        fixtures_data = None
        if os.path.exists(FIXTURES_PATH):
            with open(FIXTURES_PATH, "r", encoding="utf-8") as f:
                fixtures_data = json.load(f)

        now_iso = datetime.now(timezone.utc).isoformat()

        # 1. Event
        event_info = (fixtures_data or {}).get("event", {})
        event_id = event_info.get("id", "evt_01")
        event_name = event_info.get("name", "Sample Hack 2026")
        submissions_close = event_info.get("submissions_close", "2026-03-01T18:00:00Z")

        conn.execute("""
            INSERT OR REPLACE INTO events (id, name, description, submissions_close, is_archived, results_published, created_at)
            VALUES (?, ?, ?, ?, 0, 1, ?)
        """, (
            event_id,
            event_name,
            "The premier autonomous hackathon platform that judges you. Complete lifecycle management with normalized evaluation.",
            submissions_close,
            now_iso
        ))

        # 2. Criteria
        default_criteria = [
            ("functionality", "Technical Implementation & Functionality", 1.0, 5.0, "How complete, stable, and functionally sound is the codebase and architecture?"),
            ("innovation", "Innovation & Problem Originality", 1.0, 5.0, "Is the approach novel, creative, and distinct from cookie-cutter templates?"),
            ("quality", "Design Quality & Usability", 1.0, 5.0, "User experience, clear workflows, error resilience, and visual craftsmanship.")
        ]
        for c_key, c_name, c_weight, c_max, c_desc in default_criteria:
            conn.execute("""
                INSERT OR REPLACE INTO criteria (id, event_id, key, name, weight, max_score, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (f"crit_{c_key}", event_id, c_key, c_name, c_weight, c_max, c_desc))

        # 3. Tracks
        tracks_list = (fixtures_data or {}).get("tracks", [])
        for trk in tracks_list:
            conn.execute("""
                INSERT OR REPLACE INTO tracks (id, event_id, name, description)
                VALUES (?, ?, ?, ?)
            """, (
                trk["id"],
                event_id,
                trk["name"],
                f"Projects tackling core challenges in {trk['name'].lower()}."
            ))

        # 4. Standard User Accounts (Matching .dogfood.toml)
        # - Organizer / Admin
        admin_id = "usr_organizer"
        conn.execute("""
            INSERT OR REPLACE INTO users (id, username, email, password_hash, full_name, role, created_at)
            VALUES (?, ?, ?, ?, ?, 'organizer', ?)
        """, (admin_id, "organizer", "organizer@dogfoodhack.com", hash_password("adminpassword"), "Hackathon Organizer", now_iso))
        conn.execute("INSERT OR REPLACE INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)",
                     (SESSION_ORGANIZER, admin_id, now_iso))

        # - Judge A (Tomas Varga, jdg_01)
        judge_a_id = "usr_judge_a"
        conn.execute("""
            INSERT OR REPLACE INTO users (id, username, email, password_hash, full_name, role, created_at)
            VALUES (?, ?, ?, ?, ?, 'judge', ?)
        """, (judge_a_id, "judge_a", "tomas.varga@example.org", hash_password("judgepassword"), "Tomas Varga (Judge A)", now_iso))
        conn.execute("INSERT OR REPLACE INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)",
                     (SESSION_JUDGE_A, judge_a_id, now_iso))

        # - Judge B (Wei Lindqvist, jdg_02)
        judge_b_id = "usr_judge_b"
        conn.execute("""
            INSERT OR REPLACE INTO users (id, username, email, password_hash, full_name, role, created_at)
            VALUES (?, ?, ?, ?, ?, 'judge', ?)
        """, (judge_b_id, "judge_b", "wei.lindqvist@example.org", hash_password("judgepassword"), "Wei Lindqvist (Judge B)", now_iso))
        conn.execute("INSERT OR REPLACE INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)",
                     (SESSION_JUDGE_B, judge_b_id, now_iso))

        # - Participant (Ada Okonkwo, tm_01 Nightshift)
        part_id = "usr_participant"
        conn.execute("""
            INSERT OR REPLACE INTO users (id, username, email, password_hash, full_name, role, created_at)
            VALUES (?, ?, ?, ?, ?, 'participant', ?)
        """, (part_id, "participant", "ada@example.org", hash_password("participantpassword"), "Ada Okonkwo (Participant)", now_iso))
        conn.execute("INSERT OR REPLACE INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)",
                     (SESSION_PARTICIPANT, part_id, now_iso))

        # 5. Seed Judges from fixtures
        judges_list = (fixtures_data or {}).get("judges", [])
        for j in judges_list:
            jid = j["id"]
            j_name = j["name"]
            j_email = j["email"]
            j_tracks = json.dumps(j.get("tracks", []))

            # Link judge_a and judge_b to their users
            user_link = judge_a_id if jid == "jdg_01" else (judge_b_id if jid == "jdg_02" else None)

            # Create a user record for other judges if not exists
            if not user_link:
                uid = f"usr_{jid}"
                uname = j_email.split("@")[0].replace(".", "_")
                conn.execute("""
                    INSERT OR REPLACE INTO users (id, username, email, password_hash, full_name, role, created_at)
                    VALUES (?, ?, ?, ?, ?, 'judge', ?)
                """, (uid, uname, j_email, hash_password("judgepassword"), j_name, now_iso))
                user_link = uid

            conn.execute("""
                INSERT OR REPLACE INTO judges (id, user_id, name, email, tracks_json)
                VALUES (?, ?, ?, ?, ?)
            """, (jid, user_link, j_name, j_email, j_tracks))

        # 6. Seed Teams and Members from fixtures
        teams_list = (fixtures_data or {}).get("teams", [])
        for tm in teams_list:
            tmid = tm["id"]
            tm_name = tm["name"]
            invite_code = f"INV-{tmid.upper()}-{tm_name[:3].upper()}"

            conn.execute("""
                INSERT OR REPLACE INTO teams (id, event_id, name, invite_code, leader_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (tmid, event_id, tm_name, invite_code, part_id if tmid == "tm_01" else None, now_iso))

            for mem_email in tm.get("members", []):
                mem_id = f"mem_{tmid}_{mem_email.split('@')[0]}"
                u_link = part_id if mem_email == "ada@example.org" else None
                conn.execute("""
                    INSERT OR REPLACE INTO team_members (id, team_id, user_id, email, name, role, joined_at)
                    VALUES (?, ?, ?, ?, ?, 'member', ?)
                """, (mem_id, tmid, u_link, mem_email, mem_email.split("@")[0].title(), now_iso))

        # 7. Seed Projects from fixtures
        projects_list = (fixtures_data or {}).get("projects", [])
        for prj in projects_list:
            pid = prj["id"]
            team_id = prj.get("team")
            track_id = prj.get("track")
            title = prj.get("title", f"Project {pid}")
            summary = prj.get("summary", "A hackathon project.")
            repo_url = prj.get("repo_url", "https://github.com/example/repo")
            submitted_at = prj.get("submitted_at", now_iso)
            
            # Enrich with realistic details for rich gallery viewing and AI analysis
            problem_statement = f"Addressing high-latency synchronization and complex state validation in modern distributed setups for {title}."
            solution_description = (
                f"{summary} This project features an end-to-end self-contained architecture with reactive client state, "
                f"automated health heuristics, and complete local persistence without any hosted external reliance."
            )
            features = "Reactive Client State, Local Offline Storage, Real-time Sync Engine, Role-Based Access Control, Automated Health Heuristics"
            technologies = "Python, FastAPI, SQLite, WebSockets, Vanilla JS, TailwindCSS"
            demo_url = f"https://demo.dogfoodhack.com/p/{pid}"
            video_url = f"https://videos.dogfoodhack.com/v/{pid}.mp4"

            conn.execute("""
                INSERT OR REPLACE INTO projects (
                    id, event_id, team_id, track_id, title, summary,
                    problem_statement, solution_description, description, features, technologies, repo_url,
                    demo_url, video_url, submitted_at, eligibility_status, eligibility_notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'approved', 'Verified and meets all submission constraints.')
            """, (
                pid, event_id, team_id, track_id, title, summary,
                problem_statement, solution_description, solution_description, features, technologies, repo_url,
                demo_url, video_url, submitted_at
            ))

        # 8. Seed Scores and Criterion Scores from fixtures
        scores_list = (fixtures_data or {}).get("scores", [])
        for idx, s in enumerate(scores_list):
            jid = s.get("judge")
            pid = s.get("project")
            criteria_dict = s.get("criteria", {})
            comment = s.get("comment", "")
            
            # Calculate total score from criteria
            if criteria_dict:
                tot = sum(float(v) for v in criteria_dict.values()) / len(criteria_dict)
            else:
                tot = 3.0

            score_id = f"sc_{jid}_{pid}"
            conn.execute("""
                INSERT OR REPLACE INTO scores (id, judge_id, project_id, total_score, comment, submitted_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (score_id, jid, pid, round(tot, 2), comment, now_iso, now_iso))

            # Assignments
            conn.execute("""
                INSERT OR REPLACE INTO judge_assignments (id, judge_id, project_id, assigned_at)
                VALUES (?, ?, ?, ?)
            """, (f"asgn_{jid}_{pid}", jid, pid, now_iso))

            for crit_key, crit_val in criteria_dict.items():
                cs_id = f"cs_{score_id}_{crit_key}"
                conn.execute("""
                    INSERT OR REPLACE INTO criterion_scores (id, score_id, criterion_key, score)
                    VALUES (?, ?, ?, ?)
                """, (cs_id, score_id, crit_key, float(crit_val)))

        # 9. Seed Initial Certificates
        sample_certs = [
            ("CERT-DF-2026-WIN-01", "Nightshift (Ada Okonkwo)", "winner", event_name, "1st Place Grand Champion", "Glass Signal"),
            ("CERT-DF-2026-WIN-02", "Deep Compass Team", "winner", event_name, "Best Judging Engine Award", "Deep Compass"),
            ("CERT-DF-2026-JDG-01", "Tomas Varga", "judge", event_name, "Distinguished Technical Judge", None),
            ("CERT-DF-2026-JDG-02", "Wei Lindqvist", "judge", event_name, "Distinguished Technical Judge", None),
            ("CERT-DF-2026-PRT-01", "Ada Okonkwo", "participant", event_name, "Hackathon Finalist", "Glass Signal"),
        ]
        for c_code, r_name, c_type, ev_name, aw_title, prj_title in sample_certs:
            conn.execute("""
                INSERT OR REPLACE INTO certificates (id, cert_code, recipient_name, type, event_name, award_title, project_title, issued_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (f"cert_{c_code}", c_code, r_name, c_type, ev_name, aw_title, prj_title, now_iso))

        # 10. Audit log for seeding
        conn.execute("""
            INSERT OR REPLACE INTO audit_logs (id, user_id, action, entity_type, entity_id, details, created_at)
            VALUES (?, ?, 'SEED_INITIALIZATION', 'SYSTEM', ?, ?, ?)
        """, (
            "audit_init_01",
            admin_id,
            event_id,
            f"Seeded event with {len(projects_list)} projects, {len(judges_list)} judges, and {len(scores_list)} scores.",
            now_iso
        ))

    # 11. Run Batch AI Evaluations for all seeded projects
    try:
        from src.ai_judging import batch_evaluate_all_projects
        ai_count = batch_evaluate_all_projects(event_id)
        logger.info(f"Generated AI evaluations for {ai_count} projects.")
    except Exception as e:
        logger.warning(f"Could not batch evaluate AI projects during seed: {e}")

    print("\n========================================================")
    print("DOGFOOD 2026 PORTAL SEEDED SUCCESSFULLY!")
    print("AUTH CREDENTIALS & SESSIONS:")
    print(f"  Organizer:    Cookie: session={SESSION_ORGANIZER}")
    print(f"  Judge A:      Cookie: session={SESSION_JUDGE_A}")
    print(f"  Judge B:      Cookie: session={SESSION_JUDGE_B}")
    print(f"  Participant:  Cookie: session={SESSION_PARTICIPANT}")
    print("========================================================\n")
