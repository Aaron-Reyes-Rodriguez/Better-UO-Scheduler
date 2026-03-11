import { useState } from "react";
import { useLocation } from "react-router-dom";
import "./degreeinfo.css";

type courseRows = {
  course_id:  string;
  attempt_id: string | null;
  term:       string | null;
};

type section = {
  id:        string;
  label:     string;
  satisfied: boolean;
  rows:      courseRows[];
};

type parsedData = {
  status: string;
  completion_percentage: number;
  student_name?: string | null;
  assignments: Record<string, Array<{ attempt_id: string; course_id: string }>>;
  slack:       Record<string, number>;
  broad_data: {
    student_name:     string | null;
    gpa:              number | null;
    earned_credits:   number | null;
    program:          string | null;
    catalog_year:     string | null;
    declared_major:   { name: string; catalog_year: string } | null;
    declared_majors?: { name: string; catalog_year: string }[];
    minors:           { name: string; catalog_year: string }[];
  };
  programs_loaded: {
    degree_type: { code: string; catalog_year: string };
    major?:      { code: string; name: string; catalog_year: string };
    minors?:     { code: string; name: string; catalog_year: string }[];
  };
};

type groupedSections = {
  degreeType: section[];
  major:      section[];
  minors:     { code: string; sections: section[] }[];
};

// Maps the backend bucket terms into readable section names
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
  math_minor_credits:    "Math Minor Credits",
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
  dsci_depth:            "DSCI Depth Requirement",
};

// For the final row in every section, 
// such that if they're missing classes from a range (300 or 400 level)
// indicate the level/type  here
const BUCKET_LEFTOVERS: Record<string, string> = {
  cs_upper_electives:    "300/400-level CS courses required",
  cs_upper_div_elective: "300/400-level CS courses required",
  math_200plus_total:    "200+ level MATH courses required",
  math_upper_15:         "300/400-level MATH courses required",
  math_minor:            "MATH courses required",
  upper_math_from_cs:    "400-level CS or MATH courses required",
  upper_math_from_math:  "400-level MATH courses required",
  science_bio:           "BI courses required",
  science_chem:          "CH courses required",
  science_erth:          "ERTH courses required",
  science_geog:          "GEOG courses required",
  science_phys:          "PHYS courses required",
  science_psy:           "PSY courses required",
  dsci_depth:            "300/400-level DSCI courses required",
  bs_math_or_cis_year:   "MATH or CIS courses required",
  math_minor_credits: "MATH courses required (200+ level, 15 must be 300+)",
};

function bucketLabels(key: string): string {
  const tail = key.split(":").pop() ?? key;
  return LABELS[tail] ?? tail.replace(/_/g, " ").replace(/\b\w/g, (c: string) => c.toUpperCase());
}

function parsedTerm(attemptId: string): string {
  const m = attemptId.match(/^(\d{4})([FWSU])-/);
  if (!m) return attemptId;
  const season = { F: "Fall", W: "Winter", S: "Spring", U: "Summer" }[m[2]] ?? m[2];
  return `${season} ${m[1]}`;
}

// makes the URL needed to access a given course (following a specific format)
function classURL(courseId: string): string {
  const m = courseId.match(/^([A-Z]{2,5})(\d+[A-Z]?)$/);
  if (!m) return `/class?q=${encodeURIComponent(courseId)}`;
  return `/class?q=${encodeURIComponent(m[1])}+${encodeURIComponent(m[2])}`;
}

function getSections(
  assignments: parsedData["assignments"],
  slack: parsedData["slack"]
): section[] {
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
            ? { course_id: courseId, attempt_id: attempt.attempt_id, term: parsedTerm(attempt.attempt_id) }
            : { course_id: courseId, attempt_id: null, term: null };
        });
        return { id: bucketKey, label: bucketLabels(bucketKey), satisfied: slots.every(([, v]) => v === 0), rows };
      } else {
        const rows = courses.map((c) => ({ course_id: c.course_id, attempt_id: c.attempt_id, term: parsedTerm(c.attempt_id) }));
        return { id: bucketKey, label: bucketLabels(bucketKey), satisfied: slack[bucketKey] === 0, rows };
      }
    }
  );
}

function programGrouping(sections: section[]): groupedSections {
  const degreeType: section[] = [];
  const major: section[]      = [];
  const minorMap = new Map<string, section[]>();

  for (const s of sections) {
    const programId = s.id.split(":")[0];
    if (programId.startsWith("UO_BS") || programId.startsWith("UO_BA")) {
      degreeType.push(s);
    } else if (programId.startsWith("MAJOR_")) {
      major.push(s);
    } else if (programId.startsWith("MINOR_")) {
      const arr = minorMap.get(programId) ?? [];
      arr.push(s);
      minorMap.set(programId, arr);
    }
  }

  return {
    degreeType,
    major,
    minors: Array.from(minorMap.entries()).map(([code, secs]) => ({ code, sections: secs })),
  };
}


function RequirementSection({ section: s, slack }: { section: section; slack: number }) {
  const [open, setOpen] = useState(true);
  const tail    = s.id.split(":").pop() ?? "";
  const hint    = BUCKET_LEFTOVERS[tail];
  const showhint = !s.satisfied && hint && slack > 0;

  return (
    <div className="di-section">
      <div className="di-section-header" onClick={() => setOpen((o) => !o)}>
        <span className={s.satisfied ? "di-icon-ok" : "di-icon-miss"}>
          {s.satisfied ? "✓" : "✕"}
        </span>
        <span className="di-section-title">{s.label}</span>
        <span className={s.satisfied ? "di-sat-ok" : "di-sat-miss"}>
          {s.satisfied ? "Satisfied" : "Not Satisfied"}
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
            {s.rows.map((row, i) => (
              <tr key={row.attempt_id ?? `missing-${i}`} className={!row.attempt_id ? "di-row-missing" : ""}>
                <td className="di-td">
                  <a href={classURL(row.course_id)} className="di-course-link" target="_blank" rel="noreferrer">
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
            {showhint && (
              <tr className="di-row-hint">
                <td className="di-td di-td-hint" colSpan={3}>
                  {slack} more {hint}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default function DegreeInfo() {
  const location = useLocation()

  const auditedData = useState<parsedData | null>(() => {
    if (location.state?.auditData) return location.state.auditData as parsedData
    const stored = localStorage.getItem("auditData")
    if (stored) {
      try { return JSON.parse(stored) as parsedData } catch { return null }
    }
    return null
  })[0]

  if (!auditedData) {
    return <p className="di-state-msg error">No transcript data found. Please upload your transcript first.</p>
  }

  const { broad_data: gd, programs_loaded: programs, student_name, assignments, slack } = auditedData
  const allSections  = getSections(assignments, slack)
  const grouped      = programGrouping(allSections)
  const studentName  = student_name ?? gd.student_name ?? null
  const majorName    = programs.major?.name ?? gd.declared_majors?.[0]?.name ?? gd.declared_major?.name ?? "Unknown Major"
  const loadedMinors = programs.minors ?? []
  const declaredMinors = gd.minors ?? []

  return (
    <div className="di-root">

      {/* Header — student name, degree info, minors */}
      <div className="di-header">
        <div>
          <h1 className="di-title">
            {studentName || "Degree Audit"}
            <span className="di-pill">In-Progress</span>
          </h1>
          <p className="di-meta">
            {programs.degree_type.code} in {majorName}
            {programs.degree_type.catalog_year && (
              <> &nbsp;·&nbsp; Catalog {programs.degree_type.catalog_year}</>
            )}
            {declaredMinors.map((m) => (
              <span key={m.name}>
                &nbsp;·&nbsp; Minor: {m.name}
                {m.catalog_year && ` (${m.catalog_year})`}
              </span>
            ))}
          </p>
        </div>
      </div>

      <div className="di-body">

        {/* BS/BA degree type requirements */}
        {grouped.degreeType.length > 0 && (
          <div className="di-program-group">
            <h2 className="di-group-title">{programs.degree_type.code} Degree Requirements</h2>
            <p className="di-group-subtitle">General requirements for the {programs.degree_type.code} degree</p>
            {grouped.degreeType.map((s) => (
              <RequirementSection key={s.id} section={s} slack={auditedData.slack[s.id] ?? 0} />
            ))}
          </div>
        )}

        {/* Major requirements */}
        {grouped.major.length > 0 && (
          <div className="di-program-group">
            <h2 className="di-group-title">Major: {majorName}</h2>
            <p className="di-group-subtitle">Catalog {programs.major?.catalog_year ?? gd.catalog_year ?? ""}</p>
            {grouped.major.map((s) => (
              <RequirementSection key={s.id} section={s} slack={auditedData.slack[s.id] ?? 0} />
            ))}
          </div>
        )}

        {/* Minor requirements — iterates all declared minors, shows placeholder if no data loaded */}
        {(loadedMinors.length > 0 ? loadedMinors : declaredMinors).map((minor) => {
          const minorCode     = "code" in minor ? (minor as { code: string }).code : "";
          const minorName     = minor.name;
          const minorSections = grouped.minors.find((g) => g.code.includes(minorCode))?.sections ?? [];
          return (
            <div key={minorName} className="di-program-group">
              <h2 className="di-group-title">Minor: {minorName}</h2>
              <p className="di-group-subtitle">
                {minor.catalog_year ? `Catalog ${minor.catalog_year}` : ""}
              </p>
              {minorSections.length > 0 ? (
                minorSections.map((s) => (
                  <RequirementSection key={s.id} section={s} slack={auditedData.slack[s.id] ?? 0} />
                ))
              ) : (
                <p className="di-minor-empty">No requirement data available for this minor.</p>
              )}
            </div>
          );
        })}

      </div>
    </div>
  );
}
