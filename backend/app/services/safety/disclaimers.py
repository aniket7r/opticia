"""Disclaimer injection based on risk assessment."""

from app.services.safety.risk_assessment import RiskAssessment, RiskTier


# Disclaimer templates
DISCLAIMERS = {
    RiskTier.HIGH: {
        "medical": "⚠️ This is general information only, not medical advice. Please consult a healthcare professional for proper diagnosis and treatment.",
        "legal": "⚠️ This information is for general guidance only and does not constitute legal advice. Please consult a licensed attorney for your specific situation.",
        "financial": "⚠️ This is general information, not financial advice. Please consult a qualified financial advisor before making financial decisions.",
        "electrical": "⚠️ Electrical work can be dangerous and may require permits. Please consult a licensed electrician for safety.",
        "gas": "⚠️ Gas-related issues can be extremely dangerous. If you smell gas, leave immediately and call your gas company or emergency services.",
        "structural": "⚠️ Structural changes may require permits and professional assessment. Please consult a licensed contractor or structural engineer.",
        "default": "⚠️ This guidance involves potential risks. Please consult a qualified professional before proceeding.",
    },
    RiskTier.MEDIUM: {
        "diy_repair": "ℹ️ Please follow safety precautions and use appropriate protective equipment.",
        "cooking": "ℹ️ Follow food safety guidelines and be aware of any allergies.",
        "children": "ℹ️ Adult supervision is recommended for safety.",
        "default": "ℹ️ Please proceed with care and follow safety guidelines.",
    },
}

REFERRAL_TEMPLATES = {
    "healthcare professional": "I recommend consulting a doctor or healthcare provider for proper guidance on this matter.",
    "licensed attorney": "I recommend speaking with a licensed attorney who can provide legal advice for your situation.",
    "financial advisor": "I recommend consulting a qualified financial advisor for personalized guidance.",
    "licensed electrician": "I recommend having a licensed electrician handle this for safety and code compliance.",
    "gas company or licensed plumber": "Please contact your gas company or a licensed professional immediately.",
    "structural engineer or contractor": "I recommend consulting a structural engineer or licensed contractor.",
    "qualified professional": "I recommend consulting a qualified professional for this type of work.",
}


def get_disclaimer(assessment: RiskAssessment) -> str | None:
    """Get appropriate disclaimer based on risk assessment."""
    if not assessment.requires_disclaimer:
        return None

    tier_disclaimers = DISCLAIMERS.get(assessment.tier, {})

    if assessment.category:
        return tier_disclaimers.get(assessment.category, tier_disclaimers.get("default"))

    return tier_disclaimers.get("default")


def get_referral_suggestion(assessment: RiskAssessment) -> str | None:
    """Get professional referral suggestion if needed."""
    if not assessment.requires_referral or not assessment.referral_type:
        return None

    return REFERRAL_TEMPLATES.get(
        assessment.referral_type,
        f"I recommend consulting a {assessment.referral_type}.",
    )


def inject_safety_content(
    content: str,
    assessment: RiskAssessment,
) -> str:
    """Inject disclaimer and referral into content if needed."""
    additions = []

    disclaimer = get_disclaimer(assessment)
    if disclaimer:
        additions.append(disclaimer)

    referral = get_referral_suggestion(assessment)
    if referral:
        additions.append(referral)

    if additions:
        safety_block = "\n\n".join(additions)
        return f"{content}\n\n---\n{safety_block}"

    return content
