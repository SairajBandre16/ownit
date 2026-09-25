import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import type { Change } from "@/lib/api";
import type { Decision } from "@/lib/types";
import { DiffView } from "./DiffView";

const changes: Change[] = ["one", "two", "three"].map((w, i) => ({
  id: w,
  orig_start: i * 10,
  orig_end: i * 10 + 3,
  new_start: 0,
  new_end: 0,
  original: w,
  replacement: w.toUpperCase(),
  transform: "synonym",
  category: "vocabulary",
  reason: `reason ${w}`,
  confidence: 0.9,
}));

function Harness({ onDecide }: { onDecide: (id: string, d: Decision | null) => void }) {
  const [active, setActive] = useState<string | null>(null);
  const [decisions, setDecisions] = useState<Record<string, Decision>>({});
  return (
    <DiffView
      changes={changes}
      decisions={decisions}
      stale={new Set()}
      activeId={active}
      onActivate={setActive}
      onDecide={(id, d) => {
        onDecide(id, d);
        setDecisions((prev) => ({ ...prev, ...(d ? { [id]: d } : {}) }));
      }}
      onBulk={() => {}}
    />
  );
}

describe("DiffView keyboard review", () => {
  it("J moves to the first card, A accepts, R rejects the next", () => {
    const onDecide = vi.fn();
    render(<Harness onDecide={onDecide} />);
    fireEvent.keyDown(window, { key: "j" });
    fireEvent.keyDown(window, { key: "a" });
    expect(onDecide).toHaveBeenLastCalledWith("one", "accepted");
    fireEvent.keyDown(window, { key: "r" });
    expect(onDecide).toHaveBeenLastCalledWith("two", "rejected");
    expect(screen.getAllByText("Accepted")).toHaveLength(1);
    expect(screen.getAllByText("Rejected")).toHaveLength(1);
  });

  it("ignores shortcuts while typing in an input", () => {
    const onDecide = vi.fn();
    render(
      <>
        <input aria-label="field" />
        <Harness onDecide={onDecide} />
      </>,
    );
    fireEvent.keyDown(screen.getByLabelText("field"), { key: "a" });
    expect(onDecide).not.toHaveBeenCalled();
  });

  it("buttons accept and reject", () => {
    const onDecide = vi.fn();
    render(<Harness onDecide={onDecide} />);
    fireEvent.click(screen.getAllByRole("button", { name: /Accept A/ })[0]);
    expect(onDecide).toHaveBeenCalledWith("one", "accepted");
  });
});
