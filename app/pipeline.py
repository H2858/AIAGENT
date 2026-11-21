from dataclasses import dataclass
from app.agent import analyze_comment
from app.config import Settings, load_settings
from app.decide import decide_action
from app.guards import has_text, normalize_for_analysis
from app.schemas import AgentAssessment, ModerationDecision


@dataclass
class PipelineResult:
    skipped: bool
    original_text: str
    normalized_text: str
    assessment: AgentAssessment | None
    decision: ModerationDecision


def run_moderation_pipeline(
    comment_text: str | None,
    post_context: str | None = None,
    settings: Settings | None = None,
) -> PipelineResult:
    cfg = settings or load_settings()

    if not has_text(comment_text):
        return PipelineResult(
            skipped=True,
            original_text=comment_text or "",
            normalized_text="",
            assessment=None,
            decision=ModerationDecision(
                action="allow",
                needs_human_review=False,
                reason="تعليق فارغ أو بدون نص",
                normalized_preview="",
            ),
        )

    original = comment_text.strip()
    normalized, obfuscated = normalize_for_analysis(original)
    assessment = analyze_comment(
        original_text=original,
        normalized_text=normalized,
        obfuscation_from_guard=obfuscated,
        settings=cfg,
        post_context=post_context,
    )
    decision = decide_action(
        assessment=assessment,
        normalized_text=normalized,
        default_abusive_action=cfg.default_abusive_action,
    )

    return PipelineResult(
        skipped=False,
        original_text=original,
        normalized_text=normalized,
        assessment=assessment,
        decision=decision,
    )
