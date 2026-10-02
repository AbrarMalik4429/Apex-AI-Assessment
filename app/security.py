"""Defense in depth. Pattern screening is not the authorization boundary."""

import re
import unicodedata


def screened_text(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKC", text) if unicodedata.category(c) != "Cf"
    ).casefold()


def injection_attempt(text: str) -> bool:
    text = screened_text(text)
    patterns = (
        r"(?:ignore|override|disregard|forget).{0,45}(?:instructions|system prompt|rules|safeguards)",
        r"(?:reveal|print|show|leak|give|return).{0,55}(?:system prompt|api.?key|password|credentials|environment variables|\.env)",
        r"(?:bypass|skip|disable).{0,35}(?:confirmation|ownership|authentication|validation|safety)",
        r"(?:execute|run).{0,25}(?:sql|shell|python code|command)",
        r"(?:system|developer)\s*:",
        r"(?:change|switch|set).{0,20}patient.?id",
        r"(?:drop\s+table|union\s+select|<script|javascript:)",
    )
    return any(re.search(pattern, text) for pattern in patterns)


def emergency_signal(text: str) -> bool:
    # Conservative safety net; the intent model also detects emergencies.
    return bool(
        re.search(
            r"\b(?:not breathing|can[’']?t breathe|cannot breathe|chest pain|severe bleeding|"
            r"unconscious|unresponsive|choking|overdose|kill myself|suicide|face drooping)\b",
            screened_text(text),
        )
    )
