// DegreeAudit.tsx
// This page fetches the student's transcript and runs the degree audit,
// then displays the results as a simple list of requirements.

import { useState } from "react";
import { useLocation } from "react-router-dom";
import "./degreeinfo.css";

// ---------------------------------------------------------------------------
// TYPES
// ---------------------------------------------------------------------------

// One row in the course table — either a completed course or a missing slot
type CourseRow = {
  course_id:  string;        // e.g. "CS313"
  attempt_id: string | null; // null means the course hasn't been taken yet
  term:       string | null; // e.g. "Fall 2023", null if not taken
};

// One requirement section (e.g. "Upper-Division Core")
type Section = {
  id:        string;   // unique key from the API, e.g. "MAJOR_CS_2022-2023:cs_core_upper"
  label:     string;   // human-readable name shown in the UI
  satisfied: boolean;  // true = all courses in this bucket are fulfilled
  rows:      CourseRow[];
};

// The shape of the full audit API response
type AuditData = {
  completion_percentage: number;
  assignments: Record<string, Array<{ attempt_id: string; course_id: string }>>;
  slack:       Record<string, number>;
  programs_loaded: {
    degree_type: { code: string; catalog_year: string };
    major:       { code: string; name: string; catalog_year: string };
    minors:      Array<{ code: string; name: string; catalog_year: string }>;
  };
};

// ---------------------------------------------------------------------------
// LABEL OVERRIDES
// By default, bucket keys like "cs_core_upper" are auto-formatted to
// "Cs Core Upper". Add entries here to give them nicer names.
// The page works fine without these — add them as you encounter new majors.
// ---------------------------------------------------------------------------
const LABEL_OVERRIDES: Record<string, string> = {
  "cs_core_lower":         "Lower-Division Core",
  "cs_core_upper":         "Upper-Division Core",
  "cs_upper_div_elective": "Upper-Division Electives",
  "bs_math_or_cis_year":   "Math / CIS Requirement",
};

// Converts a bucket key into a readable label.
// Checks LABEL_OVERRIDES first, then falls back to formatting the raw key.
// e.g. "cs_core_upper" → "Cs Core Upper" if no override exists
function formatLabel(bucketKey: string): string {
  // Bucket keys look like "MAJOR_CS_2022-2023:cs_core_upper"
  // We only want the last segment after the final ":"
  const tail = bucketKey.split(":").pop() ?? bucketKey;

  return (
    LABEL_OVERRIDES[tail] ??
    tail.replace(/_/g, " ").replace(/\b\w/g, (c: string) => c.toUpperCase())
  );
}

// ---------------------------------------------------------------------------
// HELPERS
// ---------------------------------------------------------------------------

// Converts an attempt ID like "2023F-CS313-01" into "Fall 2023"
function termFromAttemptId(id: string): string {
  const m = id.match(/^(\d{4})([FWSU])-/);
  if (!m) return id;
  const season = { F: "Fall", W: "Winter", S: "Spring", U: "Summer" }[m[2]] ?? m[2];
  return `${season} ${m[1]}`;
}

// ---------------------------------------------------------------------------
// BUILD SECTIONS
// Derives the section list purely from the API response.
// No hardcoded course names or major-specific logic.
// ---------------------------------------------------------------------------
function buildSections(
  assignments: AuditData["assignments"],
  slack: AuditData["slack"]
): Section[] {

  // Each key in assignments is a requirement bucket.
  // We map over them to build one Section object per bucket.
  return Object.entries(assignments).map(
    ([bucketKey, courses]: [string, Array<{ attempt_id: string; course_id: string }>]) => {

      // Find per-course slot entries in slack that belong to this bucket.
      // e.g. "MAJOR_CS_2022-2023:cs_core_upper:CS313" belongs to
      //      "MAJOR_CS_2022-2023:cs_core_upper"
      const slotEntries = Object.entries(slack).filter(([k]) => {
        const bucketDepth = bucketKey.split(":").length; // segments in the bucket key
        const slotDepth   = k.split(":").length;         // segments in this slack key
        // must start with the bucket key and have exactly one extra segment
        return k.startsWith(bucketKey + ":") && slotDepth === bucketDepth + 1;
      });

      // Map of course_id → attempt for quick lookup
      const assignedMap = new Map(courses.map((c) => [c.course_id, c]));

      let rows: CourseRow[];
      let satisfied: boolean;

      if (slotEntries.length > 0) {
        // FIXED-SLOT BUCKET: specific named courses are required.
        // slack === 0 on a slot means it's filled; === 1 means still needed.

        rows = slotEntries.map(([slotKey]) => {
          const course_id = slotKey.split(":").pop()!; // last segment is the course ID
          const attempt   = assignedMap.get(course_id);

          if (attempt) {
            // Student completed this course
            return { course_id, attempt_id: attempt.attempt_id, term: termFromAttemptId(attempt.attempt_id) };
          } else {
            // Course not yet taken — will render as a greyed-out missing row
            return { course_id, attempt_id: null, term: null };
          }
        });

        // Satisfied only when every individual slot is filled (slack === 0)
        satisfied = slotEntries.every(([, v]) => v === 0);

      } else {
        // OPEN / ELECTIVE BUCKET: any course can fill it.
        // Just show all assigned courses and rely on the top-level slack value.

        rows = courses.map((c) => ({
          course_id:  c.course_id,
          attempt_id: c.attempt_id,
          term:       termFromAttemptId(c.attempt_id),
        }));

        // Top-level slack === 0 means the bucket is fully satisfied
        satisfied = slack[bucketKey] === 0;
      }

      return { id: bucketKey, label: formatLabel(bucketKey), satisfied, rows };
    }
  );
}

