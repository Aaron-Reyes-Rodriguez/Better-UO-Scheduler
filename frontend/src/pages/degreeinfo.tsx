import { useState } from "react";
import { useLocation } from "react-router-dom";
import "./degreeinfo.css";

type CourseRow = {
  course_id: string;
  attempt_id: string | null;
  term: string | null;
};

type Section = {
  id: string;
  label: string;
  satisfied: boolean;
  rows: CourseRow[];
};

type AuditData = {
  completion_percentage?: number;
  student_name?: string | null;
  broad_data?: { student_name?: string | null };
  assignments: Record<string, Array<{ attempt_id: string; course_id: string }>>;
  slack: Record<string, number>;
  programs_loaded: {
    degree_type: { code: string; catalog_year: string };
    major: { code: string; name: string; catalog_year: string };
    minors: Array<{ code: string; name: string; catalog_year: string }>;
  };
};

const LABEL_OVERRIDES: Record<string, string> = {
  "cs_core_lower": "Lower-Division Core",
  "cs_core_upper": "Upper-Division Core",
  "cs_upper_div_elective": "Upper-Division Electives",
  "bs_math_or_cis_year":   "Math / CIS Requirement",
  "science_sequence":      "Science Sequence",
};

function formatLabel(bucketKey: string): string {
  const tail = bucketKey.split(":").pop() ?? bucketKey;
  return (
    LABEL_OVERRIDES[tail] ??
    tail.replace(/_/g, " ").replace(/\b\w/g, (c: string) => c.toUpperCase())
  );
}

function termFromAttemptId(id: string): string {
  const m = id.match(/^(\d{4})([FWSU])-/);
  if (!m) return id;
  const season = { F: "Fall", W: "Winter", S: "Spring", U: "Summer" }[m[2]] ?? m[2];
  return `${season} ${m[1]}`;
}

function buildSections(
  assignments: AuditData["assignments"],
  slack: AuditData["slack"]
): Section[] {
  return Object.entries(assignments).map(
    ([bucketKey, courses]: [string, Array<{ attempt_id: string; course_id: string }>]) => {
      const slotEntries = Object.entries(slack).filter(([k]) => {
        const bucketDepth = bucketKey.split(":").length;
        const slotDepth = k.split(":").length;
        return k.startsWith(bucketKey + ":") && slotDepth === bucketDepth + 1;
      });

      const assignedMap = new Map(courses.map((c) => [c.course_id, c]));
      let rows: CourseRow[];
      let satisfied: boolean;

      if (slotEntries.length > 0) {
        rows = slotEntries.map(([slotKey]) => {
          const course_id = slotKey.split(":").pop()!;
          const attempt   = assignedMap.get(course_id);
          if (attempt) {
            return { course_id, attempt_id: attempt.attempt_id, term: termFromAttemptId(attempt.attempt_id) };
          } else {
            return { course_id, attempt_id: null, term: null };
          }
        });
        satisfied = slotEntries.every(([, v]) => v === 0);
      } else {
        rows = courses.map((c) => ({
          course_id:  c.course_id,
          attempt_id: c.attempt_id,
          term:       termFromAttemptId(c.attempt_id),
        }));
        satisfied = slack[bucketKey] === 0;
      }

      return { id: bucketKey, label: formatLabel(bucketKey), satisfied, rows };
    }
  );
}

// ---------------------------------------------------------------------------
// GROUP SECTIONS BY PROGRAM TYPE
// Bucket keys are "program_id:req_id". Program IDs: UO_BS_*, UO_BA_*, MAJOR_*, MINOR_*
// ---------------------------------------------------------------------------
type GroupedSections = {
  degreeType: Section[];
  major: Section[];
  minors: { programId: string; sections: Section[] }[];
};

function groupSectionsByProgram(sections: Section[]): GroupedSections {
  const degreeType: Section[] = [];
  const major: Section[] = [];
  const minorGroups = new Map<string, Section[]>();

  for (const s of sections) {
    const programId = s.id.split(":")[0];
    if (programId.startsWith("UO_BS_") || programId.startsWith("UO_BA_")) {
      degreeType.push(s);
    } else if (programId.startsWith("MAJOR_")) {
      major.push(s);
    } else if (programId.startsWith("MINOR_")) {
      const arr = minorGroups.get(programId) ?? [];
      arr.push(s);
      minorGroups.set(programId, arr);
    }
  }

  return {
    degreeType,
    major,
    minors: Array.from(minorGroups.entries()).map(([programId, secs]) => ({ programId, sections: secs })),
  };
}

// ---------------------------------------------------------------------------
// COMPONENTS
// ---------------------------------------------------------------------------

