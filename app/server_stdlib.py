import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from app.config import load_settings
from app.facebook import apply_moderation_action
from app.pipeline import run_moderation_pipeline


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

            events.append(
                {
                    "page_id": page_id,
                    "post_id": str(value.get("post_id", "")),
                    "comment_id": str(value.get("comment_id", "")),
                    "sender_id": sender_id,
                    "message": value.get("message"),
                    "verb": verb,
                }
            )
    return events


class WebhookHandler(BaseHTTPRequestHandler):
    def _send_json(self, status_code: int, data: dict[str, Any]) -> None:
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _send_text(self, status_code: int, text: str) -> None:
        raw = text.encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._send_json(200, {"status": "ok"})
            return

        if parsed.path == "/webhook/facebook":
            params = parse_qs(parsed.query)
            mode = (params.get("hub.mode") or [None])[0]
            token = (params.get("hub.verify_token") or [None])[0]
            challenge = (params.get("hub.challenge") or [None])[0]

            settings = load_settings()
            if mode == "subscribe" and challenge:
                if not settings.fb_verify_token or token == settings.fb_verify_token:
                    self._send_text(200, challenge)
                    return
            self._send_text(403, "Webhook verification failed")
            return

        self._send_json(404, {"error": "Not found"})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/webhook/facebook":
            self._send_json(404, {"error": "Not found"})
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        body_bytes = self.rfile.read(content_length) if content_length > 0 else b"{}"
        try:
            payload = json.loads(body_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_json(400, {"error": "Invalid JSON payload"})
            return

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

        self._send_json(200, {"received_comments": len(comment_events), "results": processed})

    def log_message(self, format: str, *args: Any) -> None:
        return


def run_server() -> None:
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    server = ThreadingHTTPServer((host, port), WebhookHandler)
    print(f"Server running on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    run_server()
