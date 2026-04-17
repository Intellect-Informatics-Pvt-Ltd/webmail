"""PSense Mail API — Configuration via Pydantic Settings.

Loads configuration from:
  1. config/default.yaml  (base defaults)
  2. config/{env}.yaml    (environment overlay, optional)
  3. Environment variables (PSENSE_MAIL__<SECTION>__<KEY>)

Environment variables use double-underscore nesting and take highest priority.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# ── Sub-models ───────────────────────────────────────────────────────────────

class AppConfig(BaseModel):
    name: str = "PSense Mail API"
    version: str = "0.1.0"
    debug: bool = False
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])


class AuthConfig(BaseModel):
    enabled: bool = False
    issuer: str = ""
    audience: str = ""
    jwks_uri: str = ""
    dev_user_id: str = "dev-user-001"
    dev_user_email: str = "avery@psense.ai"
    dev_user_name: str = "Avery Chen"


class MongoConfig(BaseModel):
    uri: str = "mongodb://localhost:27017"
    db_name: str = "psense_mail"
    min_pool_size: int = 5
    max_pool_size: int = 20


class MemoryDbConfig(BaseModel):
    seed_on_start: bool = True


class DatabaseConfig(BaseModel):
    backend: str = "memory"  # "mongo" | "memory"
    mongo: MongoConfig = Field(default_factory=MongoConfig)
    memory: MemoryDbConfig = Field(default_factory=MemoryDbConfig)


class MailpitConfig(BaseModel):
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    api_url: str = "http://localhost:8025"
    from_address: str = "noreply@psense.local"


class GmailConfig(BaseModel):
    credentials_file: str = ""
    token_file: str = ""
    scopes: list[str] = Field(default_factory=lambda: [
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/gmail.send",
    ])
    watch_topic: str = ""


class ProviderConfig(BaseModel):
    active: str = "memory"  # "mailpit" | "gmail" | "memory"
    mailpit: MailpitConfig = Field(default_factory=MailpitConfig)
    gmail: GmailConfig = Field(default_factory=GmailConfig)


class NASConfig(BaseModel):
    base_path: str = "./data/attachments"
    max_file_size_mb: int = 25
    allowed_extensions: list[str] = Field(default_factory=lambda: ["*"])


class S3Config(BaseModel):
    bucket: str = ""
    region: str = "us-east-1"
    access_key_id: str | None = None
    secret_access_key: str | None = None
    endpoint_url: str | None = None


class AzureBlobConfig(BaseModel):
    connection_string: str | None = None
    container_name: str = "psense-mail-attachments"


class GCSConfig(BaseModel):
    bucket: str = ""
    credentials_file: str | None = None


class FileStorageConfig(BaseModel):
    backend: str = "nas"  # "nas" | "s3" | "azure_blob" | "gcs"
    nas: NASConfig = Field(default_factory=NASConfig)
    s3: S3Config = Field(default_factory=S3Config)
    azure_blob: AzureBlobConfig = Field(default_factory=AzureBlobConfig)
    gcs: GCSConfig = Field(default_factory=GCSConfig)


class SearchConfig(BaseModel):
    backend: str = "mongo"  # "mongo" | "memory"


class WorkersConfig(BaseModel):
    enabled: bool = True
    snooze_check_interval_seconds: int = 60
    send_retry_max_attempts: int = 3
    sync_interval_seconds: int = 300
    scheduler_interval_seconds: int = 30
    retry_backoff_base_seconds: int = 60


class LoggingConfig(BaseModel):
    level: str = "INFO"
    format: str = "json"  # "json" | "console"
    correlation_header: str = "X-Correlation-ID"


# ── Root Settings ────────────────────────────────────────────────────────────

def _load_yaml_config() -> dict[str, Any]:
    """Load and merge YAML config files."""
    config_dir = Path(__file__).parent
    result: dict[str, Any] = {}

    # Base defaults
    default_path = config_dir / "default.yaml"
    if default_path.exists():
        with open(default_path) as f:
            base = yaml.safe_load(f) or {}
            result = _deep_merge(result, base)

    # Environment overlay (e.g., config/production.yaml)
    env = os.getenv("PSENSE_MAIL_ENV", "")
    if env:
        env_path = config_dir / f"{env}.yaml"
        if env_path.exists():
            with open(env_path) as f:
                overlay = yaml.safe_load(f) or {}
                result = _deep_merge(result, overlay)

    return result


def _deep_merge(base: dict, overlay: dict) -> dict:
    """Recursively merge overlay into base."""
    merged = base.copy()
    for key, value in overlay.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


class Settings(BaseSettings):
    """Root application settings.

    Priority (highest → lowest):
      1. Environment variables (PSENSE_MAIL__*)
      2. Environment-specific YAML (config/{env}.yaml)
      3. Default YAML (config/default.yaml)
      4. Pydantic defaults
    """

    model_config = SettingsConfigDict(
        env_prefix="PSENSE_MAIL__",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    app: AppConfig = Field(default_factory=AppConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    provider: ProviderConfig = Field(default_factory=ProviderConfig)
    file_storage: FileStorageConfig = Field(default_factory=FileStorageConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    workers: WorkersConfig = Field(default_factory=WorkersConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    @classmethod
    def load(cls) -> "Settings":
        """Load settings from YAML + environment variables."""
        yaml_data = _load_yaml_config()
        return cls(**yaml_data)


# Module-level singleton — import this.
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get or create the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings.load()
    return _settings
