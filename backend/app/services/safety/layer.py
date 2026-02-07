"""Unified safety layer integrating all safety components."""

import logging
from typing import Any

from pydantic import BaseModel

from app.services.safety.confidence import ConfidenceAssessment, assess_confidence
from app.services.safety.disclaimers import inject_safety_content
from app.services.safety.risk_assessment import RiskAssessment, assess_risk

logger = logging.getLogger(__name__)


class SafetyResult(BaseModel):
    """Combined result of all safety checks."""

    original_content: str
    processed_content: str
    risk: RiskAssessment
    confidence: ConfidenceAssessment
    was_modified: bool = False


def process_ai_response(
    content: str,
    context: dict[str, Any] | None = None,
) -> SafetyResult:
    """Process AI response through safety layer.

    Applies:
    1. Risk assessment
    2. Disclaimer injection
    3. Confidence assessment

    Args:
        content: Raw AI response
        context: Optional conversation context

    Returns:
        SafetyResult with processed content and assessments
    """
    # 1. Assess risk
    risk = assess_risk(content, context)
    logger.debug(f"Risk assessment: {risk.tier}, triggers: {risk.triggers}")

    # 2. Inject disclaimers if needed
    processed = inject_safety_content(content, risk)
    was_modified = processed != content

    # 3. Assess confidence
    confidence = assess_confidence(content)

    # Add confidence indicator if uncertain
    if confidence.display_text:
        processed = f"{confidence.display_text}\n\n{processed}"
        was_modified = True

    return SafetyResult(
        original_content=content,
        processed_content=processed,
        risk=risk,
        confidence=confidence,
        was_modified=was_modified,
    )


def get_safety_prompt_addition() -> str:
    """Get safety-related additions for the system prompt.

    This is added to the Gemini system prompt.
    """
    return """
## Safety Guidelines

When providing guidance:
1. For medical, legal, or financial topics: Always recommend consulting a professional
2. For electrical, gas, or structural work: Emphasize safety and professional help
3. Never claim something is "safe" or "harmless" - I cannot verify physical conditions
4. Express uncertainty when you're not confident
5. If you see potential danger, warn the user clearly
6. Preserve context of errors to help correct course

Risk awareness levels:
- Low risk: General information, everyday tasks
- Medium risk: DIY repairs, cooking, child-related activities
- High risk: Medical, legal, financial, electrical, gas, structural topics
"""
