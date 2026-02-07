"""Risk assessment system for AI guidance.

Classifies guidance into risk tiers and triggers appropriate safety measures.
"""

import logging
import re
from enum import Enum
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class RiskTier(str, Enum):
    """Risk tier levels for AI guidance."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RiskAssessment(BaseModel):
    """Result of risk assessment."""

    tier: RiskTier
    category: str | None = None
    triggers: list[str] = []
    requires_disclaimer: bool = False
    requires_referral: bool = False
    referral_type: str | None = None


# Keywords/patterns that trigger different risk levels
HIGH_RISK_PATTERNS = {
    "medical": [
        r"\b(diagnos|symptom|treatment|medication|dosage|prescription|disease|illness|injury|pain|bleeding|surgery|emergency)\b",
        r"\b(heart attack|stroke|seizure|allergic reaction|difficulty breathing)\b",
    ],
    "legal": [
        r"\b(legal advice|lawsuit|sue|contract|liability|court|attorney|lawyer)\b",
        r"\b(criminal|arrest|warrant|custody|divorce)\b",
    ],
    "financial": [
        r"\b(investment advice|stock|trading|tax advice|loan|mortgage|bankruptcy)\b",
        r"\b(financial planning|retirement|estate planning)\b",
    ],
    "electrical": [
        r"\b(electrical wiring|breaker|fuse box|high voltage|power line)\b",
        r"\b(outlet replacement|electrical panel|circuit)\b",
    ],
    "gas": [
        r"\b(gas leak|gas line|propane|natural gas|carbon monoxide)\b",
    ],
    "structural": [
        r"\b(load bearing|foundation|structural|building code|permit)\b",
    ],
}

MEDIUM_RISK_PATTERNS = {
    "diy_repair": [
        r"\b(repair|fix|replace|install|assemble)\b.*\b(careful|caution|safety)\b",
    ],
    "cooking": [
        r"\b(raw meat|temperature|food safety|allergen)\b",
    ],
    "children": [
        r"\b(child|baby|infant|toddler)\b.*\b(safety|supervision)\b",
    ],
}


def assess_risk(content: str, context: dict[str, Any] | None = None) -> RiskAssessment:
    """Assess risk level of AI guidance content.

    Args:
        content: The AI response content to assess
        context: Optional context (conversation history, topic, etc.)

    Returns:
        RiskAssessment with tier and recommendations
    """
    content_lower = content.lower()
    triggers = []

    # Check high-risk patterns
    for category, patterns in HIGH_RISK_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, content_lower, re.IGNORECASE):
                triggers.append(f"high:{category}")

    if triggers:
        # Determine referral type based on category
        category = triggers[0].split(":")[1]
        referral_map = {
            "medical": "healthcare professional",
            "legal": "licensed attorney",
            "financial": "financial advisor",
            "electrical": "licensed electrician",
            "gas": "gas company or licensed plumber",
            "structural": "structural engineer or contractor",
        }

        return RiskAssessment(
            tier=RiskTier.HIGH,
            category=category,
            triggers=triggers,
            requires_disclaimer=True,
            requires_referral=True,
            referral_type=referral_map.get(category, "qualified professional"),
        )

    # Check medium-risk patterns
    for category, patterns in MEDIUM_RISK_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, content_lower, re.IGNORECASE):
                triggers.append(f"medium:{category}")

    if triggers:
        return RiskAssessment(
            tier=RiskTier.MEDIUM,
            category=triggers[0].split(":")[1],
            triggers=triggers,
            requires_disclaimer=True,
            requires_referral=False,
        )

    # Default to low risk
    return RiskAssessment(
        tier=RiskTier.LOW,
        requires_disclaimer=False,
        requires_referral=False,
    )
