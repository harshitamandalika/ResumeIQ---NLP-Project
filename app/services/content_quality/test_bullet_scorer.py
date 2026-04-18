import unittest

from app.services.content_quality.bullet_scorer import run_content_quality


class ContentQualityTests(unittest.TestCase):
    def test_scores_only_real_bullets(self):
        experience = [
            "Austin, TX",
            "Software Engineer | ResumeIQ",
            "2023 - 2025",
            "• Built REST APIs using FastAPI for an NLP application.",
            "- Optimized inference latency by 35% using model pruning.",
        ]

        result = run_content_quality(experience)
        bullet_scores = result["bullet_scores"]

        self.assertEqual(len(bullet_scores), 2)
        self.assertEqual(
            [bullet["text"] for bullet in bullet_scores],
            [
                "Built REST APIs using FastAPI for an NLP application.",
                "Optimized inference latency by 35% using model pruning.",
            ],
        )


if __name__ == "__main__":
    unittest.main()