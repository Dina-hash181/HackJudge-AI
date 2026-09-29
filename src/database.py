import sqlite3
import json
import logging
from contextlib import contextmanager
from typing import Generator
from src.config import DB_PATH

logger = logging.getLogger("dogfood.database")

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = dict_factory
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 30000;")
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'organizer', 'judge', 'participant')),
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at TEXT NOT NULL,
            expires_at TEXT
        );

        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            submissions_close TEXT NOT NULL,
            is_archived INTEGER DEFAULT 0,
            results_published INTEGER DEFAULT 0,
            human_weight REAL DEFAULT 0.80,
            ai_weight REAL DEFAULT 0.20,
            ai_judging_enabled INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS tracks (
            id TEXT PRIMARY KEY,
            event_id TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            description TEXT
        );

        CREATE TABLE IF NOT EXISTS judges (
            id TEXT PRIMARY KEY,
            user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            tracks_json TEXT DEFAULT '[]'
        );

        CREATE TABLE IF NOT EXISTS teams (
            id TEXT PRIMARY KEY,
            event_id TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            invite_code TEXT UNIQUE NOT NULL,
            leader_id TEXT REFERENCES users(id) ON DELETE SET NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS team_members (
            id TEXT PRIMARY KEY,
            team_id TEXT NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
            user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
            email TEXT NOT NULL,
            name TEXT,
            role TEXT DEFAULT 'member',
            joined_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            event_id TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
            team_id TEXT NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
            track_id TEXT REFERENCES tracks(id) ON DELETE SET NULL,
            title TEXT NOT NULL,
            summary TEXT,
            problem_statement TEXT,
            solution_description TEXT,
            features TEXT,
            technologies TEXT,
            repo_url TEXT,
            demo_url TEXT,
            video_url TEXT,
            submitted_at TEXT NOT NULL,
            eligibility_status TEXT DEFAULT 'approved',
            eligibility_notes TEXT
        );

        CREATE TABLE IF NOT EXISTS criteria (
            id TEXT PRIMARY KEY,
            event_id TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
            key TEXT NOT NULL,
            name TEXT NOT NULL,
            weight REAL DEFAULT 1.0,
            max_score REAL DEFAULT 5.0,
            description TEXT,
            UNIQUE(event_id, key)
        );

        CREATE TABLE IF NOT EXISTS judge_assignments (
            id TEXT PRIMARY KEY,
            judge_id TEXT NOT NULL REFERENCES judges(id) ON DELETE CASCADE,
            project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            assigned_at TEXT NOT NULL,
            UNIQUE(judge_id, project_id)
        );

        CREATE TABLE IF NOT EXISTS scores (
            id TEXT PRIMARY KEY,
            judge_id TEXT NOT NULL REFERENCES judges(id) ON DELETE CASCADE,
            project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            total_score REAL NOT NULL,
            comment TEXT,
            submitted_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(judge_id, project_id)
        );

        CREATE TABLE IF NOT EXISTS criterion_scores (
            id TEXT PRIMARY KEY,
            score_id TEXT NOT NULL REFERENCES scores(id) ON DELETE CASCADE,
            criterion_key TEXT NOT NULL,
            score REAL NOT NULL,
            UNIQUE(score_id, criterion_key)
        );

        -- AI JUDGING TABLES
        CREATE TABLE IF NOT EXISTS ai_evaluations (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            model_name TEXT NOT NULL,
            overall_score REAL NOT NULL,
            reasoning TEXT NOT NULL,
            strengths_json TEXT NOT NULL,
            improvements_json TEXT NOT NULL,
            concerns_json TEXT NOT NULL,
            missing_info_json TEXT NOT NULL,
            evaluated_at TEXT NOT NULL,
            UNIQUE(project_id)
        );

        CREATE TABLE IF NOT EXISTS ai_criterion_scores (
            id TEXT PRIMARY KEY,
            ai_eval_id TEXT NOT NULL REFERENCES ai_evaluations(id) ON DELETE CASCADE,
            criterion_key TEXT NOT NULL,
            score REAL NOT NULL,
            weight REAL NOT NULL,
            reasoning TEXT,
            UNIQUE(ai_eval_id, criterion_key)
        );

        CREATE TABLE IF NOT EXISTS audit_logs (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            action TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT,
            details TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS certificates (
            id TEXT PRIMARY KEY,
            cert_code TEXT UNIQUE NOT NULL,
            user_id TEXT,
            recipient_name TEXT NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('participant', 'judge', 'winner')),
            event_name TEXT NOT NULL,
            award_title TEXT,
            project_title TEXT,
            issued_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS public_votes (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            voter_identifier TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(project_id, voter_identifier)
        );

        CREATE TABLE IF NOT EXISTS comments (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            user_id TEXT,
            author_name TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_projects_event ON projects(event_id);
        CREATE INDEX IF NOT EXISTS idx_scores_project ON scores(project_id);
        CREATE INDEX IF NOT EXISTS idx_scores_judge ON scores(judge_id);
        CREATE INDEX IF NOT EXISTS idx_assignments_judge ON judge_assignments(judge_id);
        CREATE INDEX IF NOT EXISTS idx_ai_eval_project ON ai_evaluations(project_id);
        """)

        # Migration: ensure newly added columns exist in older tables if upgrading
        existing_cols_proj = [c["name"] for c in conn.execute("PRAGMA table_info(projects);").fetchall()]
        if "solution_description" not in existing_cols_proj:
            conn.execute("ALTER TABLE projects ADD COLUMN solution_description TEXT;")
        if "features" not in existing_cols_proj:
            conn.execute("ALTER TABLE projects ADD COLUMN features TEXT;")
        if "video_url" not in existing_cols_proj:
            conn.execute("ALTER TABLE projects ADD COLUMN video_url TEXT;")

        existing_cols_event = [c["name"] for c in conn.execute("PRAGMA table_info(events);").fetchall()]
        if "human_weight" not in existing_cols_event:
            conn.execute("ALTER TABLE events ADD COLUMN human_weight REAL DEFAULT 0.80;")
        if "ai_weight" not in existing_cols_event:
            conn.execute("ALTER TABLE events ADD COLUMN ai_weight REAL DEFAULT 0.20;")
        if "ai_judging_enabled" not in existing_cols_event:
            conn.execute("ALTER TABLE events ADD COLUMN ai_judging_enabled INTEGER DEFAULT 1;")

    logger.info("Database initialized successfully with AI judging tables.")
