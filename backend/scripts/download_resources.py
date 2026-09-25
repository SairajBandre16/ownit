"""Download local NLP resources: spaCy model and NLTK data.

Usage: python scripts/download_resources.py [--languagetool]

--languagetool also downloads the LanguageTool standalone server zip into
data/languagetool (for running without Docker; requires Java 17+).
"""

from __future__ import annotations

import argparse
import io
import subprocess
import sys
import zipfile
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SPACY_MODEL = "en_core_web_md"
NLTK_PACKAGES = ["wordnet", "omw-1.4", "punkt", "punkt_tab", "stopwords"]
LT_URL = "https://languagetool.org/download/LanguageTool-stable.zip"


def download_spacy() -> None:
    try:
        import spacy

        spacy.load(SPACY_MODEL)
        print(f"spaCy model {SPACY_MODEL} already installed")
    except OSError:
        subprocess.check_call([sys.executable, "-m", "spacy", "download", SPACY_MODEL])


def download_nltk() -> None:
    import nltk

    for pkg in NLTK_PACKAGES:
        nltk.download(pkg, quiet=True)
        print(f"nltk: {pkg} ok")


def download_languagetool() -> None:
    import httpx

    target = DATA_DIR / "languagetool"
    if any(target.glob("LanguageTool-*/languagetool-server.jar")):
        print("LanguageTool already downloaded")
        return
    target.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {LT_URL} ...")
    with httpx.Client(follow_redirects=True, timeout=600) as client:
        resp = client.get(LT_URL)
        resp.raise_for_status()
    zipfile.ZipFile(io.BytesIO(resp.content)).extractall(target)
    print(f"LanguageTool extracted to {target}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--languagetool", action="store_true")
    args = parser.parse_args()
    download_spacy()
    download_nltk()
    if args.languagetool:
        download_languagetool()


if __name__ == "__main__":
    main()
