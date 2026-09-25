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

MAX_NODES = 18


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
    concepts: dict[str, str] = {}
    for p in phrases:
        k = _key(p)
        if k and not any(k in other or other in k for other in concepts if k != other):
            concepts[k] = p
    if not concepts:
        return ConceptMap()
    patterns = {
        k: re.compile(rf"(?<![\w-]){re.escape(label)}s?(?![\w-])", re.IGNORECASE)
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
                label = _relation(sent, concepts[a], concepts[b])
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
    xs = [p[0] for p in pos.values()]
    ys = [p[1] for p in pos.values()]
    span_x = (max(xs) - min(xs)) or 1.0
    span_y = (max(ys) - min(ys)) or 1.0
    top = max(rank[n] for n in keep)
    nodes = [
        Node(
            id=k,
            label=concepts[k],
            weight=round(rank[k] / top, 3),
            paragraphs=sorted(occurrences[k]),
            x=round((pos[k][0] - min(xs)) / span_x, 3),
            y=round((pos[k][1] - min(ys)) / span_y, 3),
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


def _relation(sent, a: str, b: str) -> str | None:  # type: ignore[no-untyped-def]
    """Verb connecting two concepts when one is (in) the subject and the other the object."""
    span = sent.span
    la, lb = a.lower(), b.lower()
    for tok in span:
        if tok.pos_ not in ("VERB", "AUX") or tok.lemma_ == "be":
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
        if (la in subj and lb in obj) or (lb in subj and la in obj):
            return tok.lemma_.lower()
    return None
