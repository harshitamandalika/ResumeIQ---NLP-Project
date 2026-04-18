import unittest

from app.services.aggregator.combine_results import (
    _prepare_content_quality_for_frontend,
    compute_ats_score,
)


class AggregatorTests(unittest.TestCase):
    def test_compute_ats_score(self):
        alignment = {
            "similarity_score": 0.82,
            "matched_keywords": ["python", "fastapi", "nlp"],
            "missing_keywords": ["docker"],
        }
        skills = {
            "validated_skills": [
                {"skill": "python"},
                {"skill": "fastapi"},
                {"skill": "nlp"},
            ],
            "missing_skills": ["docker"],
        }
        content = {
            "bullet_scores": [
                {"score": 75},
                {"score": 75},
                {"score": 20},
                {"score": 95},
            ]
        }

        self.assertEqual(compute_ats_score(alignment, skills, content), 74)

    def test_prepares_rewrite_candidates_for_frontend(self):
        content = {
            "bullet_scores": [
                {
                    "text": "Built REST APIs using FastAPI.",
                    "score": 80,
                    "issues": [],
                    "rewrite": None,
                    "needs_user_metric": False,
                    "metric_prompt": "",
                },
                {
                    "text": "Worked on frontend development.",
                    "score": 35,
                    "issues": ["weak_action_verb", "missing_metric"],
                    "rewrite": "Developed frontend features for the user dashboard.",
                    "needs_user_metric": True,
                    "metric_prompt": "Consider adding feature adoption or page load improvements.",
                },
            ]
        }

        prepared = _prepare_content_quality_for_frontend(content)

        self.assertEqual(prepared["bullet_scores"][0]["bullet"], "Built REST APIs using FastAPI.")
        self.assertEqual(prepared["bullet_scores"][1]["suggested_rewrite"], "Developed frontend features for the user dashboard.")
        self.assertEqual(len(prepared["rewrite_candidates"]), 1)
        self.assertEqual(
            prepared["rewrite_candidates"][0]["bullet"],
            "Worked on frontend development.",
        )


if __name__ == "__main__":
    unittest.main()