import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { loadCards, loadReviews, saveCards } from "@/lib/deck";
import { setMeta } from "@/lib/db";
import { newCard } from "@/lib/srs";
import { DeckReview } from "./DeckReview";

const past = Date.now() - 1000;
const cards = [
  newCard({ id: "a", front: "Define: relay", back: "an electrically operated switch", source: "glossary", docId: "d", docTitle: "Pump report" }, past),
  newCard({ id: "b", front: "Why a relay?", back: "It isolates the pump circuit.", source: "viva", docId: "d", docTitle: "Pump report" }, past + 1),
];

describe("DeckReview", () => {
  beforeEach(async () => {
    await saveCards(cards);
    await setMeta("deck.reviews", []);
  });

  it("reviews due cards with the keyboard and saves the schedule", async () => {
    render(<DeckReview />);
    const reviewBox = await screen.findByRole("region", { name: "Review" });
    expect(within(reviewBox).getByText("Define: relay")).toBeInTheDocument();
    expect(screen.getByText("Due now").previousSibling).toHaveTextContent("2");

    await act(async () => {
      fireEvent.keyDown(window, { key: " " });
    });
    expect(screen.getByText("an electrically operated switch")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Good/ })).toHaveTextContent("1 d");

    await act(async () => {
      fireEvent.keyDown(window, { key: "3" });
    });
    await waitFor(() => expect(within(screen.getByRole("region", { name: "Review" })).getByText("Why a relay?")).toBeInTheDocument());
    await waitFor(async () => {
      const saved = await loadCards();
      expect(saved.find((c) => c.id === "a")?.reps).toBe(1);
      expect((await loadReviews()).map((r) => r.grade)).toEqual([3]);
    });
    expect(screen.getByText("Reviewed today").previousSibling).toHaveTextContent("1");
  });

  it("says when everything is reviewed", async () => {
    await saveCards(cards.map((c) => ({ ...c, due: Date.now() + 86_400_000 })));
    render(<DeckReview />);
    expect(await screen.findByText("All caught up")).toBeInTheDocument();
  });
});
