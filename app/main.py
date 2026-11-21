from typing import Any
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from app.config import load_settings
from app.facebook import apply_moderation_action
from app.pipeline import run_moderation_pipeline

app = FastAPI(title="FB Comment Guard Webhook")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/webhook/facebook", response_class=PlainTextResponse)
def verify_webhook(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
) -> str:
    settings = load_settings()
    if hub_mode == "subscribe" and hub_challenge:
        if settings.fb_verify_token and hub_verify_token == settings.fb_verify_token:
            return hub_challenge
        if not settings.fb_verify_token:
            return hub_challenge
    raise HTTPException(status_code=403, detail="Webhook verification failed")


def _extract_comment_events(payload: dict[str, Any]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for entry in payload.get("entry", []):
        page_id = str(entry.get("id", ""))
        for change in entry.get("changes", []):
            if change.get("field") != "feed":
                continue
            value = change.get("value", {})
            if value.get("item") != "comment":
                continue
            verb = value.get("verb", "")
            if verb not in ("add", "edited"):
                continue

            from_data = value.get("from") or {}
            sender_id = str(from_data.get("id", ""))
            if page_id and sender_id and page_id == sender_id:
                continue

            comment_id = str(value.get("comment_id", ""))
            message = value.get("message")
            post_id = str(value.get("post_id", ""))
            events.append(
                {
                    "page_id": page_id,
                    "post_id": post_id,
                    "comment_id": comment_id,
                    "sender_id": sender_id,
                    "message": message,
                    "verb": verb,
                }
            )
    return events


@app.post("/webhook/facebook")
async def receive_webhook(request: Request) -> dict[str, Any]:
    payload = await request.json()
    settings = load_settings()
    comment_events = _extract_comment_events(payload)

    processed: list[dict[str, Any]] = []
    for ev in comment_events:
        result = run_moderation_pipeline(
            comment_text=ev["message"],
            post_context=f"post_id={ev['post_id']}",
            settings=settings,
        )
        action = result.decision.action
        ok, exec_detail = apply_moderation_action(
            action=action,
            comment_id=ev["comment_id"],
            page_access_token=settings.fb_page_access_token,
        )
        processed.append(
            {
                "comment_id": ev["comment_id"],
                "action": action,
                "needs_human_review": result.decision.needs_human_review,
                "category": result.assessment.category if result.assessment else None,
                "confidence": result.assessment.confidence if result.assessment else None,
                "executed": ok,
                "detail": exec_detail,
            }
        )

    return {"received_comments": len(comment_events), "results": processed}
