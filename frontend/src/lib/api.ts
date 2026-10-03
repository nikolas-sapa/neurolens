// frontend/src/lib/api.ts
import type { AnalysisResult, CompareResult, ProjectSummary, Project, PersonaSummary, PersonaDetail, SharedProject } from "@/types/analysis";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function post(path: string, body: FormData): Promise<unknown> {
  const res = await fetch(`${BASE}${path}`, { method: "POST", body });
  if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
  return res.json();
}

export const analyzeFile = (file: File): Promise<AnalysisResult> => {
  const f = new FormData(); f.append("file", file);
  return post("/analyze", f) as Promise<AnalysisResult>;
};

export const analyzeYoutube = (url: string): Promise<AnalysisResult> => {
  const f = new FormData(); f.append("youtube_url", url);
  return post("/analyze", f) as Promise<AnalysisResult>;
};

export const analyzeText = (text: string): Promise<AnalysisResult> => {
  const f = new FormData(); f.append("text_content", text);
  return post("/analyze", f) as Promise<AnalysisResult>;
};

export const comparePair = (a: FormData, b: FormData): Promise<CompareResult> => {
  const f = new FormData();
  a.forEach((v, k) => f.append(k + "_a", v));
  b.forEach((v, k) => f.append(k + "_b", v));
  return post("/compare", f) as Promise<CompareResult>;
};

async function json_get(path: string): Promise<unknown> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
  return res.json();
}

async function json_post(path: string, body: unknown): Promise<unknown> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
  return res.json();
}

export const listProjects = (): Promise<ProjectSummary[]> =>
  json_get("/projects") as Promise<ProjectSummary[]>;

export const saveProject = (name: string, result: AnalysisResult): Promise<{ id: number }> =>
  json_post("/projects", { name, result }) as Promise<{ id: number }>;

export const getProject = (id: number): Promise<Project> =>
  json_get(`/projects/${id}`) as Promise<Project>;

export const deleteProject = async (id: number): Promise<void> => {
  const res = await fetch(`${BASE}/projects/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
};

async function json_put(path: string, body: unknown): Promise<unknown> {
  const res = await fetch(`${BASE}${path}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
  return res.json();
}

export const listPersonas = (): Promise<PersonaSummary[]> =>
  json_get("/personas") as Promise<PersonaSummary[]>;

export const getPersona = (id: number): Promise<PersonaDetail> =>
  json_get(`/personas/${id}`) as Promise<PersonaDetail>;

export const createPersona = (data: Omit<PersonaDetail, "id">): Promise<{ id: number }> =>
  json_post("/personas", data) as Promise<{ id: number }>;

export const updatePersona = (id: number, data: Omit<PersonaDetail, "id">): Promise<void> =>
  json_put(`/personas/${id}`, data).then(() => undefined);

export const deletePersona = (id: number): Promise<void> =>
  fetch(`${BASE}/personas/${id}`, { method: "DELETE" })
    .then(res => { if (!res.ok) throw new Error(`${res.status}: ${res.statusText}`); });

export const shareProject = (id: number): Promise<{ token: string }> =>
  json_post(`/projects/${id}/share`, {}) as Promise<{ token: string }>;

export const getSharedProject = (token: string): Promise<SharedProject> =>
  json_get(`/share/${token}`) as Promise<SharedProject>;

export interface GeneratedPersona {
  name: string;
  tagline: string;
  step_overlays: Record<string, string[]>;
}

export const generatePersona = (
  name: string,
  source: string,
): Promise<GeneratedPersona> =>
  json_post("/personas/generate", { name, source }) as Promise<GeneratedPersona>;
