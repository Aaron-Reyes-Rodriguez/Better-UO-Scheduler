import { useState } from "react";
import { useLocation } from "react-router-dom";
import "./degreeinfo.css";

type CourseRow = {
  course_id:  string;
  attempt_id: string | null;
  term:       string | null;
};

type Section = {
  id:        string;
  label:     string;
  satisfied: boolean;
  rows:      CourseRow[];
};

type AuditData = {
  status: string;
  completion_percentage: number;
  assignments: Record<string, Array<{ attempt_id: string; course_id: string }>>;
  slack:       Record<string, number>;
  broad_data: {
    student_name:    string | null;
    gpa:             number | null;
    earned_credits:  number | null;
    program:         string | null;
    catalog_year:    string | null;
    declared_major:  { name: string; catalog_year: string } | null;
    declared_majors?: { name: string; catalog_year: string }[];
    minors:          { name: string; catalog_year: string }[];
  };
  programs_loaded: {
    degree_type: { code: string; catalog_year: string };
    major?:      { code: string; name: string; catalog_year: string };
    minors?:     { code: string; name: string; catalog_year: string }[];
  };
};

const LABELS: Record<string, string> = {
  cs_core_lower:         "Lower-Division Core",
  cs_core_upper:         "Upper-Division Core",
  cs_upper_div_elective: "Upper-Division Electives",
  cs_lower_core:         "Lower-Division Core",
  cs_upper_core:         "Upper-Division Core",
  cs_upper_electives:    "Upper-Division Electives",
  cs313_required:        "CS 313 Requirement",
  math_discrete:         "Discrete Math",
  bs_math_or_cis_year:   "Math / CIS Requirement",
  math_200plus_total:    "200+ Level Math Credits",
  math_upper_15:         "Upper-Division Math Credits",
  math_minor:            "Math Minor Total Credits",
  science_bio:           "Science - Biology",
  science_chem:          "Science - Chemistry",
  science_erth:          "Science - Earth Sciences",
  science_geog:          "Science - Geography",
  science_phys:          "Science - Physics",
  science_psy:           "Science - Psychology",
  calc_seq_251_252:      "Calculus Sequence (251-252)",
  calc_seq_261_262:      "Calculus Sequence (261-262)",
  calc_seq_246_247:      "Calculus Sequence (246-247)",
  math_elective_a:       "Math Elective A",
  math_elective_b:       "Math Elective B",
  math_elective_c:       "Math Elective C",
  math_elective_d:       "Math Elective D",
  upper_math_from_math:  "Upper-Division Math (MATH)",
  upper_math_from_cs:    "Upper-Division Math (CS)",
  writing:               "Writing Requirement",
};

function bucketLabel(key: string): string {
  const tail = key.split(":").pop() ?? key;
  return LABELS[tail] ?? tail.replace(/_/g, " ").replace(/\b\w/g, (c: string) => c.toUpperCase());
}

function parseTerm(attemptId: string): string {
  const m = attemptId.match(/^(\d{4})([FWSU])-/);
  if (!m) return attemptId;
  const season = { F: "Fall", W: "Winter", S: "Spring", U: "Summer" }[m[2]] ?? m[2];
  return `${season} ${m[1]}`;
}

function classUrl(courseId: string): string {
  const m = courseId.match(/^([A-Z]{2,5})(\d+[A-Z]?)$/);
  if (!m) return `/class?q=${encodeURIComponent(courseId)}`;
  return `/class?q=${encodeURIComponent(m[1])}+${encodeURIComponent(m[2])}`;
}

// ---- Data -------------------------------------------------------------------

function getSections(
  assignments: AuditData["assignments"],
  slack: AuditData["slack"]
): Section[] {
  return Object.entries(assignments).map(
    ([bucketKey, courses]: [string, Array<{ attempt_id: string; course_id: string }>]) => {
      const depth = bucketKey.split(":").length;

      const slots = Object.entries(slack).filter(
        ([k]) => k.startsWith(bucketKey + ":") && k.split(":").length === depth + 1
      );

      const taken = new Map(courses.map((c) => [c.course_id, c]));

      if (slots.length > 0) {
        const rows = slots.map(([slotKey]) => {
          const courseId = slotKey.split(":").pop()!;
          const attempt  = taken.get(courseId);
          return attempt
            ? { course_id: courseId, attempt_id: attempt.attempt_id, term: parseTerm(attempt.attempt_id) }
            : { course_id: courseId, attempt_id: null, term: null };
        });
        return { id: bucketKey, label: bucketLabel(bucketKey), satisfied: slots.every(([, v]) => v === 0), rows };
      } else {
        const rows = courses.map((c) => ({ course_id: c.course_id, attempt_id: c.attempt_id, term: parseTerm(c.attempt_id) }));
        return { id: bucketKey, label: bucketLabel(bucketKey), satisfied: slack[bucketKey] === 0, rows };
      }
    }
  );
}

// ---- Components -------------------------------------------------------------

function RequirementSection({ section }: { section: Section }) {
  const [open, setOpen] = useState(true);

  return (
    <div className="di-section">
      <div className="di-section-header" onClick={() => setOpen((o) => !o)}>
        <span className={section.satisfied ? "di-icon-ok" : "di-icon-miss"}>
          {section.satisfied ? "✓" : "✕"}
        </span>
        <span className="di-section-title">{section.label}</span>
        <span className={section.satisfied ? "di-sat-ok" : "di-sat-miss"}>
          {section.satisfied ? "Satisfied" : "Not Satisfied"}
        </span>
        <span className="di-chevron">{open ? "▲" : "▼"}</span>
      </div>

      {open && (
        <table className="di-table">
          <thead>
            <tr>
              <th className="di-th">Course</th>
              <th className="di-th">Term</th>
              <th className="di-th">Status</th>
            </tr>
          </thead>
          <tbody>
            {section.rows.map((row, i) => (
              <tr key={row.attempt_id ?? `missing-${i}`} className={!row.attempt_id ? "di-row-missing" : ""}>
                <td className="di-td">
                  <a href={classUrl(row.course_id)} className="di-course-link" target="_blank" rel="noreferrer">
                    {row.course_id}
                  </a>
                </td>
                <td className="di-td">{row.term ?? "—"}</td>
                <td className="di-td">
                  {row.attempt_id
                    ? <span className="di-status-ok">Completed</span>
                    : <span className="di-status-missing">Not taken</span>
                  }
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

// ---- Page -------------------------------------------------------------------

export default function DegreeInfo() {
  const location = useLocation()

  const auditData = useState<AuditData | null>(() => {
    if (location.state?.auditData) return location.state.auditData as AuditData
    const stored = sessionStorage.getItem("auditData")
    if (stored) {
      try { return JSON.parse(stored) as AuditData } catch { return null }
    }
    return null
  })[0]

  if (!auditData) {
    return <p className="di-state-msg error">No transcript data found. Please upload your transcript first.</p>
  }

  const { broad_data: bd, programs_loaded: prog, completion_percentage: pct, assignments, slack } = auditData
  const sections  = getSections(assignments, slack)
  const majorName = prog.major?.name ?? bd.declared_majors?.[0]?.name ?? bd.declared_major?.name ?? "Unknown Major"
  const catalog   = prog.major?.catalog_year ?? bd.catalog_year ?? ""
  const minors    = bd.minors ?? []

  return (
    <div className="di-root">
      <div className="di-header">
        <div>
          <h1 className="di-title">
            Major in {majorName}
            <span className="di-pill">In-Progress</span>
          </h1>
          <p className="di-meta">
            {prog.degree_type.code} &nbsp;·&nbsp; Catalog {catalog}
            {bd.gpa != null && <> &nbsp;·&nbsp; GPA {bd.gpa}</>}
            {minors.map((m) => <span key={m.name}> &nbsp;·&nbsp; Minor: {m.name}</span>)}
          </p>
        </div>
        <div className="di-pct">{pct.toFixed(1)}%</div>
      </div>

      <div className="di-body">
        {sections.map((s) => <RequirementSection key={s.id} section={s} />)}
      </div>
    </div>
  );
}
