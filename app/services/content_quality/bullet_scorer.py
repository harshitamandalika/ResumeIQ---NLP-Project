import os
import re
import warnings
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv

_DEBUG_WARNINGS = os.getenv("CONTENT_QUALITY_DEBUG_WARNINGS", "0") == "1"
if not _DEBUG_WARNINGS:
    warnings.filterwarnings("ignore", category=FutureWarning, module=r"google(\.|$)")
    warnings.filterwarnings(
        "ignore",
        message=r"(?s).*All support for the `google\.generativeai` package has ended.*",
        category=FutureWarning,
    )

import google.generativeai as genai


load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "models/gemini-flash-latest")
CONTENT_QUALITY_DEBUG_WARNINGS = os.getenv("CONTENT_QUALITY_DEBUG_WARNINGS", "0") == "1"
REWRITE_THRESHOLD = 55

# Configure Gemini only if key exists
_GEMINI_ENABLED = bool(GOOGLE_API_KEY)
if _GEMINI_ENABLED:
    genai.configure(api_key=GOOGLE_API_KEY)
    _gemini_model = genai.GenerativeModel(GEMINI_MODEL_NAME)
else:
    _gemini_model = None


STRONG_ACTION_VERBS = {
    "built", "developed", "designed", "implemented", "engineered", "created",
    "optimized", "improved", "automated", "deployed", "integrated", "led",
    "architected", "reduced", "increased", "scaled", "delivered", "launched",
    "analyzed", "trained", "evaluated", "fine-tuned", "generated", "refactored",
    "streamlined", "modernized", "migrated", "orchestrated", "debugged",
}

WEAK_START_PHRASES = {
    "worked on", "helped", "assisted", "involved in", "responsible for",
    "participated in", "contributed to",
}

TECH_HINTS = {
    "python", "java", "c++", "javascript", "typescript", "react", "next.js",
    "fastapi", "django", "flask", "sql", "mongodb", "postgresql", "api",
    "rest", "docker", "kubernetes", "aws", "azure", "gcp", "machine learning",
    "deep learning", "nlp", "bert", "transformers", "tensorflow", "pytorch",
    "scikit-learn", "data", "pipeline", "model", "embedding", "rag",
    "frontend", "backend", "web", "ui", "ux", "software", "application",
    "microservice", "microservices", "database", "cloud", "ml", "llm",
}

METRIC_PROMPT = (
    "Add a real measurable outcome if available, such as percentage improvement, "
    "latency reduction, time saved, scale handled, revenue impact, user growth, "
    "or reduction in manual steps."
)


