import os
import sys
from pathlib import Path

# Ensure root directory is in sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.main import app
from src.database import init_db
from src.seed_data import seed_database

# Ensure database is initialized on serverless cold start
try:
    init_db()
    seed_database(force=False)
except Exception as e:
    print(f"Serverless DB init note: {e}")
