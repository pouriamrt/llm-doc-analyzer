"""Typed runtime configuration and logging setup."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Literal

import structlog
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR"]

# Provider prefix -> (env var, settings attribute). Providers absent here manage their
# own credentials and are not pre-validated.
_PROVIDER_ENV = {
    "google": "GOOGLE_API_KEY",
    "gemini": "GOOGLE_API_KEY",
    "openai": "OPENAI_API_KEY",
}


class Settings(BaseSettings):
    """Configuration read from the environment, then `.env`, then these defaults."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    adk_model: str = "openai/gpt-5.6-terra"
    docs_dir: Path = Path("data")
    out_dir: Path = Path("data/outputs")
    max_concurrency: int = Field(default=3, ge=1, le=32)
    overwrite: bool = True
    user_id: str = "local_user"
    max_attempts: int = Field(default=5, ge=1, le=10)
    log_level: LogLevel = "INFO"

    google_api_key: SecretStr | None = None
    openai_api_key: SecretStr | None = None
    google_genai_use_vertexai: bool = False

    @property
    def provider(self) -> str:
        """LiteLLM provider prefix, or "google" for a bare Gemini model name."""
        return self.adk_model.split("/", 1)[0] if "/" in self.adk_model else "google"

    def require_credentials(self) -> None:
        """Fail before the first model call rather than after a document has run.

        Deliberately not a model validator: commands that never reach the model,
        such as `list-docs`, must work without any provider key configured.
        """
        env_var = _PROVIDER_ENV.get(self.provider)
        if env_var is None:
            return
        if self._secret_for(env_var) is None and not os.getenv(env_var):
            msg = f"ADK_MODEL={self.adk_model!r} requires {env_var}. Add it to .env."
            raise ValueError(msg)

    def _secret_for(self, env_var: str) -> SecretStr | None:
        return self.google_api_key if env_var == "GOOGLE_API_KEY" else self.openai_api_key

    def export_provider_credentials(self) -> None:
        """Copy credentials into the process environment.

        LiteLLM and google-genai read keys from `os.environ`, not from this object, so
        dropping `load_dotenv()` without this step breaks authentication.
        """
        for env_var, secret in (
            ("GOOGLE_API_KEY", self.google_api_key),
            ("OPENAI_API_KEY", self.openai_api_key),
        ):
            if secret is not None:
                # Assign, never setdefault: a stale value already in the environment
                # would silently outrank the key this Settings actually resolved.
                os.environ[env_var] = secret.get_secret_value()
        os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "1" if self.google_genai_use_vertexai else "0"


def configure_logging(level: LogLevel = "INFO") -> None:
    """Structured logs on stdout; tqdm owns stderr, so the two never interleave."""
    numeric = getattr(logging, level)
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=numeric)
    for noisy in ("LiteLLM", "litellm", "httpx", "google_genai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="%H:%M:%S"),
            structlog.dev.ConsoleRenderer(colors=sys.stdout.isatty()),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(numeric),
        # Defer to stdlib logging so the handler owns the stream. A PrintLogger would
        # capture sys.stdout once and keep writing to it after it is replaced or closed.
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
