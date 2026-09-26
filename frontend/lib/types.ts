import type { JSONContent } from "@tiptap/core";
import type { AnalyzeResponse, Change, ProtectedSpan, QuestionOut, ResultOut, SpotOut, WalkthroughResponse } from "./api";

export type StepId = "humanize" | "walkthrough" | "personalize" | "prove" | "export";
export const STEPS: { id: StepId; n: number; label: string; short: string }[] = [
  { id: "humanize", n: 1, label: "Humanize", short: "Rewrite with reasons" },
  { id: "walkthrough", n: 2, label: "Walkthrough", short: "Understand each paragraph" },
  { id: "personalize", n: 3, label: "Make it yours", short: "Add your own work" },
  { id: "prove", n: 4, label: "Prove it", short: "Quiz, teach-back, viva" },
  { id: "export", n: 5, label: "Export", short: "Download + report" },
];

export type Tone = "academic" | "neutral" | "casual";
export type Origin = "ai" | "engine" | "student_edit" | "student_insert";
export type Decision = "accepted" | "rejected";

export interface HumanizeState {
  /** text the humanize request was made on (offsets of changes refer to it) */
  baseText: string;
  resultText: string;
  changes: Change[];
  protected: ProtectedSpan[];
  scoreBefore: number;
  scoreAfter: number;
  voiceMatch?: number | null;
  voiceMatchBefore?: number | null;
  decisions: Record<string, Decision>;
}

export type ParagraphMark = "got" | "confusing";

export interface WalkthroughState {
  data: WalkthroughResponse;
  /** text the walkthrough offsets refer to */
  text: string;
  /** keyed by paragraph index (WalkthroughParagraph.index) */
  marks: Record<number, ParagraphMark>;
  /** the student's own definitions, keyed by lower-cased term (feeds the Revision Deck) */
  ownDefs?: Record<string, string>;
}

/** A generic spot from /personalize/spots (offsets refer to PersonalizeState.text). */
export type Spot = SpotOut;

export interface PersonalizeState {
  /** text the spot offsets refer to */
  text: string;
  spots: Spot[];
  /** spot id -> the exact text inserted for it */
  filled: Record<string, string>;
  skipped: Record<string, boolean>;
}

export interface QuizResult {
  /** text the questions were generated from */
  text: string;
  seed: number;
  questions: QuestionOut[];
  answers: Record<string, string>;
  results: ResultOut[] | null;
  total: number | null; // 0-100, set once graded
}

export interface TeachbackResult {
  explanation: string;
  coverage: number; // 0-100
  covered: string[];
  missed: string[];
  similarity: number; // 0-1
  score?: number;
  feedback?: string;
  copied?: boolean;
  /** where each missed concept appears in the text (offsets into `text`) */
  missedSources?: { concept: string; start: number; end: number }[];
  text?: string;
}

export interface VivaTurn {
  id?: string;
  question: string;
  difficulty: string;
  level?: number;
  target_concepts: string[];
  answer: string;
  score: number;
  feedback: string;
  missed_concepts: string[];
  covered_concepts?: string[];
  /** the sentence the question came from (the model answer) */
  model_answer?: string;
  source_span?: { start: number; end: number } | null;
  seconds?: number;
}

export interface VivaSession {
  turns: VivaTurn[];
  startedAt: number;
  finishedAt?: number;
  timed: boolean;
}

export interface AssessState {
  quiz?: QuizResult;
  teachback?: TeachbackResult;
  /** the latest Viva Simulator session */
  viva?: VivaSession;
  /** earlier sessions, newest last (kept short) */
  vivaHistory?: { finishedAt: number; average: number; questions: number }[];
}

export interface DocSettings {
  tone: Tone;
  intensity: number;
  keepTerms: string[];
  useVoice: boolean;
  targetGrade: number;
}

export interface OwnDoc {
  id: string;
  title: string;
  author?: string;
  createdAt: number;
  updatedAt: number;
  originalText: string;
  content: JSONContent;
  step: StepId;
  settings: DocSettings;
  analysis?: AnalyzeResponse;
  /** the text `analysis` offsets refer to */
  analysisText?: string;
  firstScore?: number;
  humanize?: HumanizeState;
  /** decisions from earlier humanize runs (ownership: decisions made / changes offered) */
  decisionHistory?: { offered: number; decided: number };
  walkthrough?: WalkthroughState;
  personalize?: PersonalizeState;
  assess?: AssessState;
  /** downloads made in the Export step (progress history) */
  exports?: { at: number; kind: "docx" | "report" }[];
  /** Cached Ownership Score breakdown for lists/progress (recomputed live in the editor). */
  ownership?: { score: number; studentShare: number };
}

export const DEFAULT_SETTINGS: DocSettings = {
  tone: "academic",
  intensity: 3,
  keepTerms: [],
  useVoice: true,
  targetGrade: 12,
};
