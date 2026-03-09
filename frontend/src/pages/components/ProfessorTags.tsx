import { useState } from 'react';
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

type TagWithCount = {
  name: string;
  count: number;
};

interface ProfessorTagsProps {
  professorId: string;
  initialTags?: TagWithCount[];
}

export default function ProfessorTags({ professorId, initialTags = [] }: ProfessorTagsProps) {
  const [tags, setTags] = useState<TagWithCount[]>(initialTags || []);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [pendingTags, setPendingTags] = useState<string[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const hasTranscript = sessionStorage.getItem('hasUploadedTranscript') === 'true';

  const handleOpenModal = () => {
    setPendingTags([]);
    setIsModalOpen(true);
    setError(null);
  };

  const handleToggleTag = (tag: string) => {
    setPendingTags(prev => 
      prev.includes(tag) ? prev.filter(t => t !== tag) : [...prev, tag]
    );
  };

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
