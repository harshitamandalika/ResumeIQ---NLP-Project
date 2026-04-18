import re
from typing import List, Dict, Any, Set

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from app.services.alignment.sbert_similarity import (
    extract_keywords,
    filter_keywords,
    extract_skills_from_jd,
    normalize_keyword,
    normalize_text,
    sbert_model,
)

SEMANTIC_MATCH_THRESHOLD = 0.38
MAX_EVIDENCE_PER_SKILL = 3

# Canonical skill -> known aliases / surface forms
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
    """
    Stronger normalization than the shared normalize_text().
    Used only inside skill validation for matching robustness.
    """
    text = text.lower()
    text = text.replace("-", " ")
    text = text.replace("/", " ")
    text = re.sub(r"[^\w\s+.#]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    # Reuse shared normalization last
    return normalize_text(text)


def _canonicalize_skill(skill: str) -> str:
    skill = _normalize_for_matching(skill)
    skill = normalize_keyword(skill)
    return ALIASES_TO_CANONICAL.get(skill, skill)


def _generate_variants(skill: str) -> Set[str]:
    """
    Generic variant generation:
    - canonical form
    - alias forms
    - singular form for simple plurals
    - hyphen/space variations
    """
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
    """
    Reuses the same extraction strategy as the alignment module:
    - KeyBERT keywords
    - rule-based skill detection
    - canonical normalization
    """
    keywords_keybert = extract_keywords(jd_text)
    keywords_keybert = filter_keywords(keywords_keybert)

    keywords_rule = extract_skills_from_jd(jd_text)

    combined = keywords_keybert + keywords_rule
    canonicalized = [_canonicalize_skill(skill) for skill in combined]

    return _dedupe_keep_order(canonicalized)


def _normalize_resume_skills(skills: List[str]) -> List[str]:
    normalized = []

    for skill in skills:
        skill = _canonicalize_skill(skill)
        if skill:
            normalized.append(skill)

    return _dedupe_keep_order(normalized)


def _contains_variant(text: str, skill: str) -> bool:
    normalized_text = _normalize_for_matching(text)

    for variant in _generate_variants(skill):
        pattern = r"\b" + re.escape(variant).replace(r"\ ", r"\s+") + r"\b"
        if re.search(pattern, normalized_text):
            return True

    return False


def _semantic_match_score(skill: str, text: str) -> float:
    embeddings = sbert_model.encode([skill, text])
    score = cosine_similarity(
        np.asarray([embeddings[0]]),
        np.asarray([embeddings[1]]),
    )[0][0]
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

    semantic_matches.sort(key=lambda x: x[0], reverse=True)

    evidence = exact_or_variant_matches[:MAX_EVIDENCE_PER_SKILL]
    remaining = MAX_EVIDENCE_PER_SKILL - len(evidence)

    if remaining > 0:
        evidence.extend([line for _, line in semantic_matches[:remaining]])

    return _dedupe_keep_order(evidence)


def _summarize_evidence(evidence_lines: List[str]) -> str:
    return evidence_lines[0] if evidence_lines else ""


def run_skill_analysis(sections: Dict[str, Any], jd_text: str) -> Dict[str, Any]:
    """
    Input:
    {
      "skills": [...],
      "experience": [...]
    }

    Output:
    {
      "validated_skills": [
        {
          "skill": "python",
                    "evidence": "Built REST APIs using FastAPI for an NLP application.",
                    "evidence_lines": [...],
                    "source": ["experience"]
        }
      ],
      "missing_skills": ["docker"]
    }
    """
    experience_lines = sections.get("experience", [])

    target_skills = _extract_target_skills(jd_text)

    validated_skills = []
    missing_skills = []

    for skill in target_skills:
        evidence_lines = _find_skill_evidence(skill, experience_lines)

        if evidence_lines:
            validated_skills.append({
                "skill": skill,
                "evidence": _summarize_evidence(evidence_lines),
                "evidence_lines": evidence_lines,
                "source": ["experience"],
            })
        else:
            missing_skills.append(skill)

    return {
        "validated_skills": validated_skills,
        "missing_skills": missing_skills,
    }