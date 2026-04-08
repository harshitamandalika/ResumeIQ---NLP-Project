# final output + ATS score

from app.services.alignment.sbert_similarity import run_alignment
from app.services.skill_analysis.skill_validator import run_skill_analysis
from app.services.content_quality.bullet_scorer import run_content_quality

def run_full_pipeline(parsed_resume, jd_text):
    alignment = run_alignment(parsed_resume["raw_text"], jd_text)
    skills = run_skill_analysis(parsed_resume["sections"], jd_text)
    content = run_content_quality(parsed_resume["sections"]["experience"])

    ats_score = compute_ats_score(alignment, skills, content)

    return {
        "ats_score": ats_score,
        "alignment": alignment,
        "skills": skills,
        "content_quality": content
    }


def compute_ats_score(alignment, skills, content):
    similarity_score = alignment.get("similarity_score", 0.0) * 100

    matched_keywords = alignment.get("matched_keywords", [])
    missing_keywords = alignment.get("missing_keywords", [])
    keyword_total = len(matched_keywords) + len(missing_keywords)
    keyword_coverage = (len(matched_keywords) / keyword_total * 100) if keyword_total else 0

    validated_skills = skills.get("validated_skills", [])
    missing_skills = skills.get("missing_skills", [])
    skill_total = len(validated_skills) + len(missing_skills)
    skill_coverage = (len(validated_skills) / skill_total * 100) if skill_total else 0

    bullet_scores = content.get("bullet_scores", [])
    average_bullet_score = (
        sum(item.get("score", 0) for item in bullet_scores) / len(bullet_scores)
        if bullet_scores else 50
    )

    alignment_component = (0.65 * similarity_score) + (0.35 * keyword_coverage)
    final_score = (
        0.5 * alignment_component
        + 0.25 * skill_coverage
        + 0.25 * average_bullet_score
    )

    return round(max(0, min(final_score, 100)))

