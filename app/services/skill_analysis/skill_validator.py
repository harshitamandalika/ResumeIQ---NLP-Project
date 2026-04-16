import re
from typing import Any, Dict, List, Set

from sklearn.metrics.pairwise import cosine_similarity

from app.services.alignment import sbert_similarity as alignment_module
from app.services.alignment.sbert_similarity import (
    extract_keywords,
    extract_skills_from_jd,
    filter_keywords,
    normalize_keyword,
    normalize_text,
)

SEMANTIC_MATCH_THRESHOLD = 0.38
MAX_EVIDENCE_PER_SKILL = 3

SKILL_ALIASES = {
    "nlp": ["natural language processing"],
    "llm": ["large language model", "large language models"],
    "api": ["apis", "rest api", "rest apis"],
    "transformers": ["transformer", "transformer based", "transformer-based"],
    "ci cd": ["ci/cd", "continuous integration", "continuous delivery"],
}

ALIASES_TO_CANONICAL = {}
for canonical, aliases in SKILL_ALIASES.items():
    ALIASES_TO_CANONICAL[canonical] = canonical
    for alias in aliases:
        ALIASES_TO_CANONICAL[alias] = canonical


def _dedupe_keep_order(items: List[str]) -> List[str]:
    seen = set()
    output = []

    for item in items:
        if item not in seen:
            seen.add(item)
            output.append(item)

    return output


def _normalize_for_matching(text: str) -> str:
    text = text.lower()
    text = text.replace("-", " ")
    text = text.replace("/", " ")
    text = re.sub(r"[^\w\s+.#]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return normalize_text(text)


def _canonicalize_skill(skill: str) -> str:
    skill = _normalize_for_matching(skill)
    skill = normalize_keyword(skill)
    return ALIASES_TO_CANONICAL.get(skill, skill)


def _generate_variants(skill: str) -> Set[str]:
    canonical = _canonicalize_skill(skill)
    variants = {canonical}

    if canonical.endswith("s") and len(canonical) > 4:
        variants.add(canonical[:-1])

    variants.add(canonical.replace(" ", "-"))
    variants.add(canonical.replace("-", " "))

    if canonical in SKILL_ALIASES:
        for alias in SKILL_ALIASES[canonical]:
            normalized_alias = _normalize_for_matching(alias)
            variants.add(normalized_alias)
            variants.add(normalized_alias.replace(" ", "-"))

    return {variant.strip() for variant in variants if variant.strip()}


def _extract_target_skills(jd_text: str) -> List[str]:
    keywords_keybert = filter_keywords(extract_keywords(jd_text))
    keywords_rule = extract_skills_from_jd(jd_text)
    combined = keywords_keybert + keywords_rule
    canonicalized = [_canonicalize_skill(skill) for skill in combined]
    return _dedupe_keep_order(canonicalized)


def _normalize_resume_skills(skills: List[str]) -> List[str]:
    normalized = []

    for skill in skills:
        canonical_skill = _canonicalize_skill(skill)
        if canonical_skill:
            normalized.append(canonical_skill)

    return _dedupe_keep_order(normalized)


def _contains_variant(text: str, skill: str) -> bool:
    normalized_text = _normalize_for_matching(text)

    for variant in _generate_variants(skill):
        pattern = r"\b" + re.escape(variant).replace(r"\ ", r"\s+") + r"\b"
        if re.search(pattern, normalized_text):
            return True

    return False


def _get_similarity_model():
    model_getter = getattr(alignment_module, "_get_models", None)
    if callable(model_getter):
        model, _ = model_getter()
        return model
    return getattr(alignment_module, "sbert_model", None)


def _semantic_match_score(skill: str, text: str) -> float:
    model = _get_similarity_model()
    if model is None:
        return 0.0

    embeddings = model.encode([skill, text])
    score = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
    return float(score)


def _find_skill_evidence(skill: str, experience_lines: List[str]) -> List[str]:
    exact_or_variant_matches = []
    semantic_matches = []

    for line in experience_lines:
        line = line.strip()
        if not line:
            continue

        if _contains_variant(line, skill):
            exact_or_variant_matches.append(line)
            continue

        score = _semantic_match_score(skill, line)
        if score >= SEMANTIC_MATCH_THRESHOLD:
            semantic_matches.append((score, line))

    semantic_matches.sort(key=lambda item: item[0], reverse=True)

    evidence = exact_or_variant_matches[:MAX_EVIDENCE_PER_SKILL]
    remaining = MAX_EVIDENCE_PER_SKILL - len(evidence)
    if remaining > 0:
        evidence.extend([line for _, line in semantic_matches[:remaining]])

    return _dedupe_keep_order(evidence)


def _summarize_evidence(found_in_skills_section: bool, evidence_lines: List[str]) -> str:
    if found_in_skills_section:
        return "Listed in the skills section"
    if evidence_lines:
        return evidence_lines[0]
    return "Mentioned in the resume"


def _extract_explicit_years(text: str) -> List[float]:
    matches = re.findall(r"(\d+(?:\.\d+)?)\+?\s+years?", text.lower())
    return [float(value) for value in matches]


def _extract_calendar_years(text: str) -> List[int]:
    return [int(year) for year in re.findall(r"\b(19\d{2}|20\d{2})\b", text)]


def _estimate_experience(found_in_skills_section: bool, evidence_lines: List[str]) -> str:
    if not evidence_lines:
        return "Listed in the resume" if found_in_skills_section else "Not enough evidence to estimate"

    explicit_years = []
    calendar_years = []

    for line in evidence_lines:
        explicit_years.extend(_extract_explicit_years(line))
        calendar_years.extend(_extract_calendar_years(line))

    if explicit_years:
        max_years = max(explicit_years)
        years_text = str(int(max_years)) if max_years.is_integer() else f"{max_years:.1f}".rstrip("0").rstrip(".")
        return f"About {years_text} years inferred from the resume"

    if len(calendar_years) >= 2:
        span = max(calendar_years) - min(calendar_years) + 1
        return f"About {max(1, span)} years inferred from dated experience lines"

    if len(evidence_lines) >= 3:
        return "Repeated across several experience lines"
    if len(evidence_lines) == 2:
        return "Supported by more than one experience line"
    return "Supported by one experience line"


def run_skill_analysis(sections: Dict[str, Any], jd_text: str) -> Dict[str, Any]:
    resume_skills = _normalize_resume_skills(sections.get("skills", []))
    experience_lines = sections.get("experience", [])
    target_skills = _extract_target_skills(jd_text)

    validated_skills = []
    missing_skills = []

    for skill in target_skills:
        found_in_skills_section = skill in resume_skills
        evidence_lines = _find_skill_evidence(skill, experience_lines)

        if found_in_skills_section or evidence_lines:
            sources = []
            if found_in_skills_section:
                sources.append("skills_section")
            if evidence_lines:
                sources.append("experience")

            validated_skills.append(
                {
                    "skill": skill,
                    "evidence": _summarize_evidence(found_in_skills_section, evidence_lines),
                    "evidence_lines": evidence_lines,
                    "source": sources,
                    "experience_estimate": _estimate_experience(found_in_skills_section, evidence_lines),
                }
            )
        else:
            missing_skills.append(skill)

    return {
        "validated_skills": validated_skills,
        "missing_skills": missing_skills,
    }