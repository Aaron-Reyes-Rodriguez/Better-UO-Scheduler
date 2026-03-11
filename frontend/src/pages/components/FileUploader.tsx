/**
 * @file FileUploader.tsx
 * @description PDF transcript file-selector and upload component for
 *   Quackademics (Better-UO-Scheduler). Handles the full file-selection to
 *   upload flow, persists audit results in localStorage, and navigates to the
 *   /audit page on success. If a transcript has already been uploaded it shows
 *   a summary state with options to view the saved audit or re-upload.
 * @authors Aaron Reyes-Rodriguez
 *
 * System: Better-UO-Scheduler (Quackademics)
 *   Rendered by scheduler.tsx inside the transcript upload page. After a
 *   successful upload it stores auditData and transcriptData in localStorage
 *   so that the audit results survive page refreshes.
 */

// React hooks and types for state management and change events.
import { type ChangeEvent, useState } from "react"
// useNavigate: React Router hook used to redirect to the audit page after upload.
import { useNavigate } from "react-router-dom"
// uploadTranscript: API helper that POSTs the PDF file to the backend.
import { uploadTranscript } from "../../api"

/** Union type for the current state of the file upload operation. */
type UploadStatus = "idle" | 'uploading' | 'success' | 'error'

/**
 * FileUploader – PDF transcript upload component.
 *
 * Renders either:
 *   a) An upload card (file picker + submit button + status feedback) when no
 *      transcript has been uploaded yet, or
 *   b) A "already uploaded" summary with links to view the saved audit or
 *      re-upload a new transcript.
 *
 * @returns JSX element representing the file uploader or the saved-state view.
 */
export default function FileUploader()
{
    const [file, setFile] = useState<File | null>(null)
    const [status, setStatus] = useState<UploadStatus>("idle")
    const [showUploader, setShowUploader] = useState(!localStorage.getItem("hasUploadedTranscript"))
    const navigate = useNavigate()

    /**
     * Update the selected file in state whenever the user picks a new file.
     * Also resets the upload status to "idle" to clear any previous error.
     *
     * @param e - The change event from the hidden file input element.
     */
    function handleFileChange(e: ChangeEvent<HTMLInputElement>) 
    {
        setStatus('idle')
        if (e.target.files) {
            setFile(e.target.files[0])
        }
    }

    /**
     * Upload the selected PDF file to the backend, persist the returned audit
     * data in localStorage, and navigate to the /audit page on success.
     * Sets status to "uploading" during the request and to "error" on failure.
     *
     * @returns Promise<void> - this function is async but its return value is
     *   not used by the parent component.
     */
    async function handleFileUpload()
    {
        if (!file) return
        setStatus("uploading")

        try {
            const data = await uploadTranscript(file)
            console.log(data)

            setStatus('success')
            
            // Persist data in localStorage so it survives across sessions
            localStorage.setItem("hasUploadedTranscript", "true");
            localStorage.setItem("auditData", JSON.stringify(data));
            localStorage.setItem("transcriptData", JSON.stringify(data));
            
            navigate("/audit", { state: { auditData: data } })
        } catch {
            setStatus('error')
        }
    }

    // If user already has transcript data, show a summary with re-upload option
    if (!showUploader) {
        return (
            <div style={{ textAlign: 'center', width: '100%' }}>
                <div style={{
                    padding: '16px',
                    backgroundColor: '#0f172a',
                    borderRadius: '8px',
                    border: '1px solid #334155',
                    marginBottom: '16px',
                }}>
                    <p style={{ margin: '0 0 4px 0', color: '#10b981', fontWeight: 'bold', fontSize: '0.95rem' }}>
                        ✓ Transcript already uploaded
                    </p>
                    <p style={{ margin: 0, color: '#94a3b8', fontSize: '0.85rem' }}>
                        Your transcript data is saved. You can view your audit or upload a new one.
                    </p>
                </div>
                <div style={{ display: 'flex', gap: '12px', justifyContent: 'center', flexWrap: 'wrap' }}>
                    <button
                        onClick={() => navigate("/audit")}
                        style={{
                            backgroundColor: '#2563eb',
                            color: 'white',
                            padding: '10px 24px',
                            borderRadius: '8px',
                            border: 'none',
                            fontSize: '0.95rem',
                            fontWeight: 600,
                            cursor: 'pointer',
                            transition: 'background-color 0.2s',
                        }}
                    >
                        View Saved Audit
                    </button>
                    <button
                        onClick={() => setShowUploader(true)}
                        style={{
                            backgroundColor: '#f9f9f9ff',
                            color: '#00060dff',
                            padding: '10px 24px',
                            borderRadius: '8px',
                            border: '1px solid #475569',
                            fontSize: '0.95rem',
                            fontWeight: 500,
                            cursor: 'pointer',
                            transition: 'all 0.2s',
                        }}
                    >
                        Upload New Transcript
                    </button>
                </div>
            </div>
        );
    }
    
    return (
        <div style={{ textAlign: 'center', width: '100%' }}>
            <input 
                type="file" 
                accept=".pdf" 
                id="file-upload-input"
                style={{ display: 'none' }}
                onChange={handleFileChange}
            />
            
            <label htmlFor="file-upload-input">
                <button 
                  type="button"
                  style={{
                    backgroundColor: file ? '#334155' : '#646cff',
                    color: 'white',
                    padding: '12px 24px',
                    borderRadius: '8px',
                    border: 'none',
                    fontSize: '1rem',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '8px',
                    margin: '0 auto',
                    transition: 'background-color 0.2s',
                  }}
                  onClick={() => document.getElementById('file-upload-input')?.click()}
                >
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                        <polyline points="17 8 12 3 7 8"></polyline>
                        <line x1="12" y1="3" x2="12" y2="15"></line>
                    </svg>
                    {file ? 'Change File' : 'Select PDF Transcript'}
                </button>
            </label>

            {file && (
                <div style={{ 
                    marginTop: '24px', 
                    padding: '16px', 
                    backgroundColor: '#0f172a', 
                    borderRadius: '8px',
                    textAlign: 'left',
                    border: '1px solid #334155'
                }}>
                    <p style={{ margin: '0 0 8px 0', color: '#f8fafc', fontWeight: 'bold' }}>Selected File:</p>
                    <p style={{ margin: '0 0 4px 0', color: '#94a3b8', fontSize: '0.9rem' }}>Name: {file.name}</p>
                    <p style={{ margin: '0', color: '#94a3b8', fontSize: '0.9rem' }}>Size: {(file.size/1024).toFixed(2)} KB</p>
                </div>
            )}
            
            {file && status !== "uploading" && status !== "success" && (
                <button 
                    onClick={handleFileUpload}
                    style={{
                        marginTop: '24px',
                        backgroundColor: '#10b981',
                        color: 'white',
                        padding: '12px 32px',
                        borderRadius: '8px',
                        border: 'none',
                        fontSize: '1.1rem',
                        fontWeight: 'bold',
                        cursor: 'pointer',
                        width: '100%',
                        transition: 'background-color 0.2s',
                    }}
                >
                    Upload and Analyze Transcript
                </button>
            )}
            
            {status === 'uploading' && (
                <div style={{ marginTop: '24px', color: '#38bdf8', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px' }}>
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ animation: 'spin 1s linear infinite' }}>
                        <line x1="12" y1="2" x2="12" y2="6"></line>
                        <line x1="12" y1="18" x2="12" y2="22"></line>
                        <line x1="4.93" y1="4.93" x2="7.76" y2="7.76"></line>
                        <line x1="16.24" y1="16.24" x2="19.07" y2="19.07"></line>
                        <line x1="2" y1="12" x2="6" y2="12"></line>
                        <line x1="18" y1="12" x2="22" y2="12"></line>
                        <line x1="4.93" y1="19.07" x2="7.76" y2="16.24"></line>
                        <line x1="16.24" y1="7.76" x2="19.07" y2="4.93"></line>
                    </svg>
                    <style>{`@keyframes spin { 100% { transform: rotate(360deg); } }`}</style>
                    <p style={{ margin: 0 }}>Processing PDF...</p>
                </div>
            )}
            
            {status === 'success' && (
                <p style={{ marginTop: '24px', color: '#10b981', fontWeight: 'bold' }}>
                    Upload Successful! Redirecting...
                </p>
            )}
            
            {status === 'error' && (
                <p style={{ marginTop: '24px', color: '#ef4444', fontWeight: 'bold' }}>
                    Upload Failed. Please try again.
                </p>
            )}
        </div>
    )
}
