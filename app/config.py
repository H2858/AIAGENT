import os
from dataclasses import dataclass


@dataclass
class Settings:
    openrouter_api_key: str
    openrouter_model: str
    default_abusive_action: str
    fb_page_access_token: str
    fb_verify_token: str


def load_settings() -> Settings:
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    model = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini").strip()
    abusive_action = os.getenv("DEFAULT_ABUSIVE_ACTION", "hide").strip().lower()
    if abusive_action not in ("hide", "delete"):
        abusive_action = "hide"

    return Settings(
        openrouter_api_key=api_key,
        openrouter_model=model,
        default_abusive_action=abusive_action,
        fb_page_access_token=os.getenv("FB_PAGE_ACCESS_TOKEN", "").strip(),
        fb_verify_token=os.getenv("FB_VERIFY_TOKEN", "").strip(),
    )