def _normalize(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def _starts_with_strong_action_verb(text: str) -> bool:
    words = _normalize(text).split()
    if not words:
        return False
    return words[0] in STRONG_ACTION_VERBS


def _starts_with_weak_phrase(text: str) -> bool:
    normalized = _normalize(text)
    return any(normalized.startswith(phrase) for phrase in WEAK_START_PHRASES)


def _has_metric(text: str) -> bool:
    normalized = _normalize(text)

    metric_patterns = [
        r"\b\d+(\.\d+)?\s*%",
        r"\b\d+(\.\d+)?\b",
        r"\b\d+\+",
        r"\b\d+x\b",
        r"\bmillions?\b",
        r"\bbillions?\b",
        r"\bthousands?\b",
        r"\bseconds?\b",
        r"\bminutes?\b",
        r"\bhours?\b",
        r"\bdays?\b",
        r"\byears?\b",
        r"\bms\b",
    ]

    return any(re.search(pattern, normalized) for pattern in metric_patterns)


def _has_technical_depth(text: str) -> bool:
    normalized = _normalize(text)
    return any(hint in normalized for hint in TECH_HINTS)


def _is_too_short(text: str) -> bool:
    return len(_normalize(text).split()) < 6


def _is_too_vague(text: str) -> bool:
    normalized = _normalize(text)

    vague_patterns = [
        r"^worked on\b",
        r"^helped\b",
        r"^assisted\b",
        r"^responsible for\b",
        r"^involved in\b",
        r"^participated in\b",
        r"^contributed to\b",
    ]

    return any(re.search(pattern, normalized) for pattern in vague_patterns)


def _build_metric_prompt(issues: List[str]) -> str:
    if "missing_metric" in issues:
        return METRIC_PROMPT
    return ""


def _fallback_rewrite(text: str, issues: List[str]) -> str:
    """
    Safe deterministic fallback when Gemini is unavailable or fails.
    Does not invent metrics.
    """
    rewritten = text.strip()

    weak_prefix_map = {
        "worked on": "Developed",
        "helped": "Supported",
        "assisted": "Supported",
        "involved in": "Contributed to",
        "responsible for": "Managed",
        "participated in": "Contributed to",
        "contributed to": "Contributed to",
    }

    normalized = _normalize(rewritten)

    for phrase, replacement in weak_prefix_map.items():
        if normalized.startswith(phrase):
            pattern = re.compile(rf"^{re.escape(phrase)}", re.IGNORECASE)
            rewritten = pattern.sub(replacement, rewritten, count=1)
            break

    # Capitalize first letter if needed
    if rewritten:
        rewritten = rewritten[0].upper() + rewritten[1:]

    # If bullet is very short and generic, add a modest specificity phrase without inventing metrics
    if "too_short" in issues and "missing_metric" in issues:
        if not rewritten.endswith("."):
            rewritten += "."
        rewritten = rewritten.rstrip(".") + " using relevant tools and technologies."

    return rewritten


def _rewrite_with_gemini(text: str, issues: List[str]) -> str:
    """
    Gemini rewrite that improves clarity without inventing metrics.
    Returns plain rewritten bullet text only.
    """
    if not _GEMINI_ENABLED or _gemini_model is None:
        return _fallback_rewrite(text, issues)

    prompt = f"""
Rewrite this resume bullet to be stronger and clearer.

Rules:
- Use a strong action verb.
- Be concise and professional.
- Improve clarity and specificity.
- DO NOT invent metrics, percentages, counts, time savings, business impact, or results.
- If the original bullet has no metric, keep the rewrite metric-free.
- Preserve the original meaning faithfully.
- Return only one rewritten bullet and nothing else.

Bullet:
{text}

Issues to address:
{", ".join(issues)}
""".strip()

    try:
        response = _gemini_model.generate_content(prompt)
        rewritten = (response.text or "").strip()

        # Remove accidental markdown bullets or quotes
        rewritten = rewritten.lstrip("-• ").strip().strip('"').strip("'")

        if not rewritten:
            return _fallback_rewrite(text, issues)

        return rewritten
    except Exception as exc:
        if CONTENT_QUALITY_DEBUG_WARNINGS:
            print("Gemini rewrite error:", exc)
        return _fallback_rewrite(text, issues)


def _score_bullet(text: str) -> Dict[str, Any]:
    score = 50
    issues = []

    strong_verb = _starts_with_strong_action_verb(text)
    weak_phrase = _starts_with_weak_phrase(text)
    has_metric = _has_metric(text)
    technical_depth = _has_technical_depth(text)
    too_short = _is_too_short(text)
    too_vague = _is_too_vague(text)

    if strong_verb:
        score += 15
    else:
        issues.append("weak_action_verb")

    if weak_phrase:
        score -= 15
        if "weak_action_verb" not in issues:
            issues.append("weak_action_verb")

    if has_metric:
        score += 20
    else:
        issues.append("missing_metric")

    if technical_depth:
        score += 10
    else:
        issues.append("low_technical_depth")

    if too_short:
        score -= 15
        issues.append("too_short")

    if too_vague:
        score -= 10
        issues.append("vague_wording")

    score = max(0, min(100, score))
    issues = sorted(list(set(issues)))

    return {
        "text": text,
        "score": score,
        "issues": issues,
        "rewrite": None,
        "needs_user_metric": "missing_metric" in issues,
        "metric_prompt": _build_metric_prompt(issues),
    }


def run_content_quality(experience: List[str]) -> Dict[str, Any]:
    bullet_scores = []

    for bullet in experience:
        bullet = bullet.strip()
        if not bullet:
            continue

        result = _score_bullet(bullet)

        if result["score"] < REWRITE_THRESHOLD:
            result["rewrite"] = _rewrite_with_gemini(
                result["text"],
                result["issues"],
            )

        bullet_scores.append(result)

    return {
        "bullet_scores": bullet_scores
    }