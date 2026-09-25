import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { QuestionOut, ResultOut } from "@/lib/api";
import { QuestionCard } from "./QuestionCard";

const base = { source_span: { start: 0, end: 10 }, concepts: [], accepted: [], explanation: "The relay switches the pump." };
const cloze: QuestionOut = { ...base, id: "c", type: "cloze", prompt: "The _____ switches the pump.", answer_key: "relay" };
const mcq: QuestionOut = { ...base, id: "m", type: "mcq", prompt: "The _____ switches the pump.", answer_key: "relay", options: ["valve", "relay", "sensor", "fan"] };
const tf: QuestionOut = { ...base, id: "t", type: "tf", prompt: "The valve switches the pump.", answer_key: "false" };

const result = (id: string, correct: boolean, feedback = "fb"): ResultOut => ({
  id,
  correct,
  score: correct ? 100 : 0,
  feedback,
  missed_concepts: [],
  covered_concepts: [],
  source_span: { start: 0, end: 10 },
});

describe("QuestionCard", () => {
  it("renders a cloze blank as an input", () => {
    const onAnswer = vi.fn();
    render(<QuestionCard q={cloze} n={1} answer="" onAnswer={onAnswer} />);
    fireEvent.change(screen.getByLabelText("Missing term"), { target: { value: "relay" } });
    expect(onAnswer).toHaveBeenCalledWith("relay");
    expect(screen.queryByText(/_____/)).toBeNull();
  });

  it("lets the student pick one multiple-choice option", () => {
    const onAnswer = vi.fn();
    render(<QuestionCard q={mcq} n={2} answer="valve" onAnswer={onAnswer} />);
    expect(screen.getAllByRole("radio")).toHaveLength(4);
    expect(screen.getByRole("radio", { name: "valve" })).toHaveAttribute("aria-checked", "true");
    fireEvent.click(screen.getByRole("radio", { name: "relay" }));
    expect(onAnswer).toHaveBeenCalledWith("relay");
  });

  it("answers true/false", () => {
    const onAnswer = vi.fn();
    render(<QuestionCard q={tf} n={3} answer="" onAnswer={onAnswer} />);
    fireEvent.click(screen.getByRole("radio", { name: "false" }));
    expect(onAnswer).toHaveBeenCalledWith("false");
  });

  it("shows the result and feedback once graded, and locks the answer", () => {
    render(<QuestionCard q={mcq} n={2} answer="valve" result={result("m", false, "The answer is “relay”.")} onAnswer={vi.fn()} />);
    expect(screen.getByText("Not quite")).toBeInTheDocument();
    expect(screen.getByText("The answer is “relay”.")).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "relay" })).toBeDisabled();
  });

  it("marks a correct answer", () => {
    render(<QuestionCard q={cloze} n={1} answer="relay" result={result("c", true)} onAnswer={vi.fn()} />);
    expect(screen.getByText("Correct")).toBeInTheDocument();
  });
});
