import os
import shutil
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# On serverless (Vercel / AWS Lambda), the filesystem is read-only except /tmp
if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
    tmp_dir = Path(tempfile.gettempdir())
    tmp_db = tmp_dir / "dogfood.db"
    orig_db = BASE_DIR / "dogfood.db"
    if not tmp_db.exists() and orig_db.exists():
        try:
            shutil.copy2(orig_db, tmp_db)
        except Exception:
            pass
    DB_PATH = str(tmp_db)
else:
    DB_PATH = os.environ.get("DB_PATH", str(BASE_DIR / "dogfood.db"))

FIXTURES_PATH = os.environ.get("FIXTURES_PATH", str(BASE_DIR / "fixtures.json"))

PORT = int(os.environ.get("PORT", "8080"))
HOST = os.environ.get("HOST", "0.0.0.0")
SECRET_KEY = os.environ.get("SECRET_KEY", "dogfood-hackathon-2026-super-secret-key-391823")

# Dogfood Spec Fixed Sessions
SESSION_ORGANIZER = "org_7f2a"
SESSION_JUDGE_A = "jdg_a_91bc"
SESSION_JUDGE_B = "jdg_b_44de"
SESSION_PARTICIPANT = "prt_2e88"
