/**
 * @file degreeinfo.tsx
 * @description Degree audit results page for Quackademics (Better-UO-Scheduler).
 *   Reads the audit response passed via React Router state after a transcript
 *   upload (or localStorage on page refresh), transforms it into collapsible
 *   requirement sections, and renders them grouped by degree type, major, and
 *   minor. Supports live re-auditing when the student changes a track or
 *   concentration selection via dropdown.
 * @authors Daniel Saito and contributors
 *
 * System: Better-UO-Scheduler (Quackademics)
 *   Mounted by the React Router at path "/audit". Receives auditData from
 *   FileUploader via navigation state. Communicates with the backend via the
 *   reAudit API call when track/concentration selections change. All requirement
 *   data is derived from program JSON files loaded by the backend solver.
 */

// useState: section open/close state, audit data, dropdown selections, re-audit loading flag
// useCallback: keeps handleChoiceChange stable across renders
import { useState, useCallback } from "react";
import { useLocation } from "react-router-dom";
// reAudit: re-runs the degree audit when the student changes a track/concentration
import { reAudit } from "../api";
import "./degreeinfo.css";

// One row in a requirement table — null attempt_id means the course hasn't been taken yet
type CourseRow = {
  course_id: string;
  attempt_id: string | null;
  term: string | null;
};

// One collapsible requirement block, maps to a single bucket key from the backend
type Section = {
  id: string;
  label: string;
  satisfied: boolean;
  rows: CourseRow[];
};

type ChoiceOption = { id: string; label: string };

// A track/concentration choice exposed by the solver, e.g. "Which CS domain track?"
type Choice = {
  program_id: string;
  requirement_id: string;
  label: string;
  options: ChoiceOption[];
  solver_pick: string | null;
};

// Full shape of the backend audit response — mirrors the Python returnData dict in app.py
type AuditData = {
  status: string;
  completion_percentage: number;
  student_name?: string | null;
  labels?: Record<string, string>;
  bucket_hints?: Record<string, string>;
  choices?: Choice[];
  parsedData?: Record<string, unknown>;
  assignments: Record<string, Array<{ attempt_id: string; course_id: string }>>;
  slack: Record<string, number>;
  broad_data: {
    student_name: string | null;
    gpa: number | null;
    earned_credits: number | null;
    program: string | null;
    catalog_year: string | null;
    declared_major: { name: string; catalog_year: string } | null;
    declared_majors?: { name: string; catalog_year: string }[];
    minors: { name: string; catalog_year: string }[];
  };
  programs_loaded: {
    degree_type: { code: string; catalog_year: string };
    major?: { code: string; name: string; catalog_year: string };
    minors?: { code: string; name: string; catalog_year: string }[];
  };
};

// Sections organized into groups for rendering
type GroupedSections = {
  bachelor: Section[];
  degreeType: Section[];
  major: Section[];
  minors: { code: string; sections: Section[] }[];
};

// Resolves a bucket key to a display label.
// API labels take priority since the program JSON is the source of truth; auto-formatting is a fallback.
function bucketLabel(key: string, apiLabels?: Record<string, string>): string {
  if (apiLabels?.[key]) return apiLabels[key];
  const tail = key.split(":").pop() ?? key;
  return tail.replace(/_/g, " ").replace(/\b\w/g, (c: string) => c.toUpperCase());
}

// Converts an attempt ID prefix to a readable term string, e.g. "2023F-CS313-01" -> "Fall 2023"
function parseTerm(attemptId: string): string {
  const m = attemptId.match(/^(\d{4})([FWSU])-/);
  if (!m) return attemptId;
  const season = { F: "Fall", W: "Winter", S: "Spring", U: "Summer" }[m[2]] ?? m[2];
  return `${season} ${m[1]}`;
}

// Builds the internal class page URL for a course ID.
// Strips trailing Z suffix before building (e.g. MATH251Z -> MATH251) since Z is a UO scheduling variant, not part of the course number.
function classUrl(courseId: string): string {
  const normalized = courseId.replace(/Z$/, "");
  const m = normalized.match(/^([A-Z]{2,5})(\d+[A-Z]?)$/);
  if (!m) return `/class?q=${encodeURIComponent(normalized)}`;
  return `/class?q=${encodeURIComponent(m[1])}+${encodeURIComponent(m[2])}`;
}

/**
 * getEffectiveSlackAndHint – resolves the most relevant slack value and hint for a section.
 *
 * For credit_pool requirements with submin constraints (e.g. "12 credits in CS 410+"),
 * the binding constraint may be the submin rather than the main pool total.
 * This matches DuckWeb's behavior of surfacing the most restrictive unmet sub-requirement.
 */
function getEffectiveSlackAndHint(
  sectionId: string,
  slack: Record<string, number>,
  bucketHints?: Record<string, string>
): { slack: number; hint: string | undefined; isCredits: boolean } {
  const mainSlack = slack[sectionId] ?? 0;
  const mainHint = bucketHints?.[sectionId];

  // submin keys follow the pattern MAJOR_CS:cs_upper_electives:submin:0
  const subminKeys = Object.keys(slack).filter(
    (k) => k.startsWith(sectionId + ":submin:") && slack[k] > 0
  );
  if (subminKeys.length > 0) {
    // Use the first unmet submin (binding constraint) — matches DuckWeb "Still needed: 8 Credits in CS 410:499"
    const subminKey = subminKeys[0];
    const subminSlack = slack[subminKey];
    const subminHint = bucketHints?.[subminKey];
    return { slack: subminSlack, hint: subminHint || mainHint, isCredits: true };
  }
  return {
    slack: mainSlack,
    hint: mainHint,
    isCredits: !!mainHint?.toLowerCase().includes("credit"),
  };
}

/**
 * getSections – transforms raw assignments and slack from the audit response into a Section array.
 *
 * Handles two bucket types the backend produces:
 *   - Fixed-slot: requires specific named courses (child slot keys exist in slack)
 *   - Credit-pool: any qualifying course counts (no child slots, only a pool total)
 */
function getSections(
  assignments: AuditData["assignments"],
  slack: AuditData["slack"],
  apiLabels?: Record<string, string>
): Section[] {
  return Object.entries(assignments).map(
    ([bucketKey, courses]: [string, Array<{ attempt_id: string; course_id: string }>]) => {
      const depth = bucketKey.split(":").length;

      // Slot keys sit one level deeper than the bucket key
      const slots = Object.entries(slack).filter(
        ([k]) => k.startsWith(bucketKey + ":") && k.split(":").length === depth + 1
      );

      const taken = new Map(courses.map((c) => [c.course_id, c]));

      if (slots.length > 0) {
        // Fixed-slot: show each required course, mark missing ones
        const rows = slots.map(([slotKey]) => {
          const courseId = slotKey.split(":").pop()!;
          const attempt = taken.get(courseId);
          return attempt
            ? { course_id: courseId, attempt_id: attempt.attempt_id, term: parseTerm(attempt.attempt_id) }
            : { course_id: courseId, attempt_id: null, term: null };
        });
        return { id: bucketKey, label: bucketLabel(bucketKey, apiLabels), satisfied: slots.every(([, v]) => v === 0), rows };
      } else {
        // Credit-pool: list all matching courses the student has taken
        const rows = courses.map((c) => ({ course_id: c.course_id, attempt_id: c.attempt_id, term: parseTerm(c.attempt_id) }));
        // Satisfied only when the main pool AND all submin constraints are met
        const subminKeys = Object.keys(slack).filter((k) => k.startsWith(bucketKey + ":submin:"));
        const allSlacksZero = (slack[bucketKey] ?? 0) === 0 && subminKeys.every((k) => (slack[k] ?? 0) === 0);
        return { id: bucketKey, label: bucketLabel(bucketKey, apiLabels), satisfied: allSlacksZero, rows };
      }
    }
  );
}

// groupByProgram – splits a flat Section array into groups by program ID prefix.
// The prefix format (UO_BACH, UO_BS/UO_BA, MAJOR_, MINOR_) comes from the program JSON IDs in deg_guide/data/programs/.
function groupByProgram(sections: Section[]): GroupedSections {
  const bachelor: Section[] = [];
  const degreeType: Section[] = [];
  const major: Section[] = [];
  const minorMap = new Map<string, Section[]>();

  for (const s of sections) {
    const programId = s.id.split(":")[0];
    if (programId.startsWith("UO_BACH")) {
      bachelor.push(s);
    } else if (programId.startsWith("UO_BS") || programId.startsWith("UO_BA")) {
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
    bachelor,
    degreeType,
    major,
    minors: Array.from(minorMap.entries()).map(([code, secs]) => ({ code, sections: secs })),
  };
}

/**
 * RequirementSection – collapsible card for a single requirement bucket.
 *
 * Shows a course table and one of three footer rows when not satisfied:
 *   1. Fixed-slot: "X classes for this section missing"
 *   2. Backend hint: "X more credits/classes needed — <hint>"
 *   3. Fallback: "X more credits needed" (used when bucket_hints isn't available yet)
 */
function RequirementSection({
  section,
  slack,
  hint,
  isCredits,
}: {
  section: Section;
  slack: number;
  hint?: string;
  isCredits?: boolean;
}) {
  const [open, setOpen] = useState(true);
  const showhint = !section.satisfied && !!hint && slack > 0;
  // Count rows with no attempt_id — these are specific required courses not yet taken
  const missingCount = section.rows.filter((r) => !r.attempt_id).length;
  // Fallback for credit-pool sections where bucket_hints isn't available from the backend yet
  const creditShortfall = !section.satisfied && missingCount === 0 && !hint && slack > 0;

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
            {!section.satisfied && missingCount > 0 && (
              <tr className="di-row-hint">
                <td className="di-td di-td-hint" colSpan={3}>
                  {missingCount} class{missingCount !== 1 ? "es" : ""} for this section missing
                </td>
              </tr>
            )}
            {/* isCredits switches the unit label between "credits" and "classes" based on the binding constraint */}
            {showhint && (
              <tr className="di-row-hint">
                <td className="di-td di-td-hint" colSpan={3}>
                  {slack} more {isCredits ? `credit${slack !== 1 ? "s" : ""}` : `class${slack !== 1 ? "es" : ""}`} needed — {hint}
                </td>
              </tr>
            )}
            {creditShortfall && (
              <tr className="di-row-hint">
                <td className="di-td di-td-hint" colSpan={3}>
                  {slack} more credit{slack !== 1 ? "s" : ""} needed for this section
                </td>
              </tr>
            )}
          </tbody>
        </table>
      )}
    </div>
  );
}

/**
 * ChoiceDropdown – labeled dropdown for a single track/concentration choice.
 *
 * Fires onChange immediately on selection to trigger a live re-audit.
 * disabled is passed from reAuditing to prevent a second change mid-flight,
 * which would cause two audit results to arrive out of order.
 */
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

// Seeds dropdown state from the solver's recommended picks.
// Solver pick is preferred over the first option since it reflects the best-fitting
// track for the student's existing courses — defaulting elsewhere would show a lower completion %.
function initSelections(choices: Choice[]): Record<string, string> {
  const out: Record<string, string> = {};
  for (const c of choices) {
    out[c.requirement_id] = c.solver_pick ?? c.options[0]?.id ?? "";
  }
  return out;
}

/**
 * DegreeInfo – main degree audit page component.
 *
 * Reads auditData from React Router state (post-upload) or localStorage (page refresh).
 * Renders requirement sections grouped by bachelor requirements, degree type, major, and minors.
 */
