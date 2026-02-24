import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';

type SearchType = 'class' | 'professor';

export default function Search() {
  const navigate = useNavigate();
  const [searchType, setSearchType] = useState<SearchType>('class');
  const [query, setQuery] = useState('');

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) return;

    const path = searchType === 'class' ? '/class' : '/professor';
    navigate(`${path}?q=${encodeURIComponent(trimmed)}`);
  };

  return (
    <div className="p-4" style={{ maxWidth: 760 }}>
      <h1 className="text-2xl font-bold">Search</h1>
      <p className="mt-2">Search by course or professor name.</p>

      <form onSubmit={onSubmit} style={{ marginTop: 16, display: 'grid', gap: 12 }}>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button
            type="button"
            onClick={() => setSearchType('class')}
            style={{
              padding: '8px 12px',
              border: '1px solid #ccc',
              borderRadius: 6,
              background: searchType === 'class' ? '#eef4ff' : '#fff',
              fontWeight: searchType === 'class' ? 600 : 400,
            }}
          >
            Class
          </button>
          <button
            type="button"
            onClick={() => setSearchType('professor')}
            style={{
              padding: '8px 12px',
              border: '1px solid #ccc',
              borderRadius: 6,
              background: searchType === 'professor' ? '#eef4ff' : '#fff',
              fontWeight: searchType === 'professor' ? 600 : 400,
            }}
          >
            Professor
          </button>
        </div>

        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={searchType === 'class' ? 'e.g. CS 110' : 'e.g. Hennessy, Michael Shane'}
          style={{ padding: '10px 12px', border: '1px solid #ccc', borderRadius: 6 }}
        />

        <div>
          <button
            type="submit"
            disabled={!query.trim()}
            style={{ padding: '8px 14px', border: '1px solid #ccc', borderRadius: 6 }}
          >
            Search
          </button>
        </div>
      </form>
    </div>
  );
}

