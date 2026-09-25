from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.nlp import get_languagetool, get_lm


@pytest.fixture(scope="session")
def client() -> TestClient:
    from app.main import app

    with TestClient(app) as c:
        yield c  # type: ignore[misc]


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    lt_ok = get_languagetool().available()
    lm_ok = get_lm().ready
    skip_lt = pytest.mark.skip(reason="LanguageTool server not reachable")
    skip_lm = pytest.mark.skip(reason="fluency LM not built (scripts/build_lm.py)")
    for item in items:
        if "languagetool" in item.keywords and not lt_ok:
            item.add_marker(skip_lt)
        if "lm" in item.keywords and not lm_ok:
            item.add_marker(skip_lm)
