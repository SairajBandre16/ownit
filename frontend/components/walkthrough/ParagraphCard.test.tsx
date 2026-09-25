import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { WalkthroughParagraph } from "@/lib/api";
import { ParagraphCard } from "./ParagraphCard";

const text = "Intro\nThe PLC drives the valve.";
const para: WalkthroughParagraph = {
  index: 1,
  start: 6,
  end: text.length,
  section: "introduction",
  gist: "The PLC drives the valve.",
  key_terms: [
    { term: "PLC", start: 10, end: 13, definition: "programmable logic controller", source: "abbreviation" },
    { term: "valve", start: 25, end: 30, definition: null, source: null },
  ],
  simplified: "The PLC opens the valve.",
  grade_before: 6,
  grade_after: 4,
};

function setup(overrides: Partial<React.ComponentProps<typeof ParagraphCard>> = {}) {
  const props = {
    para,
    n: 1,
    total: 3,
    text,
    active: false,
    simple: false,
    onMark: vi.fn(),
    onToggleSimple: vi.fn(),
    onDefine: vi.fn(),
    onFocus: vi.fn(),
    ...overrides,
  };
  render(<ParagraphCard {...props} />);
  return props;
}

describe("ParagraphCard", () => {
  it("shows the gist, section and key terms with definitions or a prompt", () => {
    setup();
    expect(screen.getByText("The PLC drives the valve.", { selector: "p" })).toBeInTheDocument();
    expect(screen.getByText("Introduction")).toBeInTheDocument();
    expect(screen.getByText(/programmable logic controller/)).toBeInTheDocument();
    expect(screen.getByText(/No definition found/)).toBeInTheDocument();
  });

  it("marks the paragraph and toggles a mark off", () => {
    const p = setup();
    fireEvent.click(screen.getByRole("button", { name: /Got it/ }));
    expect(p.onMark).toHaveBeenCalledWith("got");
    const q = setup({ mark: "confusing" });
    fireEvent.click(screen.getAllByRole("button", { name: /Confusing/ })[1]);
    expect(q.onMark).toHaveBeenCalledWith(null);
  });

  it("saves the student's own definition", () => {
    const p = setup();
    fireEvent.click(screen.getByRole("button", { name: "Define valve in your own words" }));
    fireEvent.change(screen.getByLabelText("Your definition of valve"), { target: { value: "controls flow" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(p.onDefine).toHaveBeenCalledWith("valve", "controls flow");
  });

  it("shows the student's definition instead of the tool's", () => {
    setup({ ownDefs: { plc: "the box that runs the machine" } });
    expect(screen.getByText(/the box that runs the machine/)).toBeInTheDocument();
    expect(screen.getByText("your definition")).toBeInTheDocument();
  });

  it("shows the simpler version with reading grades", () => {
    const p = setup({ simple: true });
    expect(screen.getByText("The PLC opens the valve.")).toBeInTheDocument();
    expect(screen.getByText(/6\.0 → 4\.0/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Show original/ }));
    expect(p.onToggleSimple).toHaveBeenCalled();
  });
});
