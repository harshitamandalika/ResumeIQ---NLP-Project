from app.services.alignment.sbert_similarity import run_alignment
from app.services.skill_analysis.skill_validator import run_skill_analysis
from app.services.content_quality.bullet_scorer import run_content_quality


def _normalize_bullet_score(bullet):
    bullet_text = bullet.get("bullet") or bullet.get("text") or ""
    suggested_rewrite = bullet.get("suggested_rewrite") or bullet.get("rewrite") or ""

    return {
        **bullet,
        "bullet": bullet_text,
        "text": bullet_text,
        "suggested_rewrite": suggested_rewrite,
        "rewrite": suggested_rewrite,
    }


def _prepare_content_quality_for_frontend(content):
    normalized_scores = []
    rewrite_candidates = []

    for bullet in content.get("bullet_scores", []):
        normalized = _normalize_bullet_score(bullet)
        normalized_scores.append(normalized)

        if normalized["suggested_rewrite"] or normalized.get("needs_user_metric") or normalized.get("metric_prompt"):
            rewrite_candidates.append(normalized)

    return {
        **content,
        "bullet_scores": normalized_scores,
        "rewrite_candidates": rewrite_candidates,
    }


def run_full_pipeline(parsed_resume, jd_text):
    alignment = run_alignment(parsed_resume["raw_text"], jd_text)
    skills = run_skill_analysis(parsed_resume["sections"], jd_text)
    content = _prepare_content_quality_for_frontend(
        run_content_quality(parsed_resume["sections"]["experience"])
    )

    ats_score = compute_ats_score(alignment, skills, content)

    return {
        "ats_score": ats_score,
        "alignment": alignment,
        "skills": skills,
        "content_quality": content
    }


def compute_ats_score(alignment, skills, content):
    alignment_score = _compute_alignment_score(alignment)
    skill_score = _compute_skill_score(skills)
    content_score = _compute_content_score(content)

    final_score = (
        0.40 * alignment_score +
        0.35 * skill_score +
        0.25 * content_score
    )

    return round(final_score)


def _compute_alignment_score(alignment):
    """
    Combines:
    - semantic similarity score
    - keyword coverage score
    """
    similarity_score = alignment.get("similarity_score", 0.0)
    matched_keywords = alignment.get("matched_keywords", [])
    missing_keywords = alignment.get("missing_keywords", [])

    total_keywords = len(matched_keywords) + len(missing_keywords)

    if total_keywords == 0:
        keyword_coverage = 0.0
    else:
        keyword_coverage = len(matched_keywords) / total_keywords

    similarity_component = similarity_score * 100
    keyword_component = keyword_coverage * 100

    # Slightly favor semantic similarity, but still reward keyword coverage
    combined = 0.6 * similarity_component + 0.4 * keyword_component
    return combined


def _compute_skill_score(skills):
    """
    Percentage of extracted JD skills that were validated by resume evidence.
    """
    validated_skills = skills.get("validated_skills", [])
    missing_skills = skills.get("missing_skills", [])

    total_skills = len(validated_skills) + len(missing_skills)

    if total_skills == 0:
        return 0.0

    return (len(validated_skills) / total_skills) * 100


def _compute_content_score(content):
    """
    Average bullet quality score.
    """
    bullet_scores = content.get("bullet_scores", [])

    if not bullet_scores:
        return 0.0

    scores = [bullet.get("score", 0) for bullet in bullet_scores]
    return sum(scores) / len(scores)