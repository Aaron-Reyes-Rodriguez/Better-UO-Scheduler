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