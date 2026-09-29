import unittest
import json
from src.database import get_db, init_db
from src.seed_data import seed_database
from src.scoring import calculate_project_scores, get_judge_calibration_stats
from src.auth import hash_password, verify_password

class TestDogfoodPlatform(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        seed_database(force=True)

    def test_database_seeded_counts(self):
        with get_db() as conn:
            projects = conn.execute("SELECT COUNT(*) as c FROM projects").fetchone()["c"]
            judges = conn.execute("SELECT COUNT(*) as c FROM judges").fetchone()["c"]
            scores = conn.execute("SELECT COUNT(*) as c FROM scores").fetchone()["c"]
            teams = conn.execute("SELECT COUNT(*) as c FROM teams").fetchone()["c"]

            self.assertGreaterEqual(projects, 40)
            self.assertGreaterEqual(judges, 30)
            self.assertGreaterEqual(scores, 100)
            self.assertGreaterEqual(teams, 40)

    def test_auth_hashing(self):
        raw = "mySuperSecurePass123!"
        hashed = hash_password(raw)
        self.assertTrue(verify_password(hashed, raw))
        self.assertFalse(verify_password(hashed, "wrongPassword"))

    def test_scoring_and_normalization(self):
        results = calculate_project_scores("evt_01")
        self.assertGreater(len(results), 0)
        top = results[0]
        self.assertEqual(top["rank"], 1)
        self.assertIn("project_id", top)
        self.assertIn("raw_score", top)
        self.assertIn("normalized_score", top)
        # Verify sorted
        for i in range(len(results) - 1):
            self.assertGreaterEqual(results[i]["normalized_score"], results[i+1]["normalized_score"])

    def test_calibration_stats(self):
        calib = get_judge_calibration_stats("evt_01")
        self.assertGreater(len(calib), 0)
        first_judge = calib[0]
        self.assertIn("judge_id", first_judge)
        self.assertIn("mean_score", first_judge)
        self.assertIn("std_dev", first_judge)
        self.assertIn(first_judge["bias"], ["Lenient", "Strict", "Calibrated"])

    def test_fixture_titles_present(self):
        with get_db() as conn:
            titles = [p["title"] for p in conn.execute("SELECT title FROM projects LIMIT 5").fetchall()]
            self.assertTrue(any(t in ["Glass Signal", "Small Meadow", "Deep Compass"] for t in titles))

if __name__ == "__main__":
    unittest.main()
