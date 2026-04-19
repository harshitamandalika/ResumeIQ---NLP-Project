import json
import os
import re
import warnings
from typing import List, Dict, Any, Optional, Set

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

# =========================
# Runtime / model config
# =========================
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "models/gemini-flash-latest")
CONTENT_QUALITY_DEBUG_WARNINGS = os.getenv("CONTENT_QUALITY_DEBUG_WARNINGS", "0") == "1"

_GEMINI_ENABLED = bool(GOOGLE_API_KEY)
if _GEMINI_ENABLED and genai is not None:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        _gemini_model = genai.GenerativeModel(GEMINI_MODEL_NAME)
    except Exception:
        _gemini_model = None
        _GEMINI_ENABLED = False
else:
    _gemini_model = None


# =========================
# Scoring config
# =========================
BASE_SCORE = 50
STRONG_VERB_BONUS = 15
METRIC_BONUS = 20
TECH_DEPTH_BONUS = 10
WEAK_PHRASE_PENALTY = 15
TOO_SHORT_PENALTY = 15
VAGUE_WORDING_PENALTY = 10
MIN_BULLET_WORDS = 4

REWRITE_TRIGGER_ISSUES: Set[str] = {
    "weak_action_verb",
    "vague_wording",
    "too_short",
    "low_technical_depth",
}

GENERIC_METRIC_PROMPT = (
    "Consider adding a measurable outcome relevant to this bullet, such as percentage improvement, "
    "latency reduction, time saved, scale handled, user impact, revenue impact, or reduction in manual steps."
)

STRONG_ACTION_VERBS = {
    "built", "developed", "designed", "implemented", "engineered", "created",
    "optimized", "improved", "automated", "deployed", "integrated", "led",
    "architected", "reduced", "increased", "scaled", "delivered", "launched",
    "analyzed", "trained", "evaluated", "fine-tuned", "generated", "refactored",
    "streamlined", "modernized", "migrated", "orchestrated", "debugged",
    "applied", "executed", "partnered", "served"
}

WEAK_START_PHRASES = {
    "worked on", "helped", "assisted", "involved in", "responsible for",
    "participated in", "contributed to", "used", "prepared", "experimented with",
    "collaborated with", "covered"
}

TECH_HINTS = {
    "python", "java", "c++", "javascript", "typescript", "react", "next.js",
    "fastapi", "django", "flask", "sql", "mongodb", "postgresql", "api",
    "rest", "docker", "kubernetes", "aws", "azure", "gcp", "machine learning",
    "deep learning", "nlp", "bert", "transformers", "tensorflow", "pytorch",
    "scikit-learn", "data", "pipeline", "model", "embedding", "rag",
    "frontend", "backend", "web", "ui", "ux", "software", "application",
    "microservice", "microservices", "database", "cloud", "ml", "llm",
    "classification", "recommendation", "evaluation", "preprocessing",
    "vector search", "semantic similarity", "deployment"
}


# =========================
# Normalization helpers
# =========================
def _normalize(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def _extract_first_word(text: str) -> str:
    words = _normalize(text).split()
    return words[0] if words else ""


def _is_meaningfully_different(original: str, rewritten: str) -> bool:
    original_norm = _normalize(original).strip(". ")
    rewritten_norm = _normalize(rewritten).strip(". ")
    return original_norm != rewritten_norm


def _extract_actual_bullet_text(text: str) -> Optional[str]:
    """
    Returns cleaned bullet text only if the line begins with a bullet marker.
    Otherwise returns None.
    """
    text = text.strip()
    if not text:
        return None

    match = re.match(r'^[•\-\*]\s+(.*)$', text)
    if not match:
        return None

    bullet_text = match.group(1).strip()

    if len(bullet_text.split()) < MIN_BULLET_WORDS:
        return None

    return bullet_text


# =========================
# Feature detectors
# =========================
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
        r"^used\b",
        r"^prepared\b",
        r"^experimented with\b",
        r"^collaborated with\b",
        r"^covered\b",
    ]

    return any(re.search(pattern, normalized) for pattern in vague_patterns)


# =========================
# Policy helpers
# =========================
def _should_rewrite(issues: Set[str]) -> bool:
    return any(issue in REWRITE_TRIGGER_ISSUES for issue in issues)


def _should_prompt_for_metric(issues: Set[str]) -> bool:
    return "missing_metric" in issues


