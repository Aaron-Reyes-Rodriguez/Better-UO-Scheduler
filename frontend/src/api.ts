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
  const res = await fetch(apiUrl("/audit/cs"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ taken_attempts: takenAttempts }),
  });
  if (!res.ok) throw new Error(`Audit failed: ${res.status}`);
  return res.json();
}
