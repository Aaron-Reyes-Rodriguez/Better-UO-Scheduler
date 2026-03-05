import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { getClass } from '../api';

type GradeDist = Record<string, number>;

const DETAILED_GRADES = ['AP', 'A', 'AM', 'BP', 'B', 'BM', 'CP', 'C', 'CM', 'DP', 'D', 'DM', 'F'] as const;
const CLEAN_GRADES = ['A', 'B', 'C', 'D', 'F'] as const;

type CourseData = {
  course_id?: string;
  total_students?: number;
  avg_gpa?: number;
  gradeDistribution?: GradeDist;
  stats?: {
    averageGrade?: number;
    totalStudents?: number;
  };
};

function collapseDistribution(dist: GradeDist): GradeDist {
  return {
    A: (dist.AP ?? 0) + (dist.A ?? 0) + (dist.AM ?? 0),
    B: (dist.BP ?? 0) + (dist.B ?? 0) + (dist.BM ?? 0),
    C: (dist.CP ?? 0) + (dist.C ?? 0) + (dist.CM ?? 0),
    D: (dist.DP ?? 0) + (dist.D ?? 0) + (dist.DM ?? 0),
    F: dist.F ?? 0,
  };
}

export default function GeneralClass() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const initialQuery = searchParams.get('q') ?? '';

  const [courseKey, setCourseKey] = useState(initialQuery);
  const [data, setData] = useState<CourseData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showDetailedGrades, setShowDetailedGrades] = useState(true);

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

  const avgGpa = data?.stats?.averageGrade ?? data?.avg_gpa ?? null;
  const totalStudents = data?.total_students ?? data?.stats?.totalStudents ?? null;
  const rawDist = data?.gradeDistribution ?? null;
  const dist = rawDist ? (showDetailedGrades ? rawDist : collapseDistribution(rawDist)) : null;
  const gradeOrder = showDetailedGrades ? [...DETAILED_GRADES] : [...CLEAN_GRADES];
  const distTotal = dist ? gradeOrder.reduce((sum, grade) => sum + (dist[grade] ?? 0), 0) : 0;

  return (
    <div style={{ padding: 16, maxWidth: 1080, margin: '0 auto' }}>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
        <button
          type="button"
          onClick={() => navigate('/search')}
          style={{ padding: '8px 12px', border: '1px solid #ccc', borderRadius: 8 }}
        >
          Back to Search
        </button>
        <input
          value={courseKey}
          onChange={(e) => setCourseKey(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') void load();
          }}
          placeholder="Enter course key (e.g., CS 110)"
          style={{ padding: '8px 10px', flex: '1 1 320px', minWidth: 240, borderRadius: 8, border: '1px solid #bbb' }}
        />
        <button onClick={load} style={{ padding: '8px 14px', borderRadius: 8 }} disabled={loading}>
          {loading ? 'Loading...' : 'Load'}
        </button>
      </div>

      {loading && <div style={{ marginTop: 12 }}>Loading...</div>}
      {error && <div style={{ marginTop: 12, color: 'crimson' }}>Error: {error}</div>}

      {data && (
        <div style={{ marginTop: 20, display: 'grid', gap: 18 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
            <div>
              <div style={{ fontWeight: 700, fontSize: 26 }}>{data.course_id ?? (courseKey || 'Course Result')}</div>
              {typeof totalStudents === 'number' && (
                <div style={{ color: '#666', marginTop: 2 }}>Total students: {totalStudents.toLocaleString()}</div>
              )}
            </div>

            <button
              onClick={() => setShowDetailedGrades((s) => !s)}
              style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid #ccc' }}
            >
              {showDetailedGrades ? 'Clean view (hide +/-)' : 'Detailed view (show +/-)'}
            </button>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'minmax(220px, 280px) 1fr', gap: 16 }}>
            <div style={{ border: '1px solid #ddd', borderRadius: 12, padding: 16 }}>
              <div style={{ fontSize: 12, color: '#666', textTransform: 'uppercase', letterSpacing: 0.6 }}>AVG GPA</div>
              <div style={{ fontSize: 56, fontWeight: 700, lineHeight: 1.05, marginTop: 8 }}>
                {typeof avgGpa === 'number' ? avgGpa.toFixed(3) : 'N/A'}
              </div>
              <div style={{ marginTop: 12, height: 10, borderRadius: 999, background: '#e5e7eb', overflow: 'hidden' }}>
                <div
                  style={{
                    width: `${Math.max(0, Math.min(100, ((avgGpa ?? 0) / 4) * 100))}%`,
                    height: '100%',
                    background: 'linear-gradient(90deg, #22c55e 0%, #16a34a 100%)',
                  }}
                />
              </div>
              <div style={{ marginTop: 6, color: '#6b7280', fontSize: 12 }}>Scale: 0.0 to 4.0</div>
            </div>

            <div style={{ border: '1px solid #ddd', borderRadius: 12, padding: 16 }}>
              <div style={{ fontWeight: 600, marginBottom: 10 }}>Grade Distribution</div>
              {dist ? (
                <div style={{ display: 'grid', gridTemplateColumns: `repeat(${gradeOrder.length}, minmax(26px, 1fr))`, gap: 8, alignItems: 'end', minHeight: 220 }}>
                  {gradeOrder.map((grade) => {
                    const count = dist[grade] ?? 0;
                    const pct = distTotal > 0 ? (count / distTotal) * 100 : 0;
                    return (
                      <div key={grade} style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: 11, color: '#666', marginBottom: 6 }}>{Math.round(pct)}%</div>
                        <div
                          title={`${grade}: ${count}`}
                          style={{
                            height: `${Math.max(6, pct * 2)}px`,
                            borderRadius: 6,
                            background: grade === 'F' ? '#ef4444' : '#2563eb',
                            transition: 'height 180ms ease',
                          }}
                        />
                        <div style={{ fontSize: 12, fontWeight: 600, marginTop: 6 }}>{grade}</div>
                        <div style={{ fontSize: 12, color: '#555' }}>{count}</div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div style={{ color: '#666' }}>No distribution data available.</div>
              )}
            </div>
          </div>

          <div style={{ border: '1px solid #ddd', borderRadius: 12, padding: 16 }}>
            <div style={{ fontWeight: 600 }}>Grade Trend Over Time</div>
            <div style={{ color: '#666', marginTop: 6 }}>
              Trend data is not available in the current class endpoint yet. When term-level data is added, this chart can be enabled here.
            </div>
          </div>

          <details>
            <summary style={{ cursor: 'pointer' }}>Raw response</summary>
            <pre style={{ whiteSpace: 'pre-wrap', marginTop: 8, fontSize: 12 }}>{JSON.stringify(data, null, 2)}</pre>
          </details>
        </div>
      )}
    </div>
  );
}
