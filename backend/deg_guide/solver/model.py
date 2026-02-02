import json
from typing import Dict, List, Set, Any
from ortools.sat.python import cp_model

from .data_types import Course, Requirement, Program
from .compile import build_model

def intvar_upper_bound(v: cp_model.IntVar) -> int:
    dom = list(v.Proto().domain)  # [lb, ub, lb, ub, ...]
    return max(dom[1::2]) if dom else 0


def load_courses(path: str) -> Dict[str, Course]:
    """
    Load course catalog data.

    Supports either:
      - a single JSON file containing a list of course objects, OR
      - a directory containing multiple *.json files (e.g., one per subject),
        each containing a list of course objects.

    Credit handling (easiest path):
      - Keep Course.credits as an int (solver-facing "default" credits).
      - If a course has variable credits, include an optional credits_range object:
          {"min": int, "max": int, "default": int}
        If "default" is omitted, we choose:
          - default = 2 if max == 2, else 4
        Then clamp default into [min, max].
      - If credits is provided as an object (min/max[/default]) or a "1-5" string,
        we derive credits and credits_range from it.
    """
    from pathlib import Path
    import re

    def _choose_default(cmin: int, cmax: int) -> int:
        desired = 2 if cmax == 2 else 4
        return max(cmin, min(desired, cmax))

    def _normalize_credits(row: Dict[str, Any]) -> tuple[int, Any]:
        raw = row.get("credits")
        # Case 1: int-like credits
        if isinstance(raw, (int, float)) or (isinstance(raw, str) and raw.strip().isdigit()):
            return int(raw), None

        # Case 2: object credits {"min":..,"max":.., ...}
        if isinstance(raw, dict):
            cmin = int(raw["min"])
            cmax = int(raw["max"])
            cdef = int(raw.get("default", _choose_default(cmin, cmax)))
            cdef = max(cmin, min(cdef, cmax))
            return cdef, {"min": cmin, "max": cmax, "default": cdef}

        # Case 3: string range like "1-5"
        if isinstance(raw, str):
            m = re.match(r"^\s*(\d+)\s*-\s*(\d+)\s*$", raw)
            if m:
                cmin = int(m.group(1))
                cmax = int(m.group(2))
                cdef = _choose_default(cmin, cmax)
                return cdef, {"min": cmin, "max": cmax, "default": cdef}

        raise ValueError(f"Unsupported credits format for {row.get('id')}: {raw!r}")

    p = Path(path)
    rows: List[Dict[str, Any]] = []

    if p.is_dir():
        for f in sorted(p.glob("*.json")):
            data = json.loads(f.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                raise ValueError(f"{f} must contain a JSON array of courses")
            rows.extend(data)
    else:
        data = json.load(open(path, "r", encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError(f"{path} must contain a JSON array of courses")
        rows = data

    courses: Dict[str, Course] = {}
    for row in rows:
        credits, credits_range = _normalize_credits(row)

        # Alternate easiest format: keep credits as int + add credits_range separately
        if credits_range is None and isinstance(row.get("credits_range"), dict):
            cr = row["credits_range"]
            cmin = int(cr["min"])
            cmax = int(cr["max"])
            cdef = int(cr.get("default", _choose_default(cmin, cmax)))
            cdef = max(cmin, min(cdef, cmax))
            credits_range = {"min": cmin, "max": cmax, "default": cdef}

        c = Course(
            id=row["id"],
            subject=row["subject"],
            number=int(row["number"]),
            credits=int(credits),
            level=int(row["level"]),
            tags=list(row.get("tags", [])),
            credits_range=credits_range,
        )
        if c.id in courses:
            raise ValueError(f"Duplicate course id found while loading catalog: {c.id}")
        courses[c.id] = c

    return courses

def load_program(path: str) -> Program:
    data = json.load(open(path, "r", encoding="utf-8"))
    reqs: List[Requirement] = []
    for r in data["requirements"]:
        reqs.append(Requirement(
            id=r["id"],
            type=r["type"],
            courses=r.get("courses"),
            from_set=r.get("from_set"),
            from_requirements=r.get("from_requirements"),
            k=r.get("k"),
            min_credits=r.get("min_credits"),
            where=r.get("where"),
            constraints=r.get("constraints"),
            must_be=r.get("must_be"),
            exclude_courses=r.get("exclude_courses"),
            exclude_from_set=r.get("exclude_from_set"),
        ))
    return Program(
        id=data["id"],
        name=data["name"],
        requirements=reqs,
        overlap_rules=list(data.get("overlap_rules", [])),
        sets=dict(data.get("sets", {}))
    )

def solve_degree_audit(courses, taken_attempts, programs) -> dict:
    model, x, slack = build_model(courses, taken_attempts, programs)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 3.0
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {"status": "infeasible", "message": "No solution found"}

    attempt_to_course = {a.attempt_id: a.course_id for a in taken_attempts}

    assignments: dict[str, list[dict]] = {}
    for (attempt_id, req_key), var in x.items():
        if solver.Value(var) == 1:
            assignments.setdefault(req_key, []).append({
                "attempt_id": attempt_id,
                "course_id": attempt_to_course.get(attempt_id, attempt_id),
            })

    slack_out = {k: int(solver.Value(v)) for k, v in slack.items()}

    total_slack = sum(slack_out.values())
    total_required = sum(intvar_upper_bound(v) for v in slack.values()) if slack else 0
    completion_ratio = 1.0 if total_required == 0 else max(0.0, 1.0 - total_slack / total_required)

    return {
        "status": "ok",
        "completion_percentage": round(completion_ratio * 100, 1),
        "assignments": assignments,
        "slack": slack_out,
    }