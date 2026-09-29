import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { IssueList } from "@/components/analysis/IssueList";
import type { Issue } from "@/lib/api";
import { useWorkspace } from "@/lib/store";
import { LayerToggles } from "./LayerToggles";

const issue = (id: string, category: string): Issue => ({
  id,
  start: 0,
  end: 1,
  category,
  rule: "r",
  severity: "info",
  message: `${category} issue ${id}`,
  suggestion: null,
  lesson_slug: null,
});

describe("Layers menu", () => {
  beforeEach(() => {
    useWorkspace.setState({
      layers: { issues: true, protected: true, changes: true, engineering: false, spots: false },
      heatmap: false,
      issueFocus: null,
    });
  });

  it("puts every layer and the heatmap behind one button", () => {
    render(<LayerToggles available={["issues", "protected", "changes", "engineering"]} />);
    const trigger = screen.getByRole("button", { name: "Highlight layers, 3 on" });
    fireEvent.click(trigger);
    fireEvent.click(screen.getByRole("menuitemcheckbox", { name: /Report Doctor/ }));
    expect(useWorkspace.getState().layers.engineering).toBe(true);
    fireEvent.click(screen.getByRole("menuitemcheckbox", { name: /Ownership heatmap/ }));
    expect(useWorkspace.getState().heatmap).toBe(true);
    expect(screen.getByRole("button", { name: "Highlight layers, 5 on" })).toBeInTheDocument();
  });
});

describe("IssueList focus", () => {
  it("shares its category filter when controlled", () => {
    const issues = [issue("1", "clarity"), issue("2", "rhythm"), issue("3", "rhythm")];
    let focus: string | null = null;
    const { rerender } = render(<IssueList issues={issues} filter={focus} onFilter={(f) => (focus = f)} note="note text" />);
    expect(screen.getByText("note text")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /rhythm 2/ }));
    expect(focus).toBe("rhythm");
    rerender(<IssueList issues={issues} filter={focus} onFilter={(f) => (focus = f)} />);
    expect(screen.queryByText("clarity issue 1")).toBeNull();
    expect(screen.getAllByText(/rhythm issue/)).toHaveLength(2);
  });
});
