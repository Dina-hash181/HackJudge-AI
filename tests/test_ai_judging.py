import unittest
import json
from src.database import get_db
from src.seed_data import seed_database
from src.ai_judging import ai_engine, evaluate_project_with_ai, get_ai_evaluation_for_project
from src.scoring import calculate_project_scores

class TestAIJudgingSystem(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        seed_database(force=True)

    def test_ai_engine_analysis_structure(self):
        sample_project = {
            "title": "Quantum Relay",
            "summary": "Decentralized consensus relay protocol with autonomous verification.",
            "problem_statement": "High-latency consensus fails under unpredictable packet drop in IoT clusters.",
            "solution_description": "A novel consensus protocol using threshold cryptography and reactive state machines.",
            "features": "Threshold cryptography, Local verification, Zero external cloud dependencies",
            "technologies": "Rust, Python, WebAssembly, SQLite",
            "repo_url": "https://github.com/example/quantum-relay",
            "demo_url": "https://demo.example.com",
            "video_url": "https://youtube.com/watch?v=sample"
        }
        res = ai_engine.analyze_submission(sample_project)

        self.assertIn("overall_score", res)
        self.assertGreaterEqual(res["overall_score"], 1.0)
        self.assertLessEqual(res["overall_score"], 5.0)

        # Check all 5 required criteria
        for crit in ["technical_implementation", "innovation", "problem_relevance", "impact", "usability"]:
            self.assertIn(crit, res["criteria"])
            c_data = res["criteria"][crit]
            self.assertIn("score", c_data)
            self.assertIn("weight", c_data)
            self.assertIn("reasoning", c_data)

        # Check required analytical categories
        self.assertGreater(len(res["strengths"]), 0)
        self.assertGreater(len(res["improvements"]), 0)
        self.assertGreater(len(res["concerns"]), 0)
        self.assertGreater(len(res["missing_info"]), 0)

    def test_evaluate_and_store_project(self):
        eval_result = evaluate_project_with_ai("prj_01")
        self.assertIsNotNone(eval_result)
        self.assertEqual(eval_result["project_id"], "prj_01")
        self.assertIn("overall_score", eval_result)
        self.assertEqual(len(eval_result["criteria"]), 5)

        # Verify DB persistence
        with get_db() as conn:
            stored = conn.execute("SELECT * FROM ai_evaluations WHERE project_id = 'prj_01'").fetchone()
            self.assertIsNotNone(stored)
            self.assertEqual(stored["project_id"], "prj_01")

            crit_count = conn.execute(
                "SELECT COUNT(*) as c FROM ai_criterion_scores WHERE ai_eval_id = ?",
                (stored["id"],)
            ).fetchone()["c"]
            self.assertEqual(crit_count, 5)

    def test_final_scoring_formula_with_ai(self):
        results = calculate_project_scores("evt_01")
        self.assertGreater(len(results), 0)

        first = results[0]
        self.assertIn("human_score", first)
        self.assertIn("ai_score", first)
        self.assertIn("final_score", first)
        self.assertIn("score_diff", first)
        self.assertIn("is_divergent", first)

        # Verify weights apply correctly
        if first["human_score"] and first["ai_score"]:
            w_h = first["weights"]["human"]
            w_ai = first["weights"]["ai"]
            expected = round((first["human_score"] * w_h) + (first["ai_score"] * w_ai), 3)
            self.assertAlmostEqual(first["final_score"], expected, places=2)

    def test_score_difference_calculation(self):
        results = calculate_project_scores("evt_01")
        for r in results:
            if r["ai_score"] is not None and r["human_score"] is not None and r["human_score"] > 0:
                self.assertAlmostEqual(r["score_diff"], round(r["ai_score"] - r["human_score"], 2), places=2)
                if abs(r["score_diff"]) >= 1.0:
                    self.assertTrue(r["is_divergent"])

if __name__ == "__main__":
    unittest.main()
