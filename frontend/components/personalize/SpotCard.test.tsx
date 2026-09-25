import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { Spot } from "@/lib/types";
import { SpotCard } from "./SpotCard";

const spot: Spot = {
  id: "sp-1",
  start: 0,
  end: 7,
  insert_at: 30,
  pattern: "vague_quantifier",
  label: "Vague amount",
  prompt: "'various': how many, or which ones?",
  starter: "These include ",
  quote: "various",
};

function setup(props: Partial<React.ComponentProps<typeof SpotCard>> = {}) {
  const handlers = { onInsert: vi.fn(), onSkip: vi.fn(), onFocus: vi.fn() };
  render(<SpotCard spot={spot} index={0} active {...handlers} {...props} />);
  return handlers;
}

describe("SpotCard", () => {
  it("shows the prompt and a pre-filled answer box", () => {
    setup();
    expect(screen.getByText(spot.prompt)).toBeInTheDocument();
    expect(screen.getByLabelText("Your answer")).toHaveValue("These include ");
  });

  it("only inserts once the student has written something", () => {
    const h = setup();
    const insert = screen.getByRole("button", { name: /Insert/ });
    expect(insert).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Your answer"), { target: { value: "These include 3 soil sensors" } });
    fireEvent.click(insert);
    expect(h.onInsert).toHaveBeenCalledWith("These include 3 soil sensors");
  });

  it("inserts with Ctrl+Enter and can be skipped", () => {
    const h = setup();
    const box = screen.getByLabelText("Your answer");
    fireEvent.change(box, { target: { value: "Two relays" } });
    fireEvent.keyDown(box, { key: "Enter", ctrlKey: true });
    expect(h.onInsert).toHaveBeenCalledWith("Two relays");
    fireEvent.click(screen.getByRole("button", { name: "Skip" }));
    expect(h.onSkip).toHaveBeenCalledWith(true);
  });

  it("shows the inserted answer once filled", () => {
    setup({ filled: "These include 3 soil sensors." });
    expect(screen.getByText("Added")).toBeInTheDocument();
    expect(screen.queryByLabelText("Your answer")).toBeNull();
  });

  it("warns instead of offering an answer box when the spot is stale", () => {
    setup({ stale: true });
    expect(screen.getByText(/can't be found any more/)).toBeInTheDocument();
    expect(screen.queryByLabelText("Your answer")).toBeNull();
  });
});
