# skill validation

import re

from app.services.alignment.sbert_similarity import extract_skills_from_jd, normalize_keyword


def _build_skill_pattern(skill):
    return r"\b" + re.escape(skill).replace(r"\ ", r"\s+") + r"\b"


def _find_evidence(skill, resume_skills, experience_lines):
    pattern = _build_skill_pattern(skill)

    for listed_skill in resume_skills:
        normalized_skill = normalize_keyword(listed_skill)
        if re.search(pattern, normalized_skill):
            return "Listed in the skills section"

    for line in experience_lines:
        if re.search(pattern, line.lower()):
            return line

    return "Mentioned in the resume"


def run_skill_analysis(sections, jd_text):
    resume_skills = sections.get("skills", [])
    experience_lines = sections.get("experience", [])

    required_skills = [normalize_keyword(skill) for skill in extract_skills_from_jd(jd_text)]
    required_skills = sorted(set(required_skills))

    resume_text = "\n".join(resume_skills + experience_lines).lower()

    validated_skills = []
    missing_skills = []

    for skill in required_skills:
        pattern = _build_skill_pattern(skill)

        if re.search(pattern, resume_text):
            validated_skills.append(
                {
                    "skill": skill,
                    "evidence": _find_evidence(skill, resume_skills, experience_lines),
                }
            )
        else:
            missing_skills.append(skill)

    return {
        "validated_skills": validated_skills,
        "missing_skills": missing_skills,
    }