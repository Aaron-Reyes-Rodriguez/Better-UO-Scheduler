import { useState, useCallback } from "react";
import { useLocation } from "react-router-dom";
import { reAudit } from "../api";
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

type ChoiceOption = { id: string; label: string };
type Choice = {
  program_id:     string;
  requirement_id: string;
  label:          string;
  options:        ChoiceOption[];
  solver_pick:    string | null;
};

type AuditData = {
  status: string;
  completion_percentage: number;
  student_name?: string | null;
  labels?: Record<string, string>;
  choices?: Choice[];
  parsedData?: Record<string, unknown>;
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

// Resolves a bucket key to a human-readable label.
// Priority: 1) labels from API (defined in JSON), 2) auto-format the key
function bucketLabel(key: string, apiLabels?: Record<string, string>): string {
  if (apiLabels?.[key]) return apiLabels[key];
  const tail = key.split(":").pop() ?? key;
  return tail.replace(/_/g, " ").replace(/\b\w/g, (c: string) => c.toUpperCase());
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
  assignments: AuditData["assignments"],
  slack: AuditData["slack"],
  apiLabels?: Record<string, string>
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
            ? { course_id: courseId, attempt_id: attempt.attempt_id, term: parsedTerm(attempt.attempt_id) }
            : { course_id: courseId, attempt_id: null, term: null };
        });
        return { id: bucketKey, label: bucketLabel(bucketKey, apiLabels), satisfied: slots.every(([, v]) => v === 0), rows };
      } else {
        const rows = courses.map((c) => ({ course_id: c.course_id, attempt_id: c.attempt_id, term: parseTerm(c.attempt_id) }));
        return { id: bucketKey, label: bucketLabel(bucketKey, apiLabels), satisfied: slack[bucketKey] === 0, rows };
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

// ---- Choice selector --------------------------------------------------------

function ChoiceDropdown({
  choice,
  value,
  onChange,
  disabled,
}: {
  choice: Choice;
  value: string;
  onChange: (reqId: string, selected: string) => void;
  disabled: boolean;
}) {
  return (
    <label className="di-choice-label">
      <span className="di-choice-name">{choice.label}:</span>
      <select
        className="di-choice-select"
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(choice.requirement_id, e.target.value)}
      >
        {choice.options.map((opt) => (
          <option key={opt.id} value={opt.id}>{opt.label}</option>
        ))}
      </select>
    </label>
  );
}

// ---- Page -------------------------------------------------------------------

function initSelections(choices: Choice[]): Record<string, string> {
  const out: Record<string, string> = {};
  for (const c of choices) {
    out[c.requirement_id] = c.solver_pick ?? c.options[0]?.id ?? "";
  }
  return out;
}

export default function DegreeInfo() {
  const location = useLocation()

  const [auditData, setAuditData] = useState<AuditData | null>(() => {
    if (location.state?.auditData) return location.state.auditData as AuditData
    const stored = sessionStorage.getItem("auditData")
    if (stored) {
      try { return JSON.parse(stored) as parsedData } catch { return null }
    }
    return null
  })

  const [selections, setSelections] = useState<Record<string, string>>(() => {
    const data = (location.state?.auditData as AuditData | undefined)
      ?? (() => { try { return JSON.parse(sessionStorage.getItem("auditData") ?? "") as AuditData } catch { return null } })()
    return initSelections(data?.choices ?? [])
  })
  const [reAuditing, setReAuditing] = useState(false)

  const handleChoiceChange = useCallback(async (reqId: string, selected: string) => {
    if (!auditData?.parsedData) return
    const next = { ...selections, [reqId]: selected }
    setSelections(next)
    setReAuditing(true)
    try {
      const data = await reAudit(auditData.parsedData, next) as AuditData
      setAuditData(data)
      sessionStorage.setItem("auditData", JSON.stringify(data))
    } catch (err) {
      console.error("Re-audit failed:", err)
    } finally {
      setReAuditing(false)
    }
  }, [auditData, selections])

  if (!auditedData) {
    return <p className="di-state-msg error">No transcript data found. Please upload your transcript first.</p>
  }

  const { broad_data: bd, programs_loaded: prog, student_name, labels: apiLabels, assignments, slack, choices } = auditData
  const sections  = getSections(assignments, slack, apiLabels)
  const grouped   = groupByProgram(sections)
  const displayName = student_name ?? bd.student_name ?? null
  const majorName = prog.major?.name ?? bd.declared_majors?.[0]?.name ?? bd.declared_major?.name ?? "Unknown Major"
  const loadedMinors = prog.minors ?? []
  const declaredMinors = bd.minors ?? []
  const majorChoices = (choices ?? []).filter((c) => c.program_id.startsWith("MAJOR_"))

  return (
    <div className={`di-root ${reAuditing ? "di-reauditing" : ""}`}>
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
            <p className="di-group-subtitle">Catalog {prog.major?.catalog_year ?? bd.catalog_year ?? ""}</p>

            {majorChoices.length > 0 && (
              <div className="di-choices-bar">
                {majorChoices.map((c) => (
                  <ChoiceDropdown
                    key={c.requirement_id}
                    choice={c}
                    value={selections[c.requirement_id] ?? c.solver_pick ?? ""}
                    onChange={handleChoiceChange}
                    disabled={reAuditing}
                  />
                ))}
                {reAuditing && <span className="di-reaudit-spinner">Updating...</span>}
              </div>
            )}

            {grouped.major.map((s) => <RequirementSection key={s.id} section={s} />)}
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
