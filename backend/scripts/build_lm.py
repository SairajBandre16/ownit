"""Build the fluency language model from WikiText-103 (raw text dataset - data, not a model API).

Steps:
1. Download the WikiText-103 raw train split (parquet shards) into data/corpora/.
2. Normalise it into one tokenised sentence per line (data/corpora/wiki.txt).
3. If KenLM's `lmplz` and `build_binary` are on PATH (Docker image), build a 5-gram
   binary at data/lm/wiki5.binary.
4. Always build the pure-numpy trigram fallback at data/lm/trigram.npz.

Usage:
    python scripts/build_lm.py [--max-tokens 40000000] [--vocab 100000] [--skip-kenlm]

Requires `pyarrow` (see requirements-build.txt).
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.humanize.ranking.fluency import BOS, EOS, UNK, TrigramScorer, tokenize  # noqa: E402

DATA = ROOT / "data"
CORPORA = DATA / "corpora"
LM_DIR = DATA / "lm"
HF_BASE = "https://huggingface.co/datasets/Salesforce/wikitext/resolve/main/wikitext-103-raw-v1"
SHARDS = ["train-00000-of-00002.parquet", "train-00001-of-00002.parquet"]

HEADING_RE = re.compile(r"^\s*=+ .* =+\s*$")
SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"(])")
CLITIC_RE = re.compile(r" (['’](?:s|re|ve|ll|d|m)|n't)\b")


def download() -> list[Path]:
    import httpx

    CORPORA.mkdir(parents=True, exist_ok=True)
    paths = []
    for shard in SHARDS:
        path = CORPORA / shard
        if not path.exists():
            print(f"downloading {shard} ...", flush=True)
            tmp = path.with_suffix(".part")
            with httpx.stream("GET", f"{HF_BASE}/{shard}", follow_redirects=True, timeout=600) as r:
                r.raise_for_status()
                with tmp.open("wb") as fh:
                    for chunk in r.iter_bytes(1 << 20):
                        fh.write(chunk)
            tmp.rename(path)
        paths.append(path)
    return paths


def clean_line(line: str) -> str:
    line = line.replace(" @-@ ", "-").replace(" @,@ ", ",").replace(" @.@ ", ".")
    line = CLITIC_RE.sub(r"\1", line)
    return line.strip()


def build_corpus(shards: list[Path], max_tokens: int) -> Path:
    import pyarrow.parquet as pq

    out = CORPORA / "wiki.txt"
    if out.exists():
        print(f"corpus exists: {out}")
        return out
    n_tokens = 0
    with out.open("w", encoding="utf-8") as fh:
        for shard in shards:
            pf = pq.ParquetFile(shard)
            for batch in pf.iter_batches(columns=["text"], batch_size=20000):
                for raw in batch.column(0).to_pylist():
                    if not raw or not raw.strip() or HEADING_RE.match(raw):
                        continue
                    for sent in SENT_SPLIT_RE.split(clean_line(raw)):
                        toks = tokenize(sent)
                        if len(toks) < 4:
                            continue
                        fh.write(" ".join(toks) + "\n")
                        n_tokens += len(toks)
                if n_tokens >= max_tokens:
                    print(f"corpus: {n_tokens:,} tokens -> {out}")
                    return out
    print(f"corpus: {n_tokens:,} tokens -> {out}")
    return out


def build_kenlm(corpus: Path) -> bool:
    lmplz, build_binary = shutil.which("lmplz"), shutil.which("build_binary")
    if not (lmplz and build_binary):
        print("KenLM binaries not found - skipping 5-gram build")
        return False
    LM_DIR.mkdir(parents=True, exist_ok=True)
    arpa = LM_DIR / "wiki5.arpa"
    with corpus.open("rb") as src, arpa.open("wb") as dst:
        subprocess.check_call(
            [lmplz, "-o", "5", "-S", "40%", "--prune", "0", "0", "1"], stdin=src, stdout=dst
        )
    subprocess.check_call([build_binary, str(arpa), str(LM_DIR / "wiki5.binary")])
    arpa.unlink()
    return True


def _merge(parts: list[tuple[np.ndarray, np.ndarray]]) -> tuple[np.ndarray, np.ndarray]:
    keys = np.concatenate([p[0] for p in parts])
    counts = np.concatenate([p[1] for p in parts])
    order = np.argsort(keys, kind="stable")
    keys, counts = keys[order], counts[order]
    uniq, starts = np.unique(keys, return_index=True)
    return uniq, np.add.reduceat(counts, starts)


def build_trigram(corpus: Path, vocab_size: int, min_count: int = 2) -> None:
    print("counting unigrams ...", flush=True)
    uni_counter: Counter[str] = Counter()
    with corpus.open(encoding="utf-8") as fh:
        for line in fh:
            uni_counter.update(line.split())
    specials = [UNK, BOS, EOS]
    vocab = specials + [w for w, _ in uni_counter.most_common(vocab_size)]
    index = {w: i for i, w in enumerate(vocab)}
    n = len(vocab)
    bos, eos, unk = index[BOS], index[EOS], index[UNK]

    uni = np.zeros(n, dtype=np.int64)
    bi_parts: list[tuple[np.ndarray, np.ndarray]] = []
    tri_parts: list[tuple[np.ndarray, np.ndarray]] = []
    buf: list[int] = []

    def flush() -> None:
        if not buf:
            return
        ids = np.array(buf, dtype=np.int64)
        np.add.at(uni, ids[ids != bos], 1)
        a, b, c = ids[:-2], ids[1:-1], ids[2:]
        # never count n-grams that cross a sentence boundary (EOS followed by BOS)
        tri_ok = (b != eos) & (a != eos)
        bi_ok = ids[:-1] != eos
        bk, bc = np.unique(ids[:-1][bi_ok] * n + ids[1:][bi_ok], return_counts=True)
        tk, tc = np.unique((a[tri_ok] * n + b[tri_ok]) * n + c[tri_ok], return_counts=True)
        bi_parts.append((bk, bc.astype(np.int64)))
        tri_parts.append((tk, tc.astype(np.int64)))
        buf.clear()

    print("counting n-grams ...", flush=True)
    with corpus.open(encoding="utf-8") as fh:
        for line in fh:
            buf.extend([bos, bos, *(index.get(t, unk) for t in line.split()), eos])
            if len(buf) > 5_000_000:
                flush()
                if len(tri_parts) >= 4:
                    tri_parts[:] = [_merge(tri_parts)]
                    bi_parts[:] = [_merge(bi_parts)]
    flush()
    bi_keys, bi_counts = _merge(bi_parts)
    tri_keys, tri_counts = _merge(tri_parts)
    keep = tri_counts >= min_count
    tri_keys, tri_counts = tri_keys[keep], tri_counts[keep]
    print(f"vocab={n:,} bigrams={len(bi_keys):,} trigrams(>={min_count})={len(tri_keys):,}")
    LM_DIR.mkdir(parents=True, exist_ok=True)
    out = LM_DIR / "trigram.npz"
    TrigramScorer.save(out, vocab, uni, (bi_keys, bi_counts), (tri_keys, tri_counts))
    print(f"fallback LM -> {out} ({out.stat().st_size / 1e6:.1f} MB)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-tokens", type=int, default=40_000_000)
    ap.add_argument("--vocab", type=int, default=100_000)
    ap.add_argument("--skip-kenlm", action="store_true")
    args = ap.parse_args()
    corpus = build_corpus(download(), args.max_tokens)
    if not args.skip_kenlm:
        build_kenlm(corpus)
    build_trigram(corpus, args.vocab)


if __name__ == "__main__":
    main()
