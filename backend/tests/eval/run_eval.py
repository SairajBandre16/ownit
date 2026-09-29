"""Evaluation harness for the humanize engine (CLAUDE.md §11).

Runs every paragraph in tests/eval/paragraphs_*.txt through /humanize logic and reports:
  meaning_sim (avg), new grammar errors (must be 0), readability (FK grade) change,
  writing-score change, % sentences changed, runtime per 1,000 words.
Optionally (--voice) measures Voice Match before/after humanizing with a student profile.

Usage:
    python tests/eval/run_eval.py [--intensity 3] [--tone academic] [--voice] [--limit N]

Results are written as a markdown table to tests/eval/results/<timestamp>.md (+ latest.md)
so runs can be compared.
"""

from __future__ import annotations

import argparse
import statistics
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import textstat  # noqa: E402

from app.analyze.score import quick_score  # noqa: E402
from app.core.nlp import get_languagetool  # noqa: E402
from app.humanize.pipeline import humanize  # noqa: E402
from app.humanize.ranking import grammar  # noqa: E402
from app.humanize.ranking.meaning import meaning_sim, parse_many  # noqa: E402

EVAL_DIR = Path(__file__).parent
RESULTS = EVAL_DIR / "results"


@dataclass
class Row:
    category: str
    words: int
    meaning: float
    new_errors: int
    grade_before: float
    grade_after: float
    score_before: float
    score_after: float
    sentences: int
    changed: int
    seconds: float
    voice_before: float | None = None
    voice_after: float | None = None


EM_DASH_ESCAPE = chr(92) + "u2014"


def load_paragraphs(limit: int | None) -> list[tuple[str, str]]:
    out = []
    for path in sorted(EVAL_DIR.glob("paragraphs_*.txt")):
        cat = path.stem.removeprefix("paragraphs_")
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                # the repo has no literal em dashes (house style): fixtures write the escape
                out.append((cat, line.strip().replace(EM_DASH_ESCAPE, chr(0x2014))))
    return out[:limit] if limit else out


def student_profile():  # type: ignore[no-untyped-def]
    """Voice profile built from the student-style paragraphs (U1 evaluation)."""
    from app.style.fingerprint import fingerprint

    samples = [p for c, p in load_paragraphs(None) if c == "student"]
    return fingerprint(samples)


def run(intensity: int, tone: str, voice: bool, limit: int | None) -> list[Row]:
    paragraphs = load_paragraphs(limit)
    profile = student_profile() if voice else None
    profile_dict = profile.model_dump() if profile else None
    if voice:
        from app.style.delta import voice_match
    humanize("Warm up the engine with a short sentence.")
    rows: list[Row] = []
    for i, (cat, text) in enumerate(paragraphs, 1):
        t0 = time.perf_counter()
        out = humanize(text, tone=tone, intensity=intensity, profile=profile_dict)
        secs = time.perf_counter() - t0
        docs = parse_many([text, out.text])
        errs = grammar.check_many([text, out.text])
        row = Row(
            category=cat,
            words=len(text.split()),
            meaning=meaning_sim(docs[0], docs[1]),
            new_errors=grammar.new_errors(errs[0], errs[1]),
            grade_before=float(textstat.flesch_kincaid_grade(text)),
            grade_after=float(textstat.flesch_kincaid_grade(out.text)),
            score_before=quick_score(text),
            score_after=quick_score(out.text),
            sentences=out.stats["sentences"],
            changed=out.stats["sentences_changed"],
            seconds=secs,
        )
        if voice and profile is not None:
            row.voice_before = voice_match(text, profile)
            row.voice_after = voice_match(out.text, profile)
        rows.append(row)
        print(
            f"[{i}/{len(paragraphs)}] {cat:12s} meaning={row.meaning:.3f} "
            f"score {row.score_before:.1f}->{row.score_after:.1f} errors+{row.new_errors} "
            f"changed {row.changed}/{row.sentences} {secs:.2f}s",
            flush=True,
        )
    return rows


