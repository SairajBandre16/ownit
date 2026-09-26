import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { DoctorResponse, Issue } from "@/lib/api";
import { DoctorPanel, checkOf } from "./DoctorPanel";

const issue = (id: string, rule: string, start: number, end: number, message: string, suggestion: string | null = null): Issue => ({
  id,
  start,
  end,
  category: "engineering",
  rule,
  severity: "warn",
  message,
  suggestion,
  lesson_slug: "units",
});

const text = "The supply was 12V. The PLC always works.";
const result: DoctorResponse = {
  issues: [
    issue("a", "units.spacing", 15, 18, "Put a space between a number and its unit: '12 V'.", "12 V"),
    issue("b", "abbr.undefined", 24, 27, "'PLC' is used before it's defined."),
    issue("c", "claims.unsupported", 28, 34, "Unsupported claim ('always')."),
  ],
  counts: { units: 1, abbreviations: 1, figures: 0, tense: 0, claims: 1, structure: 0 },
};

describe("DoctorPanel", () => {
  it("maps rules to checks", () => {
    expect(checkOf(result.issues[0])).toBe("Units");
    expect(checkOf(result.issues[1])).toBe("Abbreviations");
    expect(checkOf(result.issues[2])).toBe("Claims");
  });

  it("shows a count per check and filters the list by check", () => {
    render(<DoctorPanel result={result} loading={false} text={text} activeId={null} onSelect={vi.fn()} onApply={vi.fn()} />);
    expect(screen.getByText("Figures & tables")).toBeInTheDocument();
    expect(screen.getAllByText("✓")).toHaveLength(3); // figures, tense, structure pass
    fireEvent.click(screen.getByRole("button", { name: /Units 1/ }));
    expect(screen.getByText(/Put a space/)).toBeInTheDocument();
    expect(screen.queryByText(/Unsupported claim/)).toBeNull();
  });

  it("offers the fix of the active issue", () => {
    const onApply = vi.fn();
    render(<DoctorPanel result={result} loading={false} text={text} activeId="a" onSelect={vi.fn()} onApply={onApply} />);
    fireEvent.click(screen.getByRole("button", { name: "Use “12 V”" }));
    expect(onApply).toHaveBeenCalledWith(result.issues[0]);
  });

  it("says so when nothing is wrong, and while it is still checking", () => {
    const { rerender } = render(<DoctorPanel loading text="" activeId={null} onSelect={vi.fn()} onApply={vi.fn()} />);
    expect(screen.getByText(/Checking units/)).toBeInTheDocument();
    rerender(
      <DoctorPanel
        result={{ issues: [], counts: { units: 0, abbreviations: 0, figures: 0, tense: 0, claims: 0, structure: 0 } }}
        loading={false}
        text=""
        activeId={null}
        onSelect={vi.fn()}
        onApply={vi.fn()}
      />,
    );
    expect(screen.getByText("No engineering-report problems found.")).toBeInTheDocument();
  });
});
