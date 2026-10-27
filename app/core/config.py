"""Runtime settings read from environment variables (12-factor style).

Settings come only from the environment (optionally a local .env file) so the
same container image can be promoted from dev to staging to prod unchanged:
only the env file differs between environments, never the build.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["dev", "staging", "prod"] = "dev"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    data_dir: Path = Path("data")
    git_sha: str = "unknown"


@lru_cache
def get_settings() -> Settings:
    # Cached so every request sees one consistent configuration; tests that
    # need different values build their own Settings instead of mutating this.
    return Settings()
