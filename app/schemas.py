from dataclasses import dataclass
from typing import Literal

CommentCategory = Literal[
    "severe_profanity",        # شتائم وألفاظ بذيئة صريحة أو مموهة بوضوح
    "targeted_harassment",     # إهانة مباشرة أو تنمر أو استفزاز هجومي
    "hostile_provocation",     # تشكيك عدائي أو كذب أو استفزاز متعمد حول التاريخ/الهوية
    "constructive_criticism",  # نقد بناء أو اعتراض منطقي بدون إساءة
    "positive_or_normal",      # تعليق إيجابي أو عادي أو استفسار بسيط
]

ModerationAction = Literal[
    "allow",   # إبقاء التعليق ظاهراً
    "review",  # تحويل إلى قائمة المراجعة البشرية (حالة رمادية)
    "hide",    # إخفاء التعليق عن الجمهور (أنسب غالباً في فيسبوك لتجنب التصعيد)
    "delete",  # حذف التعليق نهائياً
]


@dataclass
class AgentAssessment:
    category: CommentCategory
    confidence: float          # قيمة بين 0.0 و 1.0
    reason: str                # سبب مختصر للتصنيف
    obfuscation_detected: bool # هل استُخدم تمويه (نقاط، نجوم، أرقام، اختصارات)؟


@dataclass
class ModerationDecision:
    action: ModerationAction
    needs_human_review: bool
    reason: str
    normalized_preview: str