export default function DegreeInfo() {
  const location = useLocation()

  // Router state is the normal path after upload; localStorage handles page refresh
  const [auditData, setAuditData] = useState<AuditData | null>(() => {
    if (location.state?.auditData) return location.state.auditData as AuditData
    const stored = localStorage.getItem("auditData")
    if (stored) {
      try { return JSON.parse(stored) as AuditData } catch { return null }
    }
    return null
  })

  const [selections, setSelections] = useState<Record<string, string>>(() => {
    const data = (location.state?.auditData as AuditData | undefined)
      ?? (() => { try { return JSON.parse(localStorage.getItem("auditData") ?? "") as AuditData } catch { return null } })()
    return initSelections(data?.choices ?? [])
  })

  // True while waiting for a re-audit response — fades the body and disables dropdowns
  const [reAuditing, setReAuditing] = useState(false)

  // Fires on dropdown change — calls re-audit and updates localStorage so selections survive a refresh
  const handleChoiceChange = useCallback(async (reqId: string, selected: string) => {
    if (!auditData?.parsedData) return
    const next = { ...selections, [reqId]: selected }
    setSelections(next)
    setReAuditing(true)
    try {
      const data = await reAudit(auditData.parsedData, next) as AuditData
      setAuditData(data)
      localStorage.setItem("auditData", JSON.stringify(data))
    } catch (err) {
      console.error("Re-audit failed:", err)
    } finally {
      setReAuditing(false)
    }
  }, [auditData, selections])

  if (!auditData) {
    return <p className="di-state-msg error">No transcript data found. Please upload your transcript first.</p>
  }

  const { broad_data: bd, programs_loaded: prog, student_name, labels: apiLabels, bucket_hints: bucketHints, assignments, slack, choices } = auditData
  const sections = getSections(assignments, slack, apiLabels)
  const grouped = groupByProgram(sections)
  const displayName = student_name ?? bd.student_name ?? null
  const majorName = prog.major?.name ?? bd.declared_majors?.[0]?.name ?? bd.declared_major?.name ?? "Unknown Major"
  const loadedMinors = prog.minors ?? []
  const declaredMinors = bd.minors ?? []
  // Only the major exposes track/concentration choices currently
  const majorChoices = (choices ?? []).filter((c) => c.program_id.startsWith("MAJOR_"))

  return (
    <div className={`di-root ${reAuditing ? "di-reauditing" : ""}`}>
      <div className="di-header">
        <div>
          <h1 className="di-title">
            {displayName || "Degree Audit"}
            <span className="di-pill">In-Progress</span>
          </h1>
          <p className="di-meta">
            {prog.degree_type.code} in {majorName}
            {prog.degree_type.catalog_year && (
              <> &nbsp;·&nbsp; Catalog {prog.degree_type.catalog_year}</>
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
        {/* Shared university-wide requirements, e.g. general education */}
        {grouped.bachelor.length > 0 && (
          <div className="di-program-group">
            <h2 className="di-group-title">UO Bachelor Degree</h2>
            <p className="di-group-subtitle">Shared university-wide requirements</p>
            {grouped.bachelor.map((s) => {
              const { slack: effSlack, hint: effHint, isCredits } = getEffectiveSlackAndHint(s.id, auditData.slack, bucketHints);
              return <RequirementSection key={s.id} section={s} slack={effSlack} hint={effHint} isCredits={isCredits} />;
            })}
          </div>
        )}

        {grouped.degreeType.length > 0 && (
          <div className="di-program-group">
            <h2 className="di-group-title">{prog.degree_type.code} Degree Requirements</h2>
            <p className="di-group-subtitle">General requirements for the {prog.degree_type.code} degree</p>
            {grouped.degreeType.map((s) => {
              const { slack: effSlack, hint: effHint, isCredits } = getEffectiveSlackAndHint(s.id, auditData.slack, bucketHints);
              return <RequirementSection key={s.id} section={s} slack={effSlack} hint={effHint} isCredits={isCredits} />;
            })}
          </div>
        )}

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

            {grouped.major.map((s) => {
              const { slack: effSlack, hint: effHint, isCredits } = getEffectiveSlackAndHint(s.id, auditData.slack, bucketHints);
              return <RequirementSection key={s.id} section={s} slack={effSlack} hint={effHint} isCredits={isCredits} />;
            })}
          </div>
        )}

        {/* Iterates all declared minors — shows a placeholder if no requirement JSON is loaded for one */}
        {(loadedMinors.length > 0 ? loadedMinors : declaredMinors).map((minor) => {
          const minorCode = "code" in minor ? (minor as { code: string }).code : "";
          const minorName = minor.name;
          const minorSections = grouped.minors.find((g) => g.code.includes(minorCode))?.sections ?? [];
          return (
            <div key={minorName} className="di-program-group">
              <h2 className="di-group-title">Minor: {minorName}</h2>
              <p className="di-group-subtitle">
                {minor.catalog_year ? `Catalog ${minor.catalog_year}` : ""}
              </p>
              {minorSections.length > 0 ? (
                minorSections.map((s) => {
                  const { slack: effSlack, hint: effHint, isCredits } = getEffectiveSlackAndHint(s.id, auditData.slack, bucketHints);
                  return <RequirementSection key={s.id} section={s} slack={effSlack} hint={effHint} isCredits={isCredits} />;
                })
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
