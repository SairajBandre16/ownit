"""Minimal HTTP client for a self-hosted LanguageTool server."""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass

import httpx
from cachetools import LRUCache

from app.config import settings

log = logging.getLogger(__name__)

# Rules that fire on legitimate engineering prose and on our own rewrites
# without indicating a real error.
DISABLED_RULES = [
    "WHITESPACE_RULE",
    "EN_QUOTES",
    "DASH_RULE",
    "PUNCTUATION_PARAGRAPH_END",
    "UPPERCASE_SENTENCE_START",
    "COMMA_PARENTHESIS_WHITESPACE",
    "ENGLISH_WORD_REPEAT_BEGINNING_RULE",
]


@dataclass(frozen=True)
class LTMatch:
    start: int
    end: int
    rule_id: str
    category: str
    message: str
    replacements: tuple[str, ...]
    issue_type: str


class LanguageToolClient:
    def __init__(self, base_url: str, enabled: bool = True) -> None:
        self.base_url = base_url.rstrip("/")
        self.enabled = enabled
        self._cache: LRUCache[str, list[LTMatch]] = LRUCache(maxsize=4096)
        self._available: bool | None = None
        self._checked_at = 0.0
        self._client = httpx.Client(timeout=20)

    def available(self) -> bool:
        if not self.enabled:
            return False
        now = time.monotonic()
        if self._available is not None and now - self._checked_at < 30:
            return self._available
        try:
            r = self._client.get(f"{self.base_url}/v2/languages", timeout=2)
            self._available = r.status_code == 200
        except httpx.HTTPError:
            self._available = False
        self._checked_at = now
        return self._available

    def check(self, text: str) -> list[LTMatch]:
        """Return grammar matches. Empty list if the server is unreachable."""
        if not text.strip() or not self.available():
            return []
        key = hashlib.sha256(text.encode()).hexdigest()
        if key in self._cache:
            return self._cache[key]
        try:
            r = self._client.post(
                f"{self.base_url}/v2/check",
                data={
                    "text": text,
                    "language": "en-US",
                    "disabledRules": ",".join(DISABLED_RULES),
                },
            )
            r.raise_for_status()
            payload = r.json()
        except (httpx.HTTPError, ValueError) as exc:
            log.warning("LanguageTool check failed: %s", exc)
            self._available = False
            return []
        matches = [
            LTMatch(
                start=m["offset"],
                end=m["offset"] + m["length"],
                rule_id=m["rule"]["id"],
                category=m["rule"]["category"]["id"],
                message=m["message"],
                replacements=tuple(r["value"] for r in m.get("replacements", [])[:3]),
                issue_type=m["rule"].get("issueType", "misc"),
            )
            for m in payload.get("matches", [])
        ]
        self._cache[key] = matches
        return matches


_client: LanguageToolClient | None = None


def get_languagetool() -> LanguageToolClient:
    global _client
    if _client is None:
        _client = LanguageToolClient(settings.languagetool_url, settings.languagetool_enabled)
    return _client
