import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { WalkthroughResponse } from "@/lib/api";
import { useSettings, useWorkspace } from "@/lib/store";
import { DEFAULT_SETTINGS, type OwnDoc } from "@/lib/types";

const exportDocx = vi.fn();
const exportReport = vi.fn();
vi.mock("@/lib/api", async (orig) => ({
  ...(await orig<typeof import("@/lib/api")>()),
  api: { exportDocx: (...a: unknown[]) => exportDocx(...a), exportReport: (...a: unknown[]) => exportReport(...a) },
}));
const saveBlob = vi.fn();
vi.mock("@/lib/download", () => ({ saveBlob: (...a: unknown[]) => saveBlob(...a) }));

const { ExportStep } = await import("./ExportStep");

function makeDoc(passed: boolean): OwnDoc {
  return {
    id: "d",
    title: "Solar Tracker",
    createdAt: 0,
    updatedAt: 0,
    originalText: "",
    content: { type: "doc" },
    step: "export",
    settings: DEFAULT_SETTINGS,
    walkthrough: {
      text: "",
      data: { paragraphs: [{ index: 0, key_terms: [] }], concept_map: { nodes: [], edges: [] } } as unknown as WalkthroughResponse,
      marks: passed ? { 0: "got" } : {},
    },
    assess: passed
      ? {
          quiz: { text: "", seed: 0, questions: [], answers: {}, results: [], total: 90 },
          teachback: { explanation: "", coverage: 70, covered: [], missed: [], similarity: 0.5 },
        }
      : undefined,
  };
}

function renderStep(onGo = vi.fn()) {
  const client = new QueryClient();
  render(
    <QueryClientProvider client={client}>
      <ExportStep onGo={onGo} />
    </QueryClientProvider>,
  );
  return onGo;
}

describe("ExportStep", () => {
  beforeEach(() => {
    exportDocx.mockReset();
    exportReport.mockReset();
    saveBlob.mockReset();
    useSettings.setState({ gateEnabled: true, quizThreshold: 70, teachbackThreshold: 60, walkthroughThreshold: 80 });
  });

  it("stays locked until every check is passed, and links to what's missing", () => {
    useWorkspace.setState({ doc: makeDoc(false), text: "Some text here." });
    const onGo = renderStep();
    expect(screen.getByText(/Export unlocks when you understand/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Download .docx/ })).toBeNull();
    expect(screen.getAllByRole("button", { name: "Go there" })).toHaveLength(3);
    fireEvent.click(screen.getAllByRole("button", { name: "Go there" })[0]);
    expect(onGo).toHaveBeenCalledWith("walkthrough");
  });

  it("unlocks when the gate is switched off", () => {
    useSettings.setState({ gateEnabled: false });
    useWorkspace.setState({ doc: makeDoc(false), text: "Some text here." });
    renderStep();
    expect(screen.getByRole("button", { name: /Download .docx/ })).toBeInTheDocument();
    expect(screen.getByText("Understanding gate is switched off")).toBeInTheDocument();
  });

  it("downloads the document and the report once passed", async () => {
    useWorkspace.setState({ doc: makeDoc(true), text: "Some text here." });
    exportDocx.mockResolvedValue({ blob: new Blob(["x"]), filename: "Solar-Tracker.docx" });
    exportReport.mockResolvedValue({ blob: new Blob(["y"]), filename: "Solar-Tracker-understanding-report.docx" });
    renderStep();
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(screen.getByRole("button", { name: /Download .docx/ }));
    await waitFor(() => expect(saveBlob).toHaveBeenCalledWith(expect.any(Blob), "Solar-Tracker.docx"));
    expect(exportDocx).toHaveBeenCalledWith(
      expect.objectContaining({ text: "Some text here.", title: "Solar Tracker", understanding: expect.objectContaining({ score: expect.any(Number) }) }),
    );
    fireEvent.click(screen.getByRole("button", { name: /Download Understanding Report/ }));
    await waitFor(() => expect(saveBlob).toHaveBeenCalledTimes(2));
    expect(exportReport).toHaveBeenCalledWith(expect.objectContaining({ title: "Solar Tracker", gate_passed: true }));
    expect(useWorkspace.getState().doc?.exports?.map((e) => e.kind)).toEqual(["docx", "report"]);
  });
});
