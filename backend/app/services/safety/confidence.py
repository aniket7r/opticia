"""Confidence level detection for AI responses."""

import re
from enum import Enum

from pydantic import BaseModel


class ConfidenceLevel(str, Enum):
    """Confidence levels for AI guidance."""

    HIGH = "high"
    MODERATE = "moderate"
    UNCERTAIN = "uncertain"


class ConfidenceAssessment(BaseModel):
    """Result of confidence assessment."""

    level: ConfidenceLevel
    indicators: list[str] = []
    display_text: str = ""


# Patterns indicating uncertainty
UNCERTAINTY_PATTERNS = [
    r"\b(i'm not sure|not certain|might be|could be|possibly|perhaps)\b",
    r"\b(i think|i believe|it seems|appears to be|looks like)\b",
    r"\b(difficult to tell|hard to say|can't be certain)\b",
    r"\b(may or may not|it depends|varies)\b",
]

# Patterns indicating high confidence
HIGH_CONFIDENCE_PATTERNS = [
    r"\b(definitely|certainly|clearly|obviously|absolutely)\b",
    r"\b(this is|that is|you should|you need to)\b",
    r"\b(the correct|the right|the proper)\b",
]


def assess_confidence(content: str) -> ConfidenceAssessment:
    """Assess confidence level of AI response.

    Args:
        content: The AI response content

    Returns:
        ConfidenceAssessment with level and display text
    """
    content_lower = content.lower()
    uncertainty_indicators = []
    confidence_indicators = []

    # Check for uncertainty patterns
    for pattern in UNCERTAINTY_PATTERNS:
        matches = re.findall(pattern, content_lower, re.IGNORECASE)
        uncertainty_indicators.extend(matches)

    # Check for high confidence patterns
    for pattern in HIGH_CONFIDENCE_PATTERNS:
        matches = re.findall(pattern, content_lower, re.IGNORECASE)
        confidence_indicators.extend(matches)

    # Determine overall confidence
    if len(uncertainty_indicators) > 2:
        return ConfidenceAssessment(
            level=ConfidenceLevel.UNCERTAIN,
            indicators=uncertainty_indicators[:5],
            display_text="🤔 I'm not entirely certain about this",
        )
    elif len(uncertainty_indicators) > 0 and len(confidence_indicators) < 2:
        return ConfidenceAssessment(
            level=ConfidenceLevel.MODERATE,
            indicators=uncertainty_indicators[:3],
            display_text="",  # No display for moderate confidence
        )
    else:
        return ConfidenceAssessment(
            level=ConfidenceLevel.HIGH,
            indicators=confidence_indicators[:3],
            display_text="",  # No display needed for high confidence
        )
