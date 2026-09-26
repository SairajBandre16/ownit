/**
 * Typed client for the OwnIt API. Types come from the backend's OpenAPI schema
 * (`npm run gen:api` regenerates lib/api-types.ts).
 */
import type { components } from "./api-types";

export type Schemas = components["schemas"];
export type Issue = Schemas["Issue"];
export type Change = Schemas["Change"];
export type HumanizeResponse = Schemas["HumanizeResponse"];
export type StyleProfile = Schemas["StyleProfile"];
export type CompareResponse = Schemas["CompareResponse"];
export type ProtectedSpan = Schemas["ProtectedSpan"];
export type AnalyzeResponse = Schemas["AnalyzeResponse"];
export type Section = Schemas["Section"];
export type WalkthroughResponse = Schemas["WalkthroughResponse"];
export type WalkthroughParagraph = Schemas["ParagraphOut"];
export type KeyTerm = Schemas["KeyTerm"];
export type ConceptMapData = Schemas["ConceptMapOut"];
export type SpotOut = Schemas["SpotOut"];
export type QuestionOut = Schemas["QuestionOut"];
export type ResultOut = Schemas["ResultOut"];
export type GradeResponse = Schemas["GradeResponse"];
export type VivaNextResponse = Schemas["VivaNextResponse"];
export type TeachbackResponse = Schemas["TeachbackResponse"];
export type DoctorResponse = Schemas["DoctorResponse"];

export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, init);
  } catch {
    throw new ApiError(0, "Can't reach the OwnIt server. Is the backend running?");
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail ?? body);
    } catch {
      /* not JSON */
    }
    if (res.status === 429) detail = "Too many requests — wait a minute and try again.";
    throw new ApiError(res.status, detail);
  }
  return (await res.json()) as T;
}

export function post<T>(path: string, body: unknown, signal?: AbortSignal): Promise<T> {
  return request<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
}

export function get<T>(path: string, signal?: AbortSignal): Promise<T> {
  return request<T>(path, { method: "GET", signal });
}

/** POST that returns a file (e.g. .docx export). */
export async function postBlob(path: string, body: unknown): Promise<{ blob: Blob; filename: string }> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, "Can't reach the OwnIt server. Is the backend running?");
  }
  if (!res.ok) throw new ApiError(res.status, res.statusText);
  const cd = res.headers.get("Content-Disposition") ?? "";
  const match = /filename="?([^";]+)"?/.exec(cd);
  return { blob: await res.blob(), filename: match?.[1] ?? "document.docx" };
}

export async function uploadFile(path: string, file: File): Promise<Schemas["ExtractResponse"]> {
  const form = new FormData();
  form.append("file", file);
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { method: "POST", body: form });
  } catch {
    throw new ApiError(0, "Can't reach the OwnIt server. Is the backend running?");
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, String(detail));
  }
  return res.json();
}

export const api = {
  health: () => get<Schemas["HealthResponse"]>("/health"),
  analyze: (text: string, target_grade?: number, signal?: AbortSignal) =>
    post<AnalyzeResponse>("/analyze", { text, target_grade }, signal),
  humanize: (body: Schemas["HumanizeRequest"], signal?: AbortSignal) =>
    post<HumanizeResponse>("/humanize", body, signal),
  fingerprint: (samples: string[]) => post<StyleProfile>("/style/fingerprint", { samples }),
  compareStyle: (text: string, profile: StyleProfile, signal?: AbortSignal) =>
    post<CompareResponse>("/style/compare", { text, profile }, signal),
  walkthrough: (text: string, signal?: AbortSignal) => post<WalkthroughResponse>("/walkthrough", { text }, signal),
  spots: (text: string, signal?: AbortSignal) => post<Schemas["SpotsResponse"]>("/personalize/spots", { text }, signal),
  generateQuestions: (text: string, confusing_paragraphs: string[], seed = 0) =>
    post<Schemas["GenerateResponse"]>("/assess/generate", { text, confusing_paragraphs, seed }),
  grade: (questions: QuestionOut[], answers: { id: string; answer: string }[], text?: string) =>
    post<GradeResponse>("/assess/grade", { questions, answers, text }),
  vivaNext: (text: string, history: Schemas["VivaTurnIn"][]) => post<VivaNextResponse>("/assess/viva/next", { text, history }),
  teachback: (text: string, explanation: string) => post<TeachbackResponse>("/teachback", { text, explanation }),
  doctor: (text: string, signal?: AbortSignal) => post<DoctorResponse>("/doctor", { text }, signal),
  exportDocx: (body: Schemas["ExportDocxRequest"]) => postBlob("/export/docx", body),
  exportReport: (body: Schemas["UnderstandingReportRequest"]) => postBlob("/export/report", body),
};
