import { useEffect, useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { suggestClasses, suggestProfessors } from '../api';

type SearchType = 'class' | 'professor';

export default function Search() {
  const navigate = useNavigate();
  const [searchType, setSearchType] = useState<SearchType>('class');
  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [activeIndex, setActiveIndex] = useState(-1);

  const goToResult = (value: string) => {
    const path = searchType === 'class' ? '/class' : '/professor';
    navigate(`${path}?q=${encodeURIComponent(value)}`);
  };

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) return;
    goToResult(trimmed);
  };

  useEffect(() => {
    let cancelled = false;
    const q = query.trim();
    if (!q) {
      setSuggestions([]);
      setActiveIndex(-1);
      return;
    }

    const timer = setTimeout(async () => {
      const results = searchType === 'class' ? await suggestClasses(q, 8) : await suggestProfessors(q, 8);
      if (!cancelled) {
        setSuggestions(results);
        setActiveIndex(results.length > 0 ? 0 : -1);
      }
    }, 120);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [query, searchType]);

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

        <div style={{ position: 'relative' }}>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (suggestions.length === 0) return;
              if (e.key === 'ArrowDown') {
                e.preventDefault();
                setActiveIndex((i) => (i + 1) % suggestions.length);
              } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                setActiveIndex((i) => (i - 1 + suggestions.length) % suggestions.length);
              } else if (e.key === 'Enter' && activeIndex >= 0 && activeIndex < suggestions.length) {
                e.preventDefault();
                const value = suggestions[activeIndex];
                setQuery(value);
                goToResult(value);
              }
            }}
            placeholder={searchType === 'class' ? 'e.g. CS 110' : 'e.g. Pat Holleran'}
            style={{ width: '100%', padding: '10px 12px', border: '1px solid #ccc', borderRadius: 6 }}
          />

          {suggestions.length > 0 && (
            <div
              style={{
                position: 'absolute',
                zIndex: 20,
                top: 'calc(100% + 4px)',
                left: 0,
                right: 0,
                border: '1px solid #d1d5db',
                borderRadius: 8,
                background: '#fff',
                maxHeight: 260,
                overflowY: 'auto',
                boxShadow: '0 6px 20px rgba(0,0,0,0.12)',
              }}
            >
              {suggestions.map((item, idx) => (
                <button
                  key={`${item}-${idx}`}
                  type="button"
                  onMouseDown={(e) => {
                    e.preventDefault();
                    setQuery(item);
                    goToResult(item);
                  }}
                  style={{
                    display: 'block',
                    width: '100%',
                    textAlign: 'left',
                    border: 'none',
                    borderBottom: idx === suggestions.length - 1 ? 'none' : '1px solid #f1f5f9',
                    borderRadius: 0,
                    padding: '9px 12px',
                    background: idx === activeIndex ? '#eef4ff' : '#fff',
                    color: '#111827',
                    cursor: 'pointer',
                  }}
                >
                  {item}
                </button>
              ))}
            </div>
          )}
        </div>

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
