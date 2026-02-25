import { type ChangeEvent, useState } from "react"
import axios from 'axios';
import { useNavigate } from "react-router-dom";

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
    credentials: "include", //added wwwwwww
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

export async function getTranscriptData() {
  const url = apiUrl(`/transcriptData`);
  const res = await fetch(url, { 
    method: "GET",
    credentials: "include"
  });
  if (!res.ok) throw new Error(`File Not Found/Wrong File: ${res.status} ${res.statusText}`);
  return res.json();
}

//Upload File API
type UploadStatus = "idle" | 'uploading' | 'success' | 'error'

export default function FileUploader()
{
    const [file, setFile] = useState<File | null>(null)
    const [status, setStatus] = useState<UploadStatus>("idle")
    const navigate = useNavigate()

    function handleFileChange(e: ChangeEvent<HTMLInputElement>) 
    {
        setStatus('idle')
        if (e.target.files) {
            setFile(e.target.files[0])
        }
    }

    async function handleFileUpload()
    {
        if (!file) return
        setStatus("uploading")

        const formData = new FormData()
        formData.append('file', file)

        try {
            await axios.post(apiUrl("/upload/transcript"), formData, {
              headers: { 'Content-Type': 'multipart/form-data' },
              withCredentials: true
        })
            setStatus('success')
            navigate("/transcriptdata")
        } catch {
            setStatus('error')
        }
    }
    
    return (
        <div>
            <input type="file" accept=".pdf" onChange={handleFileChange}/>
            {file && (
                <div>
                    <p>File Name: {file.name}</p>
                    <p>Size: {(file.size/1024).toFixed(2)} KB</p>
                    <p>Type: {file.type}</p>
                </div>
            )}
            {file && status !== "uploading" && status !== "success" && (
                <button onClick={handleFileUpload}>Upload</button>
            )}
            {status === 'uploading' && <p>Uploading...</p>}
            {status === 'success' && <p className="text-green-600">Upload Successful!</p>}
            {status === 'error' && <p className="text-red-600">Upload Failed. Please try again.</p>}
        </div>
    )
}