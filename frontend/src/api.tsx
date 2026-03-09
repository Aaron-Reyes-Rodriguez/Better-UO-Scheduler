import axios from 'axios';

/**
 * API base URL for the backend.
 * - Development: use .env with VITE_API_URL=http://localhost:8000
 * - Production (Amplify): set VITE_API_URL in Amplify env to your Render API URL
 */
const API_BASE =
  typeof import.meta.env.VITE_API_URL === "string" && import.meta.env.VITE_API_URL !== ""
    ? import.meta.env.VITE_API_URL.replace(/\/$/, "")
    : "http://localhost:8000";

export const apiBase = API_BASE;

export function apiUrl(path: string): string {
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${API_BASE}${p}`;
}

export async function auditCs(takenAttempts: Array<{
  attempt_id: string;
  course_id: string;
  credits_taken: number;
  grading_basis: string;
  term?: string;
  subtitle?: string;
}>) {
  const url = apiUrl("/audit/cs");
  const res = await fetch(url, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ taken_attempts: takenAttempts }),
  });
  if (!res.ok) throw new Error(`Audit failed: ${res.status} ${res.statusText}`);
  return res.json();
}

/** Fetch with clearer errors for CORS, network, and timeouts. */
export async function fetchHealth(): Promise<{ status: string }> {
  const url = apiUrl("/health");
  try {
    const res = await fetch(url, { method: "GET" });
    const data = await res.json();
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    return data as { status: string };
  } catch (e) {
    if (e instanceof TypeError && e.message.includes("fetch"))
      throw new Error("Network error (CORS or backend unreachable). Check Render CORS_ORIGINS and that the backend is running.");
    if (e instanceof Error) throw e;
    throw new Error("Request failed");
  }
}

export async function getClass(class_id: string) {
  const url = apiUrl(`/class/${class_id}`);
  const res = await fetch(url, { method: "GET" });
  if (!res.ok) throw new Error(`Class not found: ${res.status} ${res.statusText}`);
  return res.json();
}

export async function getProfessor(professor_id: string) {
  const url = apiUrl(`/professor/${professor_id}`);
  const res = await fetch(url, { method: "GET" });
  if (!res.ok) throw new Error(`Professor not found: ${res.status} ${res.statusText}`);
  return res.json();
}

export async function updateProfessorTags(professor_id: string, tags: string[]) {
  const url = apiUrl(`/professor/${professor_id}/tags`);
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tags }),
  });
  if (!res.ok) throw new Error(`Failed to update tags: ${res.status} ${res.statusText}`);
  return res.json();
}

export async function suggestClasses(query: string, limit = 8): Promise<string[]> {
  const q = query.trim();
  if (!q) return [];
  const url = apiUrl(`/suggest/classes?q=${encodeURIComponent(q)}&limit=${limit}`);
  const res = await fetch(url, { method: "GET" });
  if (!res.ok) return [];
  const data = (await res.json()) as { results?: string[] };
  return Array.isArray(data.results) ? data.results : [];
}

export async function suggestProfessors(query: string, limit = 8): Promise<string[]> {
  const q = query.trim();
  if (!q) return [];
  const url = apiUrl(`/suggest/professors?q=${encodeURIComponent(q)}&limit=${limit}`);
  const res = await fetch(url, { method: "GET" });
  if (!res.ok) return [];
  const data = (await res.json()) as { results?: string[] };
  return Array.isArray(data.results) ? data.results : [];
}

/** Upload a transcript PDF and return the parsed audit data. */
export async function uploadTranscript(file: File) {
  const formData = new FormData();
  formData.append('file', file);
  const res = await axios.post(apiUrl("/upload/transcript"), formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    withCredentials: true
  });
  return res.data;
}