// ---------------------------------------------------------------------------
// COMPONENTS
// ---------------------------------------------------------------------------

// One collapsible requirement section
function Section({ section }: { section: Section }) {
  // Controls whether the course table is visible
  const [open, setOpen] = useState(true);

  return (
    <div className="da-section">

      {/* Clicking anywhere on the header toggles the course list */}
      <div className="da-section-header" onClick={() => setOpen((o) => !o)}>

        {/* Status icon — green check if satisfied, red X if not */}
        <span className={section.satisfied ? "da-icon-ok" : "da-icon-miss"}>
          {section.satisfied ? "✓" : "✕"}
        </span>

        {/* Requirement name */}
        <span className="da-section-title">{section.label}</span>

        {/* Satisfied / Not Satisfied text on the right */}
        <span className={section.satisfied ? "da-sat-ok" : "da-sat-miss"}>
          {section.satisfied ? "Satisfied" : "Not Satisfied"}
        </span>

        {/* Arrow indicating open/closed state */}
        <span className="da-chevron">{open ? "▲" : "▼"}</span>
      </div>

      {/* Course table — hidden when section is collapsed */}
      {open && (
        <table className="da-table">
          <thead>
            <tr>
              <th className="da-th">Course</th>
              <th className="da-th">Term</th>
              <th className="da-th">Status</th>
            </tr>
          </thead>
          <tbody>
            {section.rows.map((row, i) => {
              // A row with no attempt_id means the course hasn't been taken yet
              const missing = !row.attempt_id;
              return (
                <tr
                  key={row.attempt_id ?? `missing-${i}`}
                  className={missing ? "da-row-missing" : ""}
                >
                  <td className="da-td">{row.course_id}</td>
                  <td className="da-td">{row.term ?? "—"}</td>
                  <td className="da-td">
                    {missing
                      ? <span className="da-status-missing">Not taken</span>
                      : <span className="da-status-ok">Completed</span>
                    }
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// PAGE
// ---------------------------------------------------------------------------
export default function DegreeAudit() {
  // Holds the API response once loaded; null while loading or on error
  const location = useLocation();
  const auditData = location.state?.auditData as AuditData | undefined;

  if (!auditData) return <p className="da-state-msg error">Error: No transcript or audit data found. Please upload a transcript first.</p>;

  const { programs_loaded, completion_percentage, assignments, slack } = auditData;

  // Build the section list dynamically — works for any major
  const sections = buildSections(assignments, slack);

  return (
    <div className="da-root">

      {/* ── Header ── */}
      <div className="da-header">
        <div>
          {/* Degree title + in-progress pill */}
          <h1 className="da-title">
            Major in {programs_loaded.major.name}
            <span className="da-pill">In-Progress</span>
          </h1>

          {/* Degree type, catalog year, and any minors */}
          <p className="da-meta">
            {programs_loaded.degree_type.code} &nbsp;·&nbsp;
            Catalog {programs_loaded.major.catalog_year}
            {programs_loaded.minors.map((m) => (
              <span key={m.code}> &nbsp;·&nbsp; Minor: {m.name}</span>
            ))}
          </p>
        </div>

        {/* Large completion percentage on the right */}
        <div className="da-pct">{completion_percentage}%</div>
      </div>

      {/* ── Requirement sections ── */}
      <div className="da-body">
        {sections.map((s) => (
          <Section key={s.id} section={s} />
        ))}
      </div>

    </div>
  );
}
