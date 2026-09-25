"""Build reference statistics for Burrows' Delta (U1 Voice Fingerprint).

Reads the normalised WikiText corpus (data/corpora/wiki.txt, built by build_lm.py), splits it
into 1,000-word chunks and records the mean and standard deviation of each function word's
frequency per 1,000 words. Output: app/resources/function_words.json (committed).

Usage: python scripts/build_style_reference.py [--chunks 3000]
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "data" / "corpora" / "wiki.txt"
OUT = ROOT / "app" / "resources" / "function_words.json"

# 60 frequent English function words (Burrows-style)
FUNCTION_WORDS = [
    "the",
    "of",
    "and",
    "to",
    "a",
    "in",
    "that",
    "is",
    "was",
    "it",
    "for",
    "on",
    "with",
    "as",
    "be",
    "by",
    "this",
    "are",
    "at",
    "from",
    "or",
    "an",
    "which",
    "have",
    "not",
    "but",
    "has",
    "were",
    "had",
    "they",
    "their",
    "can",
    "we",
    "i",
    "you",
    "there",
    "been",
    "would",
    "will",
    "all",
    "one",
    "more",
    "so",
    "if",
    "its",
    "also",
    "these",
    "than",
    "into",
    "other",
    "some",
    "only",
    "when",
    "what",
    "such",
    "may",
    "our",
    "my",
    "then",
    "because",
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunks", type=int, default=3000)
    args = ap.parse_args()
    freqs: dict[str, list[float]] = {w: [] for w in FUNCTION_WORDS}
    buf: list[str] = []
    n_chunks = 0
    with CORPUS.open(encoding="utf-8") as fh:
        for line in fh:
            buf.extend(t for t in line.split() if t[0].isalpha())
            while len(buf) >= 1000:
                chunk, buf = buf[:1000], buf[1000:]
                c = Counter(chunk)
                for w in FUNCTION_WORDS:
                    freqs[w].append(c[w])
                n_chunks += 1
                if n_chunks >= args.chunks:
                    break
            if n_chunks >= args.chunks:
                break
    out = {
        "_note": f"Per-1,000-word frequencies over {n_chunks} WikiText-103 chunks (Burrows Delta).",
        "words": FUNCTION_WORDS,
        "mean": {w: round(statistics.fmean(v), 4) for w, v in freqs.items()},
        "sd": {w: round(max(statistics.pstdev(v), 0.5), 4) for w, v in freqs.items()},
    }
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"wrote {OUT} from {n_chunks} chunks")


if __name__ == "__main__":
    main()
