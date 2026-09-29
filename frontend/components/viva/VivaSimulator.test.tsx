import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { QuestionOut } from "@/lib/api";
import { getDoc, saveDoc } from "@/lib/db";
import { textToContent } from "@/lib/offsets";
import { useSettings } from "@/lib/store";
import { DEFAULT_SETTINGS, type OwnDoc } from "@/lib/types";

const q = (i: number, level: number): QuestionOut => ({
  id: `v${i}`,
  type: "viva",
  prompt: `Question number ${i}?`,
  answer_key: "The relay switches the pump.",
  source_span: { start: 0, end: 28 },
  concepts: ["relay"],
  accepted: [],
  explanation: "The relay switches the pump.",
  level,
  difficulty: "Define",
});

const vivaNext = vi.fn();
const grade = vi.fn();
vi.mock("@/lib/api", async (orig) => ({ ...(await orig<typeof import("@/lib/api")>()), api: { vivaNext: (...a: unknown[]) => vivaNext(...a), grade: (...a: unknown[]) => grade(...a), health: async () => ({ status: "ok", languagetool: true }) } }));

// imported after the mock
const { VivaSimulator } = await import("./VivaSimulator");

const doc: OwnDoc = {
  id: "viva-doc",
  title: "Pump report",
  createdAt: 0,
  updatedAt: 0,
  originalText: "The relay switches the pump.",
  content: textToContent("The relay switches the pump.", "ai"),
  step: "prove",
  settings: DEFAULT_SETTINGS,
};

describe("VivaSimulator", () => {
  beforeEach(async () => {
    vivaNext.mockReset();
    grade.mockReset();
    useSettings.setState({ vivaTimer: false });
    await saveDoc(doc);
  });

  it("runs a session: question → feedback → next → results, and saves the turns", async () => {
    vivaNext
      .mockResolvedValueOnce({ done: false, index: 1, total: 2, question: q(1, 1), difficulty: "Define", target_concepts: ["relay"] })
      .mockResolvedValueOnce({ done: false, index: 2, total: 2, question: q(2, 2), difficulty: "Explain how", target_concepts: ["relay"] });
    grade.mockImplementation(async (qs: QuestionOut[]) => ({
      total: 80,
      results: [
        { id: qs[0].id, correct: null, score: 80, feedback: "Good answer.", missed_concepts: [], covered_concepts: ["relay"], source_span: { start: 0, end: 28 } },
      ],
    }));

    render(<QueryClientProvider client={new QueryClient()}><VivaSimulator docId="viva-doc" /></QueryClientProvider>);
    fireEvent.click(await screen.findByRole("button", { name: /Begin/ }));
    expect(await screen.findByText("Question number 1?")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Your answer"), { target: { value: "A relay turns the pump on." } });
    fireEvent.click(screen.getByRole("button", { name: "Submit answer" }));
    expect(await screen.findByText("Good answer.")).toBeInTheDocument();
    expect(screen.getByText("From your report")).toBeInTheDocument();
    expect(grade).toHaveBeenCalledWith([expect.objectContaining({ id: "v1" })], [{ id: "v1", answer: "A relay turns the pump on." }], expect.any(String));

    fireEvent.click(screen.getByRole("button", { name: /Next question/ }));
    expect(await screen.findByText("Question number 2?")).toBeInTheDocument();
    // the history sent to the server carries the first answer and its score
    expect(vivaNext).toHaveBeenLastCalledWith(expect.any(String), [expect.objectContaining({ question: "Question number 1?", score: 80, id: "v1" })]);

    fireEvent.click(screen.getByRole("button", { name: "I don't know" }));
    fireEvent.click(await screen.findByRole("button", { name: /See results/ }));
    expect(await screen.findByText("Session complete")).toBeInTheDocument();

    await waitFor(async () => {
      const saved = await getDoc("viva-doc");
      expect(saved?.assess?.viva?.turns).toHaveLength(2);
      expect(saved?.assess?.viva?.finishedAt).toBeTypeOf("number");
      expect(saved?.assess?.vivaHistory).toHaveLength(1);
    });
  });

  it("auto-submits when the timer runs out", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    useSettings.setState({ vivaTimer: true });
    vivaNext.mockResolvedValue({ done: false, index: 1, total: 10, question: q(1, 1), difficulty: "Define", target_concepts: [] });
    grade.mockResolvedValue({
      total: 0,
      results: [{ id: "v1", correct: null, score: 0, feedback: "Write at least one full sentence.", missed_concepts: ["relay"], covered_concepts: [], source_span: { start: 0, end: 28 } }],
    });
    render(<QueryClientProvider client={new QueryClient()}><VivaSimulator docId="viva-doc" /></QueryClientProvider>);
    fireEvent.click(await screen.findByRole("button", { name: /Begin/ }));
    await screen.findByText("Question number 1?");
    expect(screen.getByRole("timer")).toHaveAccessibleName("60 seconds left");
    await act(async () => {
      vi.advanceTimersByTime(61_000);
    });
    expect(await screen.findByText("Write at least one full sentence.")).toBeInTheDocument();
    vi.useRealTimers();
  });
});