// One collapsible requirement section
function Section({ section }: { section: Section }) {
  const [open, setOpen] = useState(true);

  return (
    <div className="i-section">
      <div className="i-section-header" onClick={() => setOpen((o) => !o)}>
        <span className={section.satisfied ? "i-icon-ok" : "i-icon-miss"}>
          {section.satisfied ? "✓" : "✕"}
        </span>
        <span className="i-section-title">{section.label}</span>
        <span className={section.satisfied ? "i-sat-ok" : "i-sat-miss"}>
          {section.satisfied ? "Satisfied" : "Not Satisfied"}
        </span>
        <span className="i-chevron">{open ? "▲" : "▼"}</span>
      </div>
      {open && (
        <table className="i-table">
          <thead>
            <tr>
              <th className="i-th">Course</th>
              <th className="i-th">Term</th>
              <th className="i-th">Status</th>
            </tr>
          </thead>
          <tbody>
            {section.rows.map((row, i) => {
              const missing = !row.attempt_id;
              return (
                <tr
                  key={row.attempt_id ?? `missing-${i}`}
                  className={missing ? "i-row-missing" : ""}
                >
                  <td className="i-td">{row.course_id}</td>
                  <td className="i-td">{row.term ?? "—"}</td>
                  <td className="i-td">
                    {missing
                      ? <span className="i-status-missing">Not taken</span>
                      : <span className="i-status-ok">Completed</span>
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

export default function DegreeAudit() {
  const location = useLocation();
  let auditData = location.state?.auditData as AuditData | undefined;

  if (!auditData) {
    const storedData = sessionStorage.getItem("auditData");
    if (storedData) {
      try {
        auditData = JSON.parse(storedData) as AuditData;
      } catch (e) {
        console.error("Failed to parse auditData from sessionStorage", e);
      }
    }
  }

  if (!auditData) return <p className="i-state-msg error">Error: No transcript or audit data found. Please upload a transcript first.</p>;

  const { programs_loaded, student_name, broad_data, assignments, slack } = auditData;
  const displayName = student_name ?? broad_data?.student_name ?? null;

  // Build the section list and group by program type
  const sections = buildSections(assignments, slack);
  const grouped = groupSectionsByProgram(sections);
  const minors = programs_loaded.minors ?? [];

  return (
    <div className="i-root">
      <div className="i-header">
        <div>
          {/* Student name + in-progress pill */}
          <h1 className="da-title">
            {displayName || "Degree Audit"}
            <span className="da-pill">In-Progress</span>
          </h1>

          {/* Program: BS/BA, Major, Minors with catalog years */}
          <p className="da-meta">
            {programs_loaded.degree_type.code} in {programs_loaded.major.name}
            {programs_loaded.degree_type.catalog_year && (
              <> &nbsp;·&nbsp; Catalog {programs_loaded.degree_type.catalog_year}</>
            )}
            {minors.length > 0 && minors.map((m) => (
              <span key={m.code}>
                &nbsp;·&nbsp; Minor: {m.name}
                {m.catalog_year && ` (Catalog ${m.catalog_year})`}
              </span>
            ))}
          </p>
        </div>
      </div>

      {/* ── Requirement sections, grouped by program type ── */}
      <div className="da-body">
        {/* Degree type (BS/BA) requirements */}
        {grouped.degreeType.length > 0 && (
          <div className="da-program-group">
            <h2 className="da-group-title">
              {programs_loaded.degree_type.code} Degree Requirements
            </h2>
            <p className="da-group-subtitle">
              General requirements for the {programs_loaded.degree_type.code} degree
            </p>
            {grouped.degreeType.map((s) => (
              <Section key={s.id} section={s} />
            ))}
          </div>
        )}

        {/* Major requirements */}
        {grouped.major.length > 0 && (
          <div className="da-program-group">
            <h2 className="da-group-title">
              Major: {programs_loaded.major.name}
            </h2>
            <p className="da-group-subtitle">
              Catalog {programs_loaded.major.catalog_year}
            </p>
            {grouped.major.map((s) => (
              <Section key={s.id} section={s} />
            ))}
          </div>
        )}

        {/* Minor requirements — show all declared minors, even if no requirement sections */}
        {minors.map((minor) => {
          const minorSections = grouped.minors.find((g) => g.programId.includes(minor.code))?.sections ?? [];
          return (
            <div key={minor.code} className="da-program-group">
              <h2 className="da-group-title">
                Minor: {minor.name}
              </h2>
              <p className="da-group-subtitle">
                {minor.catalog_year ? `Catalog ${minor.catalog_year}` : ""}
              </p>
              {minorSections.length > 0 ? (
                minorSections.map((s) => (
                  <Section key={s.id} section={s} />
                ))
              ) : (
                <p className="da-minor-empty">No requirement sections defined for this minor.</p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}