/**
 * @file ProfessorTags.tsx
 * @description Student-voting tags component for professor detail pages in
 *   Quackademics (Better-UO-Scheduler). Displays current tag vote counts and
 *   provides a modal for eligible users (those who have uploaded a transcript)
 *   to vote on Rate-My-Professor-style descriptive tags for a professor.
 * @authors Aaron Reyes-Rodriguez
 *
 * System: Better-UO-Scheduler (Quackademics)
 *   Rendered inside the professor detail page (general_professor.tsx). Tag
 *   votes are persisted in the PostgreSQL professor_tags table via the
 *   updateProfessorTags API call. Only users who have uploaded a transcript
 *   (flagged in localStorage) are allowed to add or vote on tags.
 */

// useState: React hook for managing modal open/close, pending selections,
// saving state, and error messages.
import { useState } from 'react';
// updateProfessorTags: API helper that POSTs tag votes to the backend.
import { updateProfessorTags } from '../../api';

// Example tags adapted from Rate My Professor
const AVAILABLE_TAGS = [
  "Tough Grader",
  "Get Ready To Read",
  "Participation Matters",
  "Skip Class? You Won't Pass.",
  "Accessible Outside Class",
  "Caring",
  "Respected",
  "Lecture Heavy",
  "Test Heavy",
  "Graded by few things",
  "Amazing lectures",
  "Clear grading criteria",
  "Hilarious",
  "Inspirational",
  "Lots of homework"
];

/**
 * Shape of a tag with its current vote count, as returned by the backend.
 */
type TagWithCount = {
  name: string;
  count: number;
};

/**
 * Props accepted by the ProfessorTags component.
 *
 * @property professorId - The professor's canonical identifier used to POST
 *   tag votes to the correct backend endpoint.
 * @property initialTags - Pre-fetched list of tags with their vote counts,
 *   returned as part of the professor data from the GET /professor endpoint.
 */
interface ProfessorTagsProps {
  professorId: string;
  initialTags?: TagWithCount[];
}

/**
 * ProfessorTags – student-voting tags component.
 *
 * Displays the current set of tags (with vote counts) for a professor and,
 * for users who have uploaded a transcript, provides a modal dialog to select
 * and submit additional tag votes.
 *
 * @param professorId - The professor's identifier for the tags API endpoint.
 * @param initialTags - Initial tag list fetched alongside professor data.
 * @returns JSX element rendering the tag list and optional voting modal.
 */
export default function ProfessorTags({ professorId, initialTags = [] }: ProfessorTagsProps) {
  const [tags, setTags] = useState<TagWithCount[]>(initialTags || []);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [pendingTags, setPendingTags] = useState<string[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Check localStorage to determine if the current user is eligible to vote.
  const hasTranscript = localStorage.getItem('hasUploadedTranscript') === 'true';

  /**
   * Open the tag-selection modal, clearing any previously pending selections
   * and any error message from a prior save attempt.
   */
  const handleOpenModal = () => {
    setPendingTags([]);
    setIsModalOpen(true);
    setError(null);
  };

  /**
   * Toggle a tag in the pendingTags selection list. Selecting an already-
   * selected tag deselects it, and vice versa.
   *
   * @param tag - The display name of the tag to toggle.
   */
  const handleToggleTag = (tag: string) => {
    setPendingTags(prev => 
      prev.includes(tag) ? prev.filter(t => t !== tag) : [...prev, tag]
    );
  };

  /**
   * Submit the pending tag votes to the backend and update the displayed tag
   * list with the server response. Closes the modal on success; shows an error
   * message on failure.
   *
   * @returns Promise<void>
   */
  const handleSave = async () => {
    setIsSaving(true);
    setError(null);
    try {
      const response = await updateProfessorTags(professorId, pendingTags);
      setTags(response.tags || pendingTags.map(t => ({ name: t, count: 1 })));
      setIsModalOpen(false);
    } catch (err) {
      setError("Failed to save tags. Please try again.");
      console.error(err);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div style={{ marginTop: '20px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
        <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600 }}>Student Tags</h3>
        <button
          onClick={handleOpenModal}
          disabled={!hasTranscript}
          title={!hasTranscript ? 'Upload a transcript first to vote on tags' : undefined}
          style={{
            padding: '4px 12px',
            backgroundColor: hasTranscript ? '#f1f5f9' : '#f1f5f9',
            border: '1px solid #cbd5e1',
            borderRadius: '999px',
            fontSize: '0.85rem',
            cursor: hasTranscript ? 'pointer' : 'not-allowed',
            fontWeight: 500,
            color: hasTranscript ? '#334155' : '#94a3b8',
            transition: 'background-color 0.2s',
            opacity: hasTranscript ? 1 : 0.6,
          }}
          onMouseOver={e => { if (hasTranscript) e.currentTarget.style.backgroundColor = '#e2e8f0'; }}
          onMouseOut={e => { if (hasTranscript) e.currentTarget.style.backgroundColor = '#f1f5f9'; }}
        >
          {tags.length > 0 ? 'Vote Tags' : 'Add Tags'}
        </button>
        {!hasTranscript && (
          <span style={{ fontSize: '0.8rem', color: '#94a3b8', fontStyle: 'italic' }}>
            Upload a transcript to vote
          </span>
        )}
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
        {tags.length > 0 ? (
          tags.map(tag => (
            <span
              key={tag.name}
              style={{
                backgroundColor: '#e0f2fe',
                color: '#0369a1',
                padding: '4px 12px',
                borderRadius: '999px',
                fontSize: '0.85rem',
                fontWeight: 500,
                border: '1px solid #bae6fd',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              {tag.name}
              <span style={{
                backgroundColor: '#0284c7',
                color: 'white',
                borderRadius: '999px',
                padding: '1px 7px',
                fontSize: '0.75rem',
                fontWeight: 700,
                minWidth: '20px',
                textAlign: 'center'
              }}>
                {tag.count}
              </span>
            </span>
          ))
        ) : (
          <span style={{ color: '#64748b', fontSize: '0.9rem', fontStyle: 'italic' }}>
            No tags yet. Be the first to add one!
          </span>
        )}
      </div>

      {isModalOpen && (
        <div style={{
          position: 'fixed',
          top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.5)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          zIndex: 1000,
          padding: '20px'
        }}>
          <div style={{
            backgroundColor: 'white',
            borderRadius: '12px',
            padding: '24px',
            width: '100%',
            maxWidth: '500px',
            maxHeight: '90vh',
            display: 'flex',
            flexDirection: 'column',
            boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)'
          }}>
            <h2 style={{ margin: '0 0 16px 0', fontSize: '1.25rem', fontWeight: 600 }}>Select Tags for {professorId}</h2>
            
            {error && <div style={{ color: '#ef4444', marginBottom: '12px', fontSize: '0.9rem' }}>{error}</div>}
            
            <div style={{
              overflowY: 'auto',
              display: 'flex',
              flexWrap: 'wrap',
              gap: '8px',
              paddingBottom: '20px',
              flex: 1
            }}>
              {AVAILABLE_TAGS.map(tag => {
                const isSelected = pendingTags.includes(tag);
                return (
                  <button
                    key={tag}
                    onClick={() => handleToggleTag(tag)}
                    style={{
                      padding: '6px 14px',
                      borderRadius: '999px',
                      fontSize: '0.9rem',
                      cursor: 'pointer',
                      border: isSelected ? '1px solid #0284c7' : '1px solid #cbd5e1',
                      backgroundColor: isSelected ? '#bae6fd' : '#f8fafc',
                      color: isSelected ? '#0369a1' : '#334155',
                      fontWeight: isSelected ? 600 : 400,
                      transition: 'all 0.15s'
                    }}
                  >
                    {tag}
                  </button>
                );
              })}
            </div>
            
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '16px', paddingTop: '16px', borderTop: '1px solid #e2e8f0' }}>
              <button
                onClick={() => setIsModalOpen(false)}
                disabled={isSaving}
                style={{
                  padding: '8px 16px',
                  backgroundColor: 'white',
                  border: '1px solid #cbd5e1',
                  borderRadius: '6px',
                  cursor: isSaving ? 'not-allowed' : 'pointer',
                  fontWeight: 500,
                  opacity: isSaving ? 0.5 : 1
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={isSaving}
                style={{
                  padding: '8px 24px',
                  backgroundColor: '#0ea5e9',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: isSaving ? 'not-allowed' : 'pointer',
                  fontWeight: 600,
                  opacity: isSaving ? 0.5 : 1
                }}
              >
                {isSaving ? 'Saving...' : 'Done'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
