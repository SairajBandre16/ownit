import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { saveCards } from "@/lib/deck";
import { saveDoc, setMeta } from "@/lib/db";
import { textToContent } from "@/lib/offsets";
import { newCard } from "@/lib/srs";
import { DEFAULT_SETTINGS, type OwnDoc } from "@/lib/types";
import { ProgressDashboard } from "./ProgressDashboard";

const doc: OwnDoc = {
  id: "p1",
  title: "Pump report",
  createdAt: 0,
  updatedAt: Date.now(),
  originalText: "",
  content: textToContent("The relay switches the pump.", "ai"),
  step: "prove",
  settings: DEFAULT_SETTINGS,
  firstScore: 61,
  ownership: { score: 42, studentShare: 0.3 },
  assess: {
    quiz: { text: "", seed: 0, questions: [], answers: {}, results: [], total: 80 },
    vivaHistory: [{ finishedAt: Date.now() - 86_400_000, average: 64, questions: 10 }],
  },
};

describe("ProgressDashboard", () => {
  beforeEach(async () => {
    await saveDoc(doc);
    await saveCards([newCard({ id: "c", front: "f", back: "b", source: "glossary", docId: "p1", docTitle: "Pump report" }, 0)]);
    await setMeta("deck.reviews", [{ at: Date.now(), cardId: "c", grade: 3 }]);
  });

  it("summarises documents, viva sessions and the deck", async () => {
    render(<ProgressDashboard />);
    expect(await screen.findByRole("link", { name: "Pump report" })).toHaveAttribute("href", "/workspace/p1");
    const tile = (label: string) => screen.getByText(label).previousSibling;
    expect(tile("Avg ownership")).toHaveTextContent("42");
    expect(tile("Viva sessions")).toHaveTextContent("1");
    expect(tile("Cards due")).toHaveTextContent("1");
    expect(tile("Review streak")).toHaveTextContent("1 d");
    expect(screen.getByRole("cell", { name: "80%" })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "5" })).toBeInTheDocument(); // words
    expect(screen.getAllByText("Show as a table")).toHaveLength(2);
  });
});