# =========================
# Safe fallbacks
# =========================
def _fallback_rewrite(text: str, issues: List[str]) -> str:
    rewritten = text.strip()

    weak_prefix_map = {
        "worked on": "Developed",
        "helped": "Supported",
        "assisted": "Supported",
        "involved in": "Contributed to",
        "responsible for": "Managed",
        "participated in": "Contributed to",
        "contributed to": "Contributed to",
        "used": "Implemented",
        "prepared": "Developed",
        "experimented with": "Evaluated",
        "collaborated with": "Partnered with",
        "covered": "Executed",
    }

    normalized = _normalize(rewritten)

    # Check longer phrases first
    for phrase in sorted(weak_prefix_map.keys(), key=len, reverse=True):
        replacement = weak_prefix_map[phrase]
        if normalized.startswith(phrase):
            pattern = re.compile(rf"^{re.escape(phrase)}", re.IGNORECASE)
            rewritten = pattern.sub(replacement, rewritten, count=1)
            break

    if rewritten:
        rewritten = rewritten[0].upper() + rewritten[1:]

    if "missing_metric" in issues and not _has_metric(rewritten):
        rewritten = rewritten.rstrip(". ") + _fallback_metric_template_clause(rewritten)

    if "too_short" in issues:
        if not rewritten.endswith("."):
            rewritten += "."
        rewritten = rewritten.rstrip(".") + " using relevant tools and technologies."

    return rewritten


def _fallback_metric_template_clause(text: str) -> str:
    normalized = _normalize(text)

    if "api" in normalized or "fastapi" in normalized or "backend" in normalized:
        return (
            ", improving [response latency / throughput / integration time] by "
            "[X% / Y ms] across [N] downstream services or workflows."
        )
    if "frontend" in normalized or "ui" in normalized or "web" in normalized:
        return (
            ", improving [page load time / adoption / task completion rate] by "
            "[X%] for [N] users or sessions."
        )
    if "nlp" in normalized or "classification" in normalized or "information extraction" in normalized:
        return (
            ", improving [accuracy / F1 / processing time] by [X%] across [N] documents or samples."
        )
    if "model" in normalized or "machine learning" in normalized or "deep learning" in normalized:
        return (
            ", improving [model accuracy / inference latency / training efficiency] by "
            "[X% / Y ms] on [N] requests or samples."
        )
    if "embedding" in normalized or "vector search" in normalized or "semantic similarity" in normalized:
        return (
            ", improving [retrieval relevance / ranking quality / query latency] by "
            "[X% / Y ms] across [N] queries or documents."
        )

    return ", driving [measurable outcome] by [X% / Y units] across [project scope]."


def _fallback_metric_prompt(text: str) -> str:
    normalized = _normalize(text)

    if "api" in normalized or "fastapi" in normalized or "backend" in normalized:
        return (
            "Consider adding a measurable outcome such as API response latency, request throughput, "
            "number of downstream services supported, or reduction in integration time."
        )
    if "nlp" in normalized or "classification" in normalized or "information extraction" in normalized:
        return (
            "Consider adding measurable outcomes such as dataset size processed, model accuracy or F1 improvement, "
            "reduction in manual review effort, or processing time improvement."
        )
    if "frontend" in normalized or "ui" in normalized or "web" in normalized:
        return (
            "Consider adding measurable outcomes such as page load improvement, reduction in user steps, "
            "feature adoption, or improvement in user engagement."
        )
    if "model" in normalized or "machine learning" in normalized or "deep learning" in normalized:
        return (
            "Consider adding measurable outcomes such as model accuracy improvement, inference latency reduction, "
            "training efficiency gain, or scale of data handled."
        )
    if "embedding" in normalized or "vector search" in normalized or "semantic similarity" in normalized:
        return (
            "Consider adding measurable outcomes such as ranking quality improvement, retrieval relevance gains, "
            "query latency reduction, or number of documents processed."
        )

    return GENERIC_METRIC_PROMPT


# =========================
# LLM helpers
# =========================
def _extract_json_block(text: str) -> Optional[Dict[str, Any]]:
    text = text.strip()

    try:
        return json.loads(text)
    except Exception:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None

    try:
        return json.loads(match.group(0))
    except Exception:
        return None


