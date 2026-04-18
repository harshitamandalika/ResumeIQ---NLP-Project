import unittest

from app.services.content_quality import bullet_scorer as bullet_scorer_module


class ContentQualityTests(unittest.TestCase):
    def setUp(self):
        self.original_gemini_enabled = bullet_scorer_module._GEMINI_ENABLED
        self.original_gemini_model = bullet_scorer_module._gemini_model
        bullet_scorer_module._GEMINI_ENABLED = False
        bullet_scorer_module._gemini_model = None

    def tearDown(self):
        bullet_scorer_module._GEMINI_ENABLED = self.original_gemini_enabled
        bullet_scorer_module._gemini_model = self.original_gemini_model

    def test_scores_only_real_bullets(self):
        experience = [
            "Austin, TX",
            "Software Engineer | ResumeIQ",
            "2023 - 2025",
            "• Built REST APIs using FastAPI for an NLP application.",
            "- Optimized inference latency by 35% using model pruning.",
        ]

        result = bullet_scorer_module.run_content_quality(experience)
        bullet_scores = result["bullet_scores"]

        self.assertEqual(len(bullet_scores), 2)
        self.assertEqual(
            [bullet["text"] for bullet in bullet_scores],
            [
                "Built REST APIs using FastAPI for an NLP application.",
                "Optimized inference latency by 35% using model pruning.",
            ],
        )

    def test_uses_metric_ready_rewrite_template_for_demo(self):
        experience = [
            "- Used FastAPI to serve model predictions and support downstream application integration.",
        ]

        result = bullet_scorer_module.run_content_quality(experience)
        bullet = result["bullet_scores"][0]

        self.assertEqual(bullet["text"], "Used FastAPI to serve model predictions and support downstream application integration.")
        self.assertEqual(bullet["rewrite"].startswith("Implemented FastAPI"), True)
        self.assertIn("[X% / Y ms]", bullet["rewrite"])
        self.assertIn("[N] downstream services or workflows", bullet["rewrite"])
        self.assertTrue(bullet["needs_user_metric"])
        self.assertTrue(bullet["metric_prompt"])


if __name__ == "__main__":
    unittest.main()