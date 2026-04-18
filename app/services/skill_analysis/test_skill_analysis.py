import unittest

from app.services.skill_analysis import skill_validator as skill_validator_module


class SkillAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.original_extract_keywords = skill_validator_module.extract_keywords
        self.original_filter_keywords = skill_validator_module.filter_keywords
        self.original_extract_skills_from_jd = skill_validator_module.extract_skills_from_jd
        self.original_semantic_match_score = skill_validator_module._semantic_match_score

    def tearDown(self):
        skill_validator_module.extract_keywords = self.original_extract_keywords
        skill_validator_module.filter_keywords = self.original_filter_keywords
        skill_validator_module.extract_skills_from_jd = self.original_extract_skills_from_jd
        skill_validator_module._semantic_match_score = self.original_semantic_match_score

    def test_requires_experience_evidence_for_validation(self):
        skill_validator_module.extract_keywords = lambda _: ["Python", "Docker"]
        skill_validator_module.filter_keywords = lambda keywords: keywords
        skill_validator_module.extract_skills_from_jd = lambda _: []
        skill_validator_module._semantic_match_score = lambda skill, text: 0.0

        sections = {
            "skills": ["Python", "Docker"],
            "experience": [
                "Built REST APIs using Python for an NLP application.",
            ],
        }

        result = skill_validator_module.run_skill_analysis(sections, "mock jd")

        self.assertEqual([skill["skill"] for skill in result["validated_skills"]], ["python"])
        self.assertEqual(result["missing_skills"], ["docker"])
        self.assertEqual(result["validated_skills"][0]["source"], ["experience"])
        self.assertEqual(
            result["validated_skills"][0]["evidence"],
            "Built REST APIs using Python for an NLP application.",
        )


if __name__ == "__main__":
    unittest.main()