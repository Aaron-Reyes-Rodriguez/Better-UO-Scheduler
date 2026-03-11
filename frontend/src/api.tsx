/**
 * @file api.tsx
 * @description Centralised HTTP client for the Quackademics (Better-UO-Scheduler)
 *   frontend. Exports typed wrapper functions that call the FastAPI backend.
 *   This is the single source of truth for API base-URL resolution and all
 *   fetch/axios calls from the React application.
 * @authors Aaron Reyes-Rodriguez
 *
 * System: Better-UO-Scheduler (Quackademics)
 *   This module is imported by any React page or component that needs to
 *   communicate with the backend. It reads the VITE_API_URL environment
 *   variable to support both local development and production (Amplify + Render)
 *   deployments without code changes.
 */

// axios: promise-based HTTP client used for multipart/form-data uploads
// (the built-in fetch API does not handle FormData progress events as cleanly).
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

/**
 * Construct a fully-qualified backend URL by prepending the resolved API base
 * to any relative path, ensuring exactly one slash between them.
 *
 * @param path - Relative URL path (e.g. "/class/CS210" or "health").
 * @returns Absolute URL string ready for use in a fetch or axios call.
 */
export function apiUrl(path: string): string {
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${API_BASE}${p}`;
}

/**
 * POST a list of course attempts to the /audit/cs endpoint and return the
 * degree-audit result for the CS major.
 *
 * @param takenAttempts - Array of course-attempt objects. Each object must
 *   include attempt_id, course_id, credits_taken, and grading_basis, with
 *   optional term and subtitle fields.
 * @returns Promise resolving to the audit result JSON from the backend.
 * @throws Error if the HTTP response is not 2xx.
 */
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

/** Fetch with clearer errors for CORS, network, and timeouts.
 * @returns Promise resolving to {status: "ok"} when the backend is reachable.
 * @throws Error with a human-readable message for CORS failures, network errors,
 *   or non-2xx HTTP responses.
 */
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

/**
 * Fetch grade-distribution and statistics for a single class from the backend.
 *
 * @param class_id - Course identifier string (e.g. "CS210" or "CS 210").
 * @returns Promise resolving to the class data JSON object.
 * @throws Error if the class is not found or the request fails.
 */
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

// Fetch a list of professors who taught the given class.
export async function getClassProfessors(class_id: string, limit = 50): Promise<string[]> {
  const url = apiUrl(`/class/${encodeURIComponent(class_id)}/professors?limit=${limit}`);
  const res = await fetch(url, { method: "GET" });
  if (!res.ok) return [];
  const data = (await res.json()) as { results?: string[] };
  return Array.isArray(data.results) ? data.results : [];
}

/**
 * POST tag votes for a professor to the backend, incrementing their counts.
 *
 * @param professor_id - The professor's identifier or display name.
 * @param tags - Array of tag display-name strings to vote for
 *   (e.g. ["Tough Grader", "Caring"]).
 * @returns Promise resolving to {status, tags} where tags is the updated list.
 * @throws Error if the request fails or the professor is not found.
 */
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

/**
 * Fetch course name suggestions from the backend for typeahead autocomplete.
 *
 * @param query - Partial course name or ID typed by the user.
 * @param limit - Maximum number of suggestions to return (default 8).
 * @returns Promise resolving to an array of matching course name strings.
 */
export async function suggestClasses(query: string, limit = 8): Promise<string[]> {
  const q = query.trim();
  if (!q) return [];
  const url = apiUrl(`/suggest/classes?q=${encodeURIComponent(q)}&limit=${limit}`);
  const res = await fetch(url, { method: "GET" });
  if (!res.ok) return [];
  const data = (await res.json()) as { results?: string[] };
  return Array.isArray(data.results) ? data.results : [];
}

/**
 * Fetch professor name suggestions from the backend for typeahead autocomplete.
 *
 * @param query - Partial professor name typed by the user.
 * @param limit - Maximum number of suggestions to return (default 8).
 * @returns Promise resolving to an array of matching professor name strings.
 */
export async function suggestProfessors(query: string, limit = 8): Promise<string[]> {
  const q = query.trim();
  if (!q) return [];
  const url = apiUrl(`/suggest/professors?q=${encodeURIComponent(q)}&limit=${limit}`);
  const res = await fetch(url, { method: "GET" });
  if (!res.ok) return [];
  const data = (await res.json()) as { results?: string[] };
  return Array.isArray(data.results) ? data.results : [];
}

/** Upload a transcript PDF and return the parsed audit data.
 * @param file - A PDF File object selected by the user via the file input.
 * @returns Promise resolving to the full audit result JSON from the backend,
 *   including broad_data, taken_attempts, class_grades, and degree-audit output.
 * @throws Error (axios) if the upload fails or the backend returns an error.
 */
export async function uploadTranscript(file: File) {
  const formData = new FormData();
  formData.append('file', file);
  const res = await axios.post(apiUrl("/upload/transcript"), formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    withCredentials: true
  });
  return res.data;
}

/** Re-run the degree audit with user-selected tracks/domains. */
export async function reAudit(
  parsedData: Record<string, unknown>,
  selections: Record<string, string>,
) {
  const res = await axios.post(
    apiUrl("/re-audit"),
    { parsedData, selections },
    { withCredentials: true },
  );
  return res.data;
}
