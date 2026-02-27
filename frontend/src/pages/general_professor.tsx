import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { getClass, getProfessor } from '../api';

type GradeDist = Record<string, number>;

const DETAILED_GRADES = ['AP', 'A', 'AM', 'BP', 'B', 'BM', 'CP', 'C', 'CM', 'DP', 'D', 'DM', 'F'] as const;
const CLEAN_GRADES = ['A', 'B', 'C', 'D', 'F'] as const;

type ProfessorData = {
  professor?: string;
  professor_name?: string;
  total_students?: number;
  courses_taught_count?: number;
  courses_taught?: string;
  avg_gpa?: number;
  gradeDistribution?: GradeDist;
  stats?: {
    averageGrade?: number;
    totalStudents?: number;
  };
};

type CourseData = {
  course_id?: string;
  stats?: {
    averageGrade?: number;
    totalStudents?: number;
  };
};

type CourseStat = {
  courseId: string;
  avg: number;
  totalStudents: number;
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

function parseCourses(raw?: string): string[] {
  if (!raw) return [];
  return raw
    .split(';')
    .map((item) => item.trim())
    .filter(Boolean);
}

export default function GeneralProfessor() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const initialQuery = searchParams.get('q') ?? '';

  const [professorName, setProfessorName] = useState(initialQuery);
  const [data, setData] = useState<ProfessorData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showDetailedGrades, setShowDetailedGrades] = useState(true);
  const [courseStats, setCourseStats] = useState<CourseStat[]>([]);

  const loadByValue = async (value: string) => {
    setError(null);
    setData(null);
    setCourseStats([]);

    const trimmed = value.trim();
    if (!trimmed) {
      setError('Please enter a professor name.');
      return;
    }

    setLoading(true);
    try {
      const json = (await getProfessor(trimmed)) as ProfessorData;
      setData(json);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  // const load = async () => {
  //   const trimmed = professorName.trim();
  //   if (trimmed) {
  //     setSearchParams({ q: trimmed });
  //   }
  //   await loadByValue(professorName);
  // };

  useEffect(() => {
    const q = searchParams.get('q');
    if (q) {
      setProfessorName(q);
      void loadByValue(q);
    }
    // only on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    let cancelled = false;

    const fetchCourseStats = async () => {
      if (!data) return;
      const courses = parseCourses(data.courses_taught);
      if (courses.length === 0) {
        setCourseStats([]);
        return;
      }

      const results = await Promise.all(
        courses.map(async (courseId) => {
          try {
            const response = (await getClass(courseId)) as CourseData;
            const avg = response.stats?.averageGrade;
            const totalStudents = response.stats?.totalStudents ?? 0;
            if (typeof avg !== 'number') return null;
            return { courseId: response.course_id ?? courseId, avg, totalStudents };
          } catch {
            return null;
          }
        }),
      );

      if (!cancelled) {
        setCourseStats(results.filter((r): r is CourseStat => r !== null));
      }
    };

    void fetchCourseStats();

    return () => {
      cancelled = true;
    };
  }, [data]);

  const displayName = data?.professor_name ?? data?.professor ?? professorName;
  const profAvg = data?.stats?.averageGrade ?? data?.avg_gpa ?? null;
  const profStudents = data?.stats?.totalStudents ?? data?.total_students ?? null;
  const rawDist = data?.gradeDistribution ?? null;
  const dist = rawDist ? (showDetailedGrades ? rawDist : collapseDistribution(rawDist)) : null;
  const gradeOrder = showDetailedGrades ? [...DETAILED_GRADES] : [...CLEAN_GRADES];
  const distTotal = dist ? gradeOrder.reduce((sum, grade) => sum + (dist[grade] ?? 0), 0) : 0;

  const departmentAvg = useMemo(() => {
    if (courseStats.length === 0) return null;
    const weightedSum = courseStats.reduce((sum, c) => sum + c.avg * Math.max(1, c.totalStudents), 0);
    const weights = courseStats.reduce((sum, c) => sum + Math.max(1, c.totalStudents), 0);
    return weights > 0 ? weightedSum / weights : null;
  }, [courseStats]);

  const courses = parseCourses(data?.courses_taught);

  return (
    <div style={{ padding: 16, maxWidth: 1200, margin: '0 auto' }}>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
        <button
          type="button"
          onClick={() => navigate('/search')}
          style={{ padding: '8px 12px', border: '1px solid #ccc', borderRadius: 8 }}
        >
          Back to Search
        </button>
        {/* <input
          value={professorName}
          onChange={(e) => setProfessorName(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') void load();
          }}
          placeholder="Enter professor name (e.g., Pat Holleran)"
          style={{ padding: '8px 10px', flex: '1 1 360px', minWidth: 240, borderRadius: 8, border: '1px solid #bbb' }}
        />
        <button onClick={load} style={{ padding: '8px 14px', borderRadius: 8 }} disabled={loading}>
          {loading ? 'Loading...' : 'Load'}
        </button> */}
      </div>

      {loading && <div style={{ marginTop: 12 }}>Loading...</div>}
      {error && <div style={{ marginTop: 12, color: 'crimson' }}>Error: {error}</div>}

      {data && (
        <div style={{ marginTop: 20, display: 'grid', gridTemplateColumns: '260px 1fr', gap: 16 }}>
          <aside style={{ border: '1px solid #ddd', borderRadius: 12, padding: 12, height: 'fit-content' }}>
            <div style={{ fontWeight: 700, marginBottom: 8 }}>Courses Taught</div>
            <div style={{ maxHeight: 460, overflowY: 'auto', display: 'grid', gap: 8, paddingRight: 4 }}>
              {courses.length === 0 && <div style={{ color: '#666', fontSize: 13 }}>No course list available.</div>}
              {courses.map((course) => (
                <button
                  key={course}
                  onClick={() => navigate(`/class?q=${encodeURIComponent(course)}`)}
                  style={{
                    textAlign: 'left',
                    border: '1px solid #ccc',
                    borderRadius: 8,
                    padding: '8px 10px',
                    background: '#fff',
                  }}
                >
                  {course}
                </button>
              ))}
            </div>
          </aside>

          <section style={{ display: 'grid', gap: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
              <div>
                <div style={{ fontWeight: 700, fontSize: 26 }}>{displayName || 'Professor Result'}</div>
                {typeof profStudents === 'number' && (
                  <div style={{ color: '#666', marginTop: 2 }}>Total students: {profStudents.toLocaleString()}</div>
                )}
              </div>

              <button
                onClick={() => setShowDetailedGrades((s) => !s)}
                style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid #ccc' }}
              >
                {showDetailedGrades ? 'Clean view (hide +/-)' : 'Detailed view (show +/-)'}
              </button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(220px, 1fr))', gap: 12 }}>
              <div style={{ border: '1px solid #ddd', borderRadius: 12, padding: 14 }}>
                <div style={{ fontSize: 12, color: '#666', textTransform: 'uppercase' }}>Professor AVG GPA</div>
                <div style={{ fontSize: 42, fontWeight: 700 }}>{typeof profAvg === 'number' ? profAvg.toFixed(3) : 'N/A'}</div>
              </div>
              <div style={{ border: '1px solid #ddd', borderRadius: 12, padding: 14 }}>
                <div style={{ fontSize: 12, color: '#666', textTransform: 'uppercase' }}>Department AVG GPA (courses taught)</div>
                <div style={{ fontSize: 42, fontWeight: 700 }}>{typeof departmentAvg === 'number' ? departmentAvg.toFixed(3) : 'N/A'}</div>
              </div>
            </div>

            <div style={{ border: '1px solid #ddd', borderRadius: 12, padding: 16 }}>
              <div style={{ fontWeight: 600, marginBottom: 10 }}>Professor vs Department/Course GPA Comparison</div>
              <div style={{ display: 'grid', gap: 8 }}>
                {typeof profAvg === 'number' && (
                  <div style={{ display: 'grid', gridTemplateColumns: '180px 1fr 60px', gap: 10, alignItems: 'center' }}>
                    <div style={{ fontWeight: 600 }}>Professor</div>
                    <div style={{ background: '#e5e7eb', height: 12, borderRadius: 999 }}>
                      <div
                        style={{
                          width: `${(profAvg / 4) * 100}%`,
                          height: '100%',
                          borderRadius: 999,
                          background: '#2563eb',
                        }}
                      />
                    </div>
                    <div>{profAvg.toFixed(2)}</div>
                  </div>
                )}
                {typeof departmentAvg === 'number' && (
                  <div style={{ display: 'grid', gridTemplateColumns: '180px 1fr 60px', gap: 10, alignItems: 'center' }}>
                    <div style={{ fontWeight: 600 }}>Department baseline</div>
                    <div style={{ background: '#e5e7eb', height: 12, borderRadius: 999 }}>
                      <div
                        style={{
                          width: `${(departmentAvg / 4) * 100}%`,
                          height: '100%',
                          borderRadius: 999,
                          background: '#475569',
                        }}
                      />
                    </div>
                    <div>{departmentAvg.toFixed(2)}</div>
                  </div>
                )}
                {courseStats.slice(0, 12).map((course) => (
                  <div key={course.courseId} style={{ display: 'grid', gridTemplateColumns: '180px 1fr 60px', gap: 10, alignItems: 'center' }}>
                    <button
                      onClick={() => navigate(`/class?q=${encodeURIComponent(course.courseId)}`)}
                      style={{
                        textAlign: 'left',
                        border: 'none',
                        background: 'transparent',
                        color: '#2563eb',
                        padding: 0,
                        cursor: 'pointer',
                      }}
                    >
                      {course.courseId}
                    </button>
                    <div style={{ background: '#e5e7eb', height: 12, borderRadius: 999 }}>
                      <div
                        style={{
                          width: `${(course.avg / 4) * 100}%`,
                          height: '100%',
                          borderRadius: 999,
                          background: '#10b981',
                        }}
                      />
                    </div>
                    <div>{course.avg.toFixed(2)}</div>
                  </div>
                ))}
              </div>
            </div>

            <div style={{ border: '1px solid #ddd', borderRadius: 12, padding: 16 }}>
              <div style={{ fontWeight: 600, marginBottom: 10 }}>Professor Grade Distribution (Stacked)</div>
              {dist ? (
                <>
                  <div style={{ display: 'flex', height: 30, borderRadius: 8, overflow: 'hidden', border: '1px solid #d1d5db' }}>
                    {gradeOrder.map((grade, idx) => {
                      const count = dist[grade] ?? 0;
                      const width = distTotal > 0 ? (count / distTotal) * 100 : 0;
                      const colors = ['#1d4ed8', '#2563eb', '#3b82f6', '#0ea5e9', '#06b6d4', '#14b8a6', '#10b981', '#22c55e', '#84cc16', '#eab308', '#f59e0b', '#f97316', '#ef4444'];
                      return (
                        <div key={grade} title={`${grade}: ${count}`} style={{ width: `${width}%`, background: colors[idx % colors.length] }} />
                      );
                    })}
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: `repeat(${gradeOrder.length}, minmax(24px, 1fr))`, gap: 6, marginTop: 10 }}>
                    {gradeOrder.map((grade) => {
                      const count = dist[grade] ?? 0;
                      const pct = distTotal > 0 ? (count / distTotal) * 100 : 0;
                      return (
                        <div key={grade} style={{ textAlign: 'center', fontSize: 12 }}>
                          <div style={{ fontWeight: 600 }}>{grade}</div>
                          <div>{Math.round(pct)}%</div>
                        </div>
                      );
                    })}
                  </div>
                </>
              ) : (
                <div style={{ color: '#666' }}>No distribution data available.</div>
              )}
            </div>

            <details>
              <summary style={{ cursor: 'pointer' }}>Raw response</summary>
              <pre style={{ whiteSpace: 'pre-wrap', marginTop: 8, fontSize: 12 }}>{JSON.stringify(data, null, 2)}</pre>
            </details>
          </section>
        </div>
      )}
    </div>
  );
}
