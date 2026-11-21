import json
import urllib.error
import urllib.parse
import urllib.request

GRAPH_API_VERSION = "v21.0"
GRAPH_BASE_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


def hide_comment(comment_id: str, page_access_token: str) -> tuple[bool, str]:
    if not comment_id:
        return False, "Missing comment_id"
    if not page_access_token:
        return False, "Missing FB_PAGE_ACCESS_TOKEN (skipped live Graph API call)"

    url = f"{GRAPH_BASE_URL}/{urllib.parse.quote(comment_id)}"
    payload = urllib.parse.urlencode({"is_hidden": "true", "access_token": page_access_token}).encode("utf-8")
    req = urllib.request.Request(url=url, data=payload, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8")
            return True, f"Comment hidden: {body}"
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")
        return False, f"Graph API HTTP {exc.code} on hide: {err_body}"
    except (urllib.error.URLError, TimeoutError) as exc:
        return False, f"Network error on hide: {type(exc).__name__}"


def delete_comment(comment_id: str, page_access_token: str) -> tuple[bool, str]:
    if not comment_id:
        return False, "Missing comment_id"
    if not page_access_token:
        return False, "Missing FB_PAGE_ACCESS_TOKEN (skipped live Graph API call)"

    query = urllib.parse.urlencode({"access_token": page_access_token})
    url = f"{GRAPH_BASE_URL}/{urllib.parse.quote(comment_id)}?{query}"
    req = urllib.request.Request(url=url, method="DELETE")

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8")
            return True, f"Comment deleted: {body}"
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")
        return False, f"Graph API HTTP {exc.code} on delete: {err_body}"
    except (urllib.error.URLError, TimeoutError) as exc:
        return False, f"Network error on delete: {type(exc).__name__}"


def apply_moderation_action(
    action: str,
    comment_id: str,
    page_access_token: str,
) -> tuple[bool, str]:
    if action == "hide":
        return hide_comment(comment_id, page_access_token)
    if action == "delete":
        return delete_comment(comment_id, page_access_token)
    if action == "review":
        return True, f"Queued for human review (comment_id={comment_id})"
    return True, f"Allowed comment (comment_id={comment_id})"
