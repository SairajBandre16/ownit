"""Runtime configuration, read from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RESOURCES_DIR = Path(__file__).resolve().parent / "resources"
DATA_DIR = Path(os.environ.get("OWNIT_DATA_DIR", BASE_DIR / "data"))


def _env_list(name: str, default: str) -> list[str]:
    return [v.strip() for v in os.environ.get(name, default).split(",") if v.strip()]


@dataclass(frozen=True)
class Settings:
    spacy_model: str = os.environ.get("OWNIT_SPACY_MODEL", "en_core_web_md")
    languagetool_url: str = os.environ.get("OWNIT_LANGUAGETOOL_URL", "http://127.0.0.1:8010")
    languagetool_enabled: bool = os.environ.get("OWNIT_LANGUAGETOOL", "1") != "0"
    lm_dir: Path = DATA_DIR / "lm"
    max_words: int = int(os.environ.get("OWNIT_MAX_WORDS", "3000"))
    rate_limit: str = os.environ.get("OWNIT_RATE_LIMIT", "30/minute")
    cache_size: int = int(os.environ.get("OWNIT_CACHE_SIZE", "256"))
    cors_origins: list[str] = field(
        default_factory=lambda: _env_list(
            "OWNIT_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
        )
    )


settings = Settings()
