from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _read_secret(name: str) -> str:
    """Read a Docker secret from /run/secrets/<name>."""
    path = Path(f"/run/secrets/{name}")
    if path.exists():
        return path.read_text().strip()
    return ""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    environment: str = "development"
    log_level: str = "info"
    secret_key: str = "dev-secret-change-me"

    # OpenAI
    openai_model_default: str = "gpt-5.4-nano"
    openai_model_complex: str = "gpt-5.4-mini"

    # Postgres
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "quark"

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_ttl_seconds: int = 86400

    # MQTT
    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    mqtt_client_id: str = "quark-api"

    # Discord
    discord_channel_id: str = ""
    discord_reminder_channel_id: str = ""  # 알림 전용 채널 (미설정 시 DM으로 발송)

    # GitHub
    github_username: str = ""

    # Weather (Open-Meteo, Seoul default)
    weather_lat: float = 37.5665
    weather_lon: float = 126.9780

    # Host helper (reboot / Wake-on-LAN — runs outside Docker on the host)
    host_helper_url: str = "http://172.19.0.1:8999"
    laptop_mac: str = ""

    # ── Secrets (Docker Secrets or env fallback) ────────────────────────────
    @computed_field  # type: ignore[prop-decorator]
    @property
    def openai_api_key(self) -> str:
        # Prefer a Docker secret; fall back to OPENAI_API_KEY from .env / environment.
        return _read_secret("openai_api_key") or os.environ.get("OPENAI_API_KEY", "")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def postgres_user(self) -> str:
        return _read_secret("postgres_user") or "quark"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def postgres_password(self) -> str:
        return _read_secret("postgres_password") or "quark"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def redis_password(self) -> str:
        return _read_secret("redis_password") or ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def mqtt_user(self) -> str:
        return _read_secret("mqtt_user") or "quark"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def mqtt_password(self) -> str:
        return _read_secret("mosquitto_password") or ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def discord_token(self) -> str:
        return _read_secret("discord_token") or ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def host_helper_token(self) -> str:
        return _read_secret("host_helper_token") or ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def siri_api_key(self) -> str:
        return _read_secret("siri_api_key") or os.environ.get("SIRI_API_KEY", "")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def google_oauth_client_id(self) -> str:
        return _read_secret("google_oauth_client_id") or ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def google_oauth_client_secret(self) -> str:
        return _read_secret("google_oauth_client_secret") or ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def google_calendar_refresh_token(self) -> str:
        return _read_secret("google_calendar_refresh_token") or ""

    # ── Derived DSNs ────────────────────────────────────────────────────────
    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url(self) -> str:
        u = self.postgres_user
        p = self.postgres_password
        h = self.postgres_host
        port = self.postgres_port
        db = self.postgres_db
        return f"postgresql+asyncpg://{u}:{p}@{h}:{port}/{db}"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def redis_url(self) -> str:
        pw = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{pw}{self.redis_host}:{self.redis_port}/0"


@lru_cache
def get_settings() -> Settings:
    return Settings()
