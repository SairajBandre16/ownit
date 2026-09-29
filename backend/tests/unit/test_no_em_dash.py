"""House style: no em dashes anywhere in the repo (copy, code, comments, docs).

Code that has to recognise an em dash in user input writes it as the escape \\u2014.
"""

from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
EM_DASH = chr(0x2014)
SKIP_DIRS = {
    "node_modules",
    ".venv",
    ".next",
    ".git",
    "data",
    "test-results",
    "__pycache__",
    ".mypy_cache",
}
# written and re-added by `next dev`, so edits to it do not stick
SKIP_FILES = {REPO / "frontend" / "AGENTS.md"}
TEXT_SUFFIXES = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".mjs",
    ".css",
    ".md",
    ".json",
    ".yml",
    ".yaml",
    ".toml",
    ".txt",
    ".html",
}


def test_no_em_dashes_in_repo() -> None:
    offenders = []
    for path in REPO.rglob("*"):
        if SKIP_DIRS & set(path.relative_to(REPO).parts) or path in SKIP_FILES:
            continue
        if path.suffix not in TEXT_SUFFIXES or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for n, line in enumerate(text.splitlines(), 1):
            if EM_DASH in line:
                offenders.append(f"{path.relative_to(REPO)}:{n}")
    assert not offenders, (
        "Em dashes found (use a comma, colon, full stop or brackets):\n" + "\n".join(offenders)
    )