def _generate_bullet_improvement_with_gemini(
    text: str,
    issues: List[str],
    used_opening_verbs: Set[str],
    should_rewrite: bool,
    should_prompt_metric: bool,
) -> Dict[str, str]:
    """
    Returns:
    {
      "rewrite": "... or empty string",
      "metric_prompt": "... or empty string"
    }
    """
    if not _GEMINI_ENABLED or _gemini_model is None:
        return {
            "rewrite": _fallback_rewrite(text, issues) if should_rewrite else "",
            "metric_prompt": _fallback_metric_prompt(text) if should_prompt_metric else "",
        }

    avoided_verbs = ", ".join(sorted(used_opening_verbs)) if used_opening_verbs else "none"

    prompt = f"""
You are improving a resume bullet in a safe and factual way.

Tasks:
1. Rewrite the bullet only if rewrite_needed is true.
2. Suggest a customized metric prompt only if metric_prompt_needed is true.

Constraints:
- Do NOT invent metrics, percentages, counts, time savings, business impact, or results.
- Preserve the original meaning faithfully.
- If rewriting is needed because of weak_action_verb, vague_wording, too_short, or low_technical_depth, the rewrite should be meaningfully improved and should not simply repeat the original bullet.
- Replace weak opening verbs such as "used", "worked on", "helped", "prepared", "experimented with", "collaborated with", or "covered" with a stronger and more specific alternative when appropriate.
- Use one strong opening action verb.
- Try not to reuse these opening verbs if a natural alternative exists: {avoided_verbs}
- Keep the rewrite concise, professional, and metric-free if the original has no metric.
- If metric_prompt_needed is true, prefer a fill-in template rewrite with bracketed placeholders such as [X%], [Y ms], [N users], or [N services] instead of generic paraphrasing.
- The metric suggestion must describe only the kinds of measurable outcomes the user could add, not actual values.

Inputs:
bullet: "{text}"
issues: {issues}
rewrite_needed: {str(should_rewrite).lower()}
metric_prompt_needed: {str(should_prompt_metric).lower()}

Return strict JSON only in this format:
{{
  "rewrite": "string or empty string",
  "metric_prompt": "string or empty string"
}}
""".strip()

    try:
        response = _gemini_model.generate_content(prompt)
        raw = (response.text or "").strip()
        parsed = _extract_json_block(raw)

        if not parsed:
            return {
                "rewrite": _fallback_rewrite(text, issues) if should_rewrite else "",
                "metric_prompt": _fallback_metric_prompt(text) if should_prompt_metric else "",
            }

        rewrite = str(parsed.get("rewrite", "") or "").strip()
        metric_prompt = str(parsed.get("metric_prompt", "") or "").strip()

        rewrite = rewrite.lstrip("-• ").strip().strip('"').strip("'")
        metric_prompt = metric_prompt.strip().strip('"').strip("'")

        if should_rewrite:
            if not rewrite or not _is_meaningfully_different(text, rewrite):
                rewrite = _fallback_rewrite(text, issues)

        if should_prompt_metric and not metric_prompt:
            metric_prompt = _fallback_metric_prompt(text)

        if not should_rewrite:
            rewrite = ""

        if not should_prompt_metric:
            metric_prompt = ""

        return {
            "rewrite": rewrite,
            "metric_prompt": metric_prompt,
        }

    except Exception as exc:
        if CONTENT_QUALITY_DEBUG_WARNINGS:
            print("Gemini content quality error:", exc)

        return {
            "rewrite": _fallback_rewrite(text, issues) if should_rewrite else "",
            "metric_prompt": _fallback_metric_prompt(text) if should_prompt_metric else "",
        }


# =========================
# Scoring
# =========================
def _score_bullet(text: str) -> Dict[str, Any]:
    score = BASE_SCORE
    issues: List[str] = []

    strong_verb = _starts_with_strong_action_verb(text)
    weak_phrase = _starts_with_weak_phrase(text)
    has_metric = _has_metric(text)
    technical_depth = _has_technical_depth(text)
    too_short = _is_too_short(text)
    too_vague = _is_too_vague(text)

    if strong_verb:
        score += STRONG_VERB_BONUS
    else:
        issues.append("weak_action_verb")

    if weak_phrase:
        score -= WEAK_PHRASE_PENALTY
        if "weak_action_verb" not in issues:
            issues.append("weak_action_verb")

    if has_metric:
        score += METRIC_BONUS
    else:
        issues.append("missing_metric")

    if technical_depth:
        score += TECH_DEPTH_BONUS
    else:
        issues.append("low_technical_depth")

    if too_short:
        score -= TOO_SHORT_PENALTY
        issues.append("too_short")

    if too_vague:
        score -= VAGUE_WORDING_PENALTY
        issues.append("vague_wording")

    score = max(0, min(100, score))
    issues = sorted(set(issues))

    return {
        "text": text,
        "score": score,
        "issues": issues,
        "rewrite": None,
        "needs_user_metric": False,
        "metric_prompt": "",
    }


# =========================
# Public API
# =========================
def run_content_quality(experience: List[str]) -> Dict[str, Any]:
    bullet_scores = []
    used_opening_verbs: Set[str] = set()

    for line in experience:
        cleaned_bullet = _extract_actual_bullet_text(line)
        if not cleaned_bullet:
            continue

        result = _score_bullet(cleaned_bullet)
        issues = set(result["issues"])

        should_rewrite = _should_rewrite(issues)
        should_prompt_metric = _should_prompt_for_metric(issues)

        if should_rewrite or should_prompt_metric:
            llm_output = _generate_bullet_improvement_with_gemini(
                text=result["text"],
                issues=result["issues"],
                used_opening_verbs=used_opening_verbs,
                should_rewrite=should_rewrite,
                should_prompt_metric=should_prompt_metric,
            )

            rewrite = llm_output.get("rewrite", "").strip()
            metric_prompt = llm_output.get("metric_prompt", "").strip()

            if should_rewrite and rewrite:
                result["rewrite"] = rewrite
                opening_verb = _extract_first_word(rewrite)
                if opening_verb:
                    used_opening_verbs.add(opening_verb)

            if should_prompt_metric and metric_prompt:
                result["needs_user_metric"] = True
                result["metric_prompt"] = metric_prompt

        bullet_scores.append(result)

    return {
        "bullet_scores": bullet_scores
    }