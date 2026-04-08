# scoring + rewriting

import re


ACTION_VERBS = {
    "achieved", "analyzed", "automated", "built", "collaborated", "created",
    "delivered", "designed", "developed", "drove", "enhanced", "evaluated",
    "implemented", "improved", "launched", "led", "managed", "optimized",
    "reduced", "streamlined", "trained"
}

WEAK_STARTERS = {
    "worked on", "helped", "responsible for", "involved in", "tasked with"
}


def _normalize_bullet(text):
    return text.strip().lstrip("-• ").strip()


def _starts_with_action_verb(bullet):
    first_word = bullet.split()[0].lower() if bullet.split() else ""
    return first_word in ACTION_VERBS


def _has_metric(bullet):
    return bool(re.search(r"\b\d+[\d,.]*\b|%|\$", bullet))


def _has_weak_start(bullet):
    lowered = bullet.lower()
    return any(lowered.startswith(starter) for starter in WEAK_STARTERS)


def _strip_weak_start(bullet):
    lowered = bullet.lower()

    for starter in WEAK_STARTERS:
        if lowered.startswith(starter):
            return bullet[len(starter):].strip(" ,.")

    return bullet


def _score_bullet(bullet):
    normalized_bullet = _normalize_bullet(bullet)
    issues = []
    score = 10

    if _starts_with_action_verb(normalized_bullet):
        score += 25
    else:
        issues.append("Start with a stronger action verb")

    if _has_metric(normalized_bullet):
        score += 25
    else:
        issues.append("Add a measurable outcome")

    word_count = len(normalized_bullet.split())
    if 10 <= word_count <= 30:
        score += 15
    else:
        issues.append("Keep the bullet concise and specific")

    if not _has_weak_start(normalized_bullet):
        score += 15
    else:
        issues.append("Avoid weak openings such as 'worked on' or 'helped'")

    if re.search(r"\b(using|with|through|by)\b", normalized_bullet.lower()):
        score += 10
    else:
        issues.append("Clarify how the work was completed")

    return min(score, 100), issues


def _build_rewrite(bullet, issues):
    normalized_bullet = _strip_weak_start(_normalize_bullet(bullet))
    rewritten = normalized_bullet[:1].upper() + normalized_bullet[1:] if normalized_bullet else ""

    if rewritten and not _starts_with_action_verb(rewritten):
        rewritten = f"Developed {rewritten[0].lower() + rewritten[1:]}"

    if rewritten and not _has_metric(rewritten):
        rewritten = rewritten.rstrip(".") + ", with a clear metric for speed, scale, or quality"

    if rewritten and "Clarify how the work was completed" in issues:
        rewritten = rewritten.rstrip(".") + " using the key tools or methods involved"

    if rewritten and not rewritten.endswith("."):
        rewritten += "."

    return rewritten


def run_content_quality(experience):
    bullet_scores = []

    for bullet in experience:
        normalized_bullet = _normalize_bullet(bullet)
        if not normalized_bullet:
            continue

        score, issues = _score_bullet(normalized_bullet)
        bullet_scores.append(
            {
                "bullet": normalized_bullet,
                "score": score,
                "issues": issues,
                "suggested_rewrite": _build_rewrite(normalized_bullet, issues) if issues else "",
            }
        )

    return {
        "bullet_scores": bullet_scores,
    }