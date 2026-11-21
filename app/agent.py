import json
import re
import urllib.error
import urllib.request
from app.config import Settings
from app.schemas import AgentAssessment, CommentCategory

VALID_CATEGORIES: set[str] = {
    "severe_profanity",
    "targeted_harassment",
    "hostile_provocation",
    "constructive_criticism",
    "positive_or_normal",
}

SYSTEM_PROMPT = """You are a strict, accurate comment moderation classifier for Algerian public Facebook pages.
Your job is to classify comments (which may be in Maghrebi dialect, Arabic, French, English, leetspeak, or obfuscated text).

Categories:
- "severe_profanity": Explicit or clearly obfuscated sexual/vulgar insults, slurs, or profane phrases in Arabic/Maghrebi/Latin script (e.g., variations of "نيك مك", "نياك يماك", "9a7ba", "9ahba", "w9", dot/star-separated profanity).
- "targeted_harassment": Direct insults, name-calling, or personal attacks aimed at a person/group without explicit vulgar profanity.
- "hostile_provocation": Deliberate provocation, mockery, false accusations, or hostile baiting targeting Algeria, its history, culture, or people.
- "constructive_criticism": Honest feedback, disagreement, or criticism expressed without abuse or hostility.
- "positive_or_normal": Positive comments, greetings, normal questions, or neutral remarks.

Important rules:
1. Understand Maghrebi dialect variations and obfuscation (dots, stars, repeated letters, numbers like 9=ق, 7=ح, 3=ع, abbreviations like w9).
2. Do not confuse honest criticism or disagreement with severe_profanity.
3. Return ONLY valid JSON with keys: "category", "confidence" (float 0.0 to 1.0), and "reason" (short reason in Arabic).

Examples:
- Comment: "ن.يك يماك" | Normalized: "نيك يماك" -> {"category": "severe_profanity", "confidence": 0.98, "reason": "شتيمة صريحة مموهة بالنقاط بالدارجة"}
- Comment: "w9 9a7ba" | Normalized: "w9 قحba" -> {"category": "severe_profanity", "confidence": 0.97, "reason": "استخدام اختصار وألفاظ بذيئة مموهة"}
- Comment: "المعلومة التاريخية فيها نقص وتحتاج توضيح أكثر" -> {"category": "constructive_criticism", "confidence": 0.92, "reason": "نقد وملاحظة مهذبة حول المحتوى"}
- Comment: "الله يبارك في تاريخ الجزائر" -> {"category": "positive_or_normal", "confidence": 0.96, "reason": "تعليق إيجابي عادي"}
"""


def _extract_json_block(raw_text: str) -> dict:
    text = raw_text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    else:
        brace_match = re.search(r"\{.*\}", text, re.DOTALL)
        if brace_match:
            text = brace_match.group(0)
    return json.loads(text)


def analyze_comment(
    original_text: str,
    normalized_text: str,
    obfuscation_from_guard: bool,
    settings: Settings,
    post_context: str | None = None,
) -> AgentAssessment:
    if not settings.openrouter_api_key:
        return AgentAssessment(
            category="hostile_provocation" if obfuscation_from_guard else "positive_or_normal",
            confidence=0.2,
            reason="مفتاح OPENROUTER_API_KEY غير مضبوط بعد؛ تم التحويل للمراجعة الآمنة",
            obfuscation_detected=obfuscation_from_guard,
        )

    user_payload = {
        "original_comment": original_text,
        "normalized_comment": normalized_text,
        "post_context": post_context or "",
    }

    body = {
        "model": settings.openrouter_model,
        "temperature": 0.1,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ],
    }

    req = urllib.request.Request(
        url="https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        content = data["choices"][0]["message"]["content"]
        parsed = _extract_json_block(content)

        raw_cat = str(parsed.get("category", "hostile_provocation")).strip()
        category: CommentCategory = (
            raw_cat if raw_cat in VALID_CATEGORIES else "hostile_provocation"  # type: ignore[assignment]
        )
        confidence = float(parsed.get("confidence", 0.5))
        confidence = max(0.0, min(1.0, confidence))
        reason = str(parsed.get("reason", "تم التحليل")).strip()

        return AgentAssessment(
            category=category,
            confidence=confidence,
            reason=reason,
            obfuscation_detected=obfuscation_from_guard,
        )
    except (urllib.error.URLError, TimeoutError, KeyError, ValueError, json.JSONDecodeError) as exc:
        return AgentAssessment(
            category="hostile_provocation",
            confidence=0.3,
            reason=f"تعذر إتمام التحليل الآلي ({type(exc).__name__})؛ يُحوّل للمراجعة",
            obfuscation_detected=obfuscation_from_guard,
        )
