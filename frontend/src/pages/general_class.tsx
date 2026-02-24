import { useEffect, useState, type CSSProperties } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { getClass } from '../api';

type GradeDist = Record<string, number>;
const GRADE_ORDER = ['AP', 'A', 'AM', 'BP', 'B', 'BM', 'CP', 'C', 'CM', 'DP', 'D', 'DM', 'F'];

type CourseData = {
  course_id?: string;
  total_students?: number;
  avg_gpa?: number;
  gradeDistribution?: GradeDist;
  [key: string]: unknown;
};

export default function GeneralClass() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const initialQuery = searchParams.get('q') ?? '';

  const [courseKey, setCourseKey] = useState(initialQuery);
  const [data, setData] = useState<CourseData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadByValue = async (value: string) => {
    setError(null);
    setData(null);

    const trimmed = value.trim();
    if (!trimmed) {
      setError('Please enter a course key (e.g., "CS 110").');
      return;
    }

    setLoading(true);
    try {
      const json = (await getClass(trimmed)) as CourseData;
      setData(json);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const load = async () => {
    const trimmed = courseKey.trim();
    if (trimmed) {
      setSearchParams({ q: trimmed });
    }
    await loadByValue(courseKey);
  };

  useEffect(() => {
    const q = searchParams.get('q');
    if (q) {
      setCourseKey(q);
      void loadByValue(q);
    }
    // only on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const tableStyle: CSSProperties = {
    borderCollapse: 'collapse',
    width: '100%',
    maxWidth: 700,
    marginTop: 12,
  };

  const thTdStyle: CSSProperties = {
    border: '1px solid #ddd',
    padding: '6px 8px',
    textAlign: 'left',
  };

  return (
    <div className="p-4">
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
        <button
          type="button"
          onClick={() => navigate('/search')}
          style={{ padding: '6px 10px', border: '1px solid #ccc', borderRadius: 6 }}
        >
          Back to Search
        </button>
        <input
          value={courseKey}
          onChange={(e) => setCourseKey(e.target.value)}
          placeholder="Enter course key (e.g., CS 110)"
          style={{ padding: 6, flex: '1 1 320px', minWidth: 240 }}
        />
        <button onClick={load} style={{ padding: '6px 12px' }} disabled={loading}>
          {loading ? 'Loading...' : 'Load'}
        </button>
      </div>

      {loading && <div style={{ marginTop: 12 }}>Loading...</div>}
      {error && <div style={{ marginTop: 12, color: 'crimson' }}>Error: {error}</div>}

      {data && (
        <div style={{ marginTop: 16 }}>
          <div style={{ fontWeight: 600 }}>{data.course_id ?? (courseKey || 'Course Result')}</div>
          {typeof data.total_students === 'number' && (
            <div style={{ color: '#555', marginTop: 4 }}>Total students: {data.total_students}</div>
          )}
          {typeof data.avg_gpa === 'number' && (
            <div style={{ color: '#555', marginTop: 4 }}>Avg GPA: {data.avg_gpa.toFixed(3)}</div>
          )}

          {data.gradeDistribution && (
            <table style={tableStyle}>
              <thead>
                <tr>
                  <th style={thTdStyle}>Grade</th>
                  <th style={thTdStyle}>Count</th>
                </tr>
              </thead>
              <tbody>
                {GRADE_ORDER.map((g) => (
                  <tr key={g}>
                    <td style={thTdStyle}>{g}</td>
                    <td style={thTdStyle}>{data.gradeDistribution?.[g] ?? 0}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          <details style={{ marginTop: 12 }}>
            <summary>Raw response</summary>
            <pre style={{ whiteSpace: 'pre-wrap', marginTop: 8 }}>{JSON.stringify(data, null, 2)}</pre>
          </details>
        </div>
      )}
    </div>
  );
}

