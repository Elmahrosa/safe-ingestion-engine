"""
core/config.py — Application configuration

Loads environment variables from `.env` and provides a typed settings object
used across the Safe Ingestion Engine.

Security goals:
• No hard-coded secrets
• Safe defaults
• Environment override support
• Production container compatibility
"""

from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List


class Settings(BaseSettings):

    # ── Core System ─────────────────────────────────────────────
    redis_url: str = "redis://redis:6379/0"
    data_dir: str = "data"

    # ── Billing / Google Apps Script ────────────────────────────
    sheet_webhook_url: str = ""
    sheet_api_secret: str = ""

    # ── Security ────────────────────────────────────────────────
    pii_salt: str = ""
    dashboard_admin_password: str = ""

    # ── API Configuration ───────────────────────────────────────
    cors_origins: str = "https://safe.teosegypt.com"
    user_agent: str = "SafeIngestion/1.0"
    require_payment: bool = False

    # ── Runtime Mode ────────────────────────────────────────────
    teos_mode: str = "production"

    # ── Security Hardening ──────────────────────────────────────
    allow_redirects: bool = False

    # ── Logging ─────────────────────────────────────────────────
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False

    # ── Helper methods ──────────────────────────────────────────

    def get_cors_list(self) -> List[str]:
        """
        Convert comma-separated CORS origins to list.
        """
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


# Singleton settings instance
@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
