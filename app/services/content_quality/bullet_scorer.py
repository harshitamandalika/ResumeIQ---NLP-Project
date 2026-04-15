import os
import re
import warnings
from typing import Any, Dict, List

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv():
        return False

_DEBUG_WARNINGS = os.getenv("CONTENT_QUALITY_DEBUG_WARNINGS", "0") == "1"
if not _DEBUG_WARNINGS:
    warnings.filterwarnings("ignore", category=FutureWarning, module=r"google(\.|$)")
    warnings.filterwarnings(
        "ignore",
        message=r"(?s).*All support for the `google\.generativeai` package has ended.*",
        category=FutureWarning,
    )

try:
    import google.generativeai as genai
except ImportError:
    genai = None


load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "models/gemini-flash-latest")
CONTENT_QUALITY_DEBUG_WARNINGS = os.getenv("CONTENT_QUALITY_DEBUG_WARNINGS", "0") == "1"
REWRITE_THRESHOLD = 55

_GEMINI_ENABLED = bool(GOOGLE_API_KEY and genai is not None)
if _GEMINI_ENABLED:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        _gemini_model = genai.GenerativeModel(GEMINI_MODEL_NAME)
    except Exception:
        _gemini_model = None
        _GEMINI_ENABLED = False
else:
    _gemini_model = None


ACTION_VERBS = {
    "achieved", "analyzed", "architected", "automated", "built", "collaborated",
    "created", "debugged", "delivered", "designed", "developed", "drove",
    "engineered", "enhanced", "evaluated", "fine-tuned", "generated",
    "implemented", "improved", "integrated", "launched", "led", "managed",
    "migrated", "modernized", "optimized", "orchestrated", "reduced",
    "refactored", "scaled", "streamlined", "trained",
}

WEAK_STARTERS = {
    "worked on", "helped", "assisted", "involved in", "responsible for",
    "participated in", "contributed to", "tasked with",
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


def _normalize_bullet(text: str) -> str:
    text = text.strip().lstrip("-*• ").strip()
    return re.sub(r"\s+", " ", text)


def _starts_with_action_verb(bullet: str) -> bool:
    words = _normalize_bullet(bullet).lower().split()
    if not words:
        return False
    return words[0] in ACTION_VERBS


def _has_metric(bullet: str) -> bool:
    normalized = _normalize_bullet(bullet).lower()
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
        r"\$",
    ]
    return any(re.search(pattern, normalized) for pattern in metric_patterns)


def _has_technical_depth(bullet: str) -> bool:
    normalized = _normalize_bullet(bullet).lower()
    return any(hint in normalized for hint in TECH_HINTS)


def _has_weak_start(bullet: str) -> bool:
    lowered = _normalize_bullet(bullet).lower()
    return any(lowered.startswith(starter) for starter in WEAK_STARTERS)


def _is_too_short(bullet: str) -> bool:
    return len(_normalize_bullet(bullet).split()) < 6


def _has_process_detail(bullet: str) -> bool:
    return bool(re.search(r"\b(using|with|through|by)\b", _normalize_bullet(bullet).lower()))


def _dedupe_keep_order(items: List[str]) -> List[str]:
    seen = set()
    output = []

    for item in items:
        if item not in seen:
            seen.add(item)
            output.append(item)

    return output


def _score_bullet(bullet: str) -> tuple[int, List[str]]:
    normalized_bullet = _normalize_bullet(bullet)
    issues: List[str] = []
    score = 50

    if _starts_with_action_verb(normalized_bullet):
        score += 15
    else:
        issues.append("Start with a stronger action verb")

    if _has_weak_start(normalized_bullet):
        score -= 15
        issues.append("Avoid weak openings such as 'worked on' or 'helped'")

    if _has_metric(normalized_bullet):
        score += 20
    else:
        issues.append("Add a measurable outcome")

    if _has_technical_depth(normalized_bullet):
        score += 10
    else:
        issues.append("Add more technical detail")

    if _is_too_short(normalized_bullet):
        score -= 15
        issues.append("Keep the bullet concise and specific")

    if not _has_process_detail(normalized_bullet):
        score -= 5
        issues.append("Clarify how the work was completed")

    return max(0, min(score, 100)), _dedupe_keep_order(issues)


def _fallback_rewrite(bullet: str, issues: List[str]) -> str:
    rewritten = _normalize_bullet(bullet)
    weak_prefix_map = {
        "worked on": "Developed",
        "helped": "Supported",
        "assisted": "Supported",
        "involved in": "Contributed to",
        "responsible for": "Managed",
        "participated in": "Contributed to",
        "contributed to": "Contributed to",
        "tasked with": "Delivered",
    }

    lowered = rewritten.lower()
    for phrase, replacement in weak_prefix_map.items():
        if lowered.startswith(phrase):
            pattern = re.compile(rf"^{re.escape(phrase)}", re.IGNORECASE)
            rewritten = pattern.sub(replacement, rewritten, count=1)
            break

    if rewritten and not _starts_with_action_verb(rewritten):
        rewritten = f"Developed {rewritten[0].lower() + rewritten[1:]}"

    if rewritten and not _has_process_detail(rewritten) and "Clarify how the work was completed" in issues:
        rewritten = rewritten.rstrip(".") + " using relevant tools and technologies"

    if rewritten and rewritten[0].islower():
        rewritten = rewritten[0].upper() + rewritten[1:]

    if rewritten and not rewritten.endswith("."):
        rewritten += "."

    return rewritten


def _rewrite_with_gemini(bullet: str, issues: List[str]) -> str:
    if not _GEMINI_ENABLED or _gemini_model is None:
        return _fallback_rewrite(bullet, issues)

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
{bullet}

Issues to address:
{", ".join(issues)}
""".strip()

    try:
        response = _gemini_model.generate_content(prompt)
        rewritten = (response.text or "").strip()
        rewritten = rewritten.lstrip("-• ").strip().strip('"').strip("'")
        if not rewritten:
            return _fallback_rewrite(bullet, issues)
        if not rewritten.endswith("."):
            rewritten += "."
        return rewritten
    except Exception as exc:
        if CONTENT_QUALITY_DEBUG_WARNINGS:
            print("Gemini rewrite error:", exc)
        return _fallback_rewrite(bullet, issues)


def run_content_quality(experience: List[str]) -> Dict[str, Any]:
    bullet_scores = []

    for bullet in experience:
        normalized_bullet = _normalize_bullet(bullet)
        if not normalized_bullet:
            continue

        score, issues = _score_bullet(normalized_bullet)
        suggested_rewrite = ""

        if issues and score < REWRITE_THRESHOLD:
            suggested_rewrite = _rewrite_with_gemini(normalized_bullet, issues)

        bullet_scores.append(
            {
                "bullet": normalized_bullet,
                "score": score,
                "issues": issues,
                "suggested_rewrite": suggested_rewrite,
            }
        )

    return {
        "bullet_scores": bullet_scores,
    }