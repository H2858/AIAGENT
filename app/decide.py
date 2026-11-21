from app.schemas import AgentAssessment, ModerationDecision


def decide_action(
    assessment: AgentAssessment,
    normalized_text: str,
    default_abusive_action: str = "hide",
) -> ModerationDecision:
    conf = max(0.0, min(1.0, assessment.confidence))
    cat = assessment.category

    if cat == "severe_profanity" and conf >= 0.75:
        action = "delete" if default_abusive_action == "delete" else "hide"
        return ModerationDecision(
            action=action,
            needs_human_review=False,
            reason=f"Clear profanity (conf={conf:.2f}): {assessment.reason}",
            normalized_preview=normalized_text,
        )

    if cat == "targeted_harassment" and conf >= 0.85:
        action = "hide" if default_abusive_action != "delete" else "delete"
        return ModerationDecision(
            action=action,
            needs_human_review=True,
            reason=f"High-confidence harassment (conf={conf:.2f}): {assessment.reason}",
            normalized_preview=normalized_text,
        )

    if cat in ("hostile_provocation", "targeted_harassment", "severe_profanity"):
        return ModerationDecision(
            action="review",
            needs_human_review=True,
            reason=f"Needs human review (conf={conf:.2f}): {assessment.reason}",
            normalized_preview=normalized_text,
        )

    return ModerationDecision(
        action="allow",
        needs_human_review=False,
        reason=f"Allowed ({cat}): {assessment.reason}",
        normalized_preview=normalized_text,
    )