def summarize(rows: list[Row]) -> dict[str, dict[str, float]]:
    groups: dict[str, list[Row]] = {"all": rows}
    for r in rows:
        groups.setdefault(r.category, []).append(r)
    out: dict[str, dict[str, float]] = {}
    for name, rs in groups.items():
        words = sum(r.words for r in rs)
        s: dict[str, float] = {
            "paragraphs": len(rs),
            "meaning_sim": statistics.fmean(r.meaning for r in rs),
            "min_meaning_sim": min(r.meaning for r in rs),
            "new_grammar_errors": sum(r.new_errors for r in rs),
            "fk_grade_change": statistics.fmean(r.grade_after - r.grade_before for r in rs),
            "score_change": statistics.fmean(r.score_after - r.score_before for r in rs),
            "pct_sentences_changed": 100
            * sum(r.changed for r in rs)
            / max(1, sum(r.sentences for r in rs)),
            "sec_per_1000_words": 1000 * sum(r.seconds for r in rs) / max(1, words),
        }
        vb = [r.voice_before for r in rs if r.voice_before is not None]
        va = [r.voice_after for r in rs if r.voice_after is not None]
        if vb and va:
            s["voice_match_before"] = statistics.fmean(vb)
            s["voice_match_after"] = statistics.fmean(va)
            s["voice_match_improved_pct"] = (
                100 * sum(1 for r in rs if (r.voice_after or 0) > (r.voice_before or 0)) / len(rs)
            )
        out[name] = s
    return out


def to_markdown(
    summary: dict[str, dict[str, float]], args: argparse.Namespace, lt: bool, lm: str
) -> str:
    cols = list(dict.fromkeys(k for s in summary.values() for k in s))
    lines = [
        f"# Humanize evaluation: {datetime.now():%Y-%m-%d %H:%M}",
        "",
        f"intensity={args.intensity} · tone={args.tone} · LanguageTool={'on' if lt else 'OFF'} · LM={lm}",
        "",
        "| group | " + " | ".join(cols) + " |",
        "|---|" + "---|" * len(cols),
    ]
    for name, s in summary.items():
        vals = [
            f"{s[c]:.3f}" if isinstance(s[c], float) and c != "paragraphs" else f"{s[c]:g}"
            for c in cols
        ]
        lines.append(f"| {name} | " + " | ".join(vals) + " |")
    lines += [
        "",
        "Targets: new_grammar_errors = 0 · meaning_sim ≥ 0.80 per sentence (gate) · "
        "doc_sec_per_1000_words < 3 on the free CPU. sec_per_1000_words is per-paragraph "
        "requests (~70 words each), dominated by fixed per-request overhead.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--intensity", type=int, default=3)
    ap.add_argument("--tone", default="academic")
    ap.add_argument("--voice", action="store_true")
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()
    lt = get_languagetool().available()
    from app.core.nlp import get_lm

    rows = run(args.intensity, args.tone, args.voice, args.limit)
    summary = summarize(rows)
    # whole-document timing (how the API is used): one request per category
    by_cat: dict[str, list[str]] = {}
    for cat, text in load_paragraphs(args.limit):
        by_cat.setdefault(cat, []).append(text)
    total_words = total_secs = 0.0
    for cat, texts in by_cat.items():
        doc = "\n\n".join(texts)
        t0 = time.perf_counter()
        humanize(doc, tone=args.tone, intensity=args.intensity)
        secs = time.perf_counter() - t0
        words = len(doc.split())
        summary[cat]["doc_sec_per_1000_words"] = 1000 * secs / words
        total_words += words
        total_secs += secs
    summary["all"]["doc_sec_per_1000_words"] = 1000 * total_secs / max(total_words, 1)
    md = to_markdown(summary, args, lt, get_lm().name)
    RESULTS.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    suffix = f"-i{args.intensity}-{args.tone}" + ("-voice" if args.voice else "")
    (RESULTS / f"{stamp}{suffix}.md").write_text(md, encoding="utf-8")
    (RESULTS / "latest.md").write_text(md, encoding="utf-8")
    print()
    print(md)
    print("done")


if __name__ == "__main__":
    main()
