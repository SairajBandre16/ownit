"""Concept map: key concepts as nodes, relations between them as edges.

Nodes: document keyphrases merged by lemma, sized by PageRank centrality, each listing the
paragraphs it appears in (so the UI can zoom to the paragraph being read).
Edges: concepts appearing in the same sentence; labelled with the connecting verb when the
dependency parse links them as subject → verb → object ("sensor —measures→ temperature").
Positions come from a seeded spring layout (deterministic), scaled to [0, 1].
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field

import networkx as nx

from app.core.graph import pagerank
from app.core.segment import Segmentation
from app.core.terms import noun_keyphrases
from app.walkthrough.glossary import abbreviation_pairs

MAX_NODES = 18
LIGHT_VERBS = {"be", "have", "do", "make", "play", "take", "give", "get"}  # "plays a role"


@dataclass
class Node:
    id: str
    label: str
    weight: float
    paragraphs: list[int]
    x: float = 0.0
    y: float = 0.0


@dataclass
class EdgeOut:
    source: str
    target: str
    label: str | None
    weight: float


@dataclass
class ConceptMap:
    nodes: list[Node] = field(default_factory=list)
    edges: list[EdgeOut] = field(default_factory=list)


def _key(phrase: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", phrase.lower()).strip()


def build(seg: Segmentation, body_paragraphs: list[int]) -> ConceptMap:
    phrases = [p for p, _, _ in noun_keyphrases(seg, top=30)]
    # "programmable logic controller (PLC)": one concept, labelled by the abbreviation
    full_to_abbr = {full.lower(): abbr for abbr, full in abbreviation_pairs(seg).items()}
    concepts: dict[str, str] = {}
    aliases: dict[str, list[str]] = defaultdict(list)
    for p in phrases:
        abbr = full_to_abbr.get(p.lower())
        if abbr:
            aliases[_key(abbr)].append(p)
            p = abbr
        k = _key(p)
        if k and not any(k in other or other in k for other in concepts if k != other):
            concepts.setdefault(k, p)
    if not concepts:
        return ConceptMap()
    patterns = {
        k: re.compile(
            "|".join(rf"(?<![\w-]){re.escape(form)}s?(?![\w-])" for form in [label, *aliases[k]]),
            re.IGNORECASE,
        )
        for k, label in concepts.items()
    }

    occurrences: dict[str, set[int]] = defaultdict(set)
    counts: Counter[str] = Counter()
    pair_weight: Counter[tuple[str, str]] = Counter()
    pair_label: dict[tuple[str, str], str] = {}
    body = set(body_paragraphs)
    for sent in seg.sentences:
        if sent.paragraph not in body:
            continue
        present = []
        for k, rx in patterns.items():
            if rx.search(sent.text):
                present.append(k)
                occurrences[k].add(sent.paragraph)
                counts[k] += 1
        for i, a in enumerate(present):
            for b in present[i + 1 :]:
                pair = tuple(sorted((a, b)))
                pair_weight[pair] += 1  # type: ignore[index]
                label = _relation(sent, [concepts[a], *aliases[a]], [concepts[b], *aliases[b]])
                if label:
                    pair_label[pair] = label  # type: ignore[index]

    g = nx.Graph()
    for k, n in counts.items():
        g.add_node(k, count=n)
    for (a, b), w in pair_weight.items():
        g.add_edge(a, b, weight=w)
    if g.number_of_nodes() == 0:
        return ConceptMap()
    rank = pagerank(g) if g.number_of_edges() else {n: 1.0 for n in g}
    keep = sorted(g.nodes, key=lambda n: -(rank[n] + 0.01 * counts[n]))[:MAX_NODES]
    sub = g.subgraph(keep).copy()
    pos = (
        nx.spring_layout(sub, seed=7, k=1.2 / max(1, len(keep)) ** 0.5, weight="weight")
        if len(keep) > 1
        else {keep[0]: (0.0, 0.0)}
    )
    pos = _spread(pos)
    top = max(rank[n] for n in keep)
    nodes = [
        Node(
            id=k,
            label=concepts[k],
            weight=round(rank[k] / top, 3),
            paragraphs=sorted(occurrences[k]),
            x=round(pos[k][0], 3),
            y=round(pos[k][1], 3),
        )
        for k in keep
    ]
    edges = [
        EdgeOut(
            source=a,
            target=b,
            label=pair_label.get((a, b)) or pair_label.get((b, a)),
            weight=float(d["weight"]),
        )
        for a, b, d in sub.edges(data=True)
    ]
    return ConceptMap(nodes=nodes, edges=edges)


def _spread(pos: dict) -> dict[str, tuple[float, float]]:  # type: ignore[type-arg]
    """Scale a spring layout to [0, 1] by rank on each axis, blended with the raw position.

    Spring layouts put loosely connected concepts far out and squash the rest into a
    clump; ranking spreads labels evenly while keeping who-is-near-whom."""
    keys = list(pos)
    if len(keys) == 1:
        return {keys[0]: (0.5, 0.5)}
    out: dict[str, list[float]] = {k: [0.0, 0.0] for k in keys}
    for axis in (0, 1):
        vals = [float(pos[k][axis]) for k in keys]
        lo, hi = min(vals), max(vals)
        order = sorted(keys, key=lambda k: pos[k][axis])
        for r, k in enumerate(order):
            raw = (float(pos[k][axis]) - lo) / ((hi - lo) or 1.0)
            out[k][axis] = 0.7 * r / (len(keys) - 1) + 0.3 * raw
    return {k: (v[0], v[1]) for k, v in out.items()}


def _relation(sent, a: list[str], b: list[str]) -> str | None:  # type: ignore[no-untyped-def]
    """Verb connecting two concepts when one is (in) the subject and the other the object."""
    span = sent.span
    la, lb = [x.lower() for x in a], [x.lower() for x in b]
    for tok in span:
        if tok.pos_ not in ("VERB", "AUX") or tok.lemma_ in LIGHT_VERBS:
            continue
        subj = " ".join(
            t.text for c in tok.children if c.dep_ in ("nsubj", "nsubjpass") for t in c.subtree
        ).lower()
        obj = " ".join(
            t.text
            for c in tok.children
            if c.dep_ in ("dobj", "pobj", "attr", "prep", "agent")
            for t in c.subtree
        ).lower()
        a_subj, a_obj = any(x in subj for x in la), any(x in obj for x in la)
        b_subj, b_obj = any(x in subj for x in lb), any(x in obj for x in lb)
        if (a_subj and b_obj) or (b_subj and a_obj):
            return tok.lemma_.lower()
    return None
