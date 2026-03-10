import json
import logging
from typing import Dict, List, Set, Any
from ortools.sat.python import cp_model

from .data_types import Course, Requirement, Program, CourseAttempt
from .compile import build_model

logger = logging.getLogger(__name__)




def load_courses(path: str) -> tuple[Dict[str, Course], Dict[str, str]]:
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
            equivalents=row.get("equivalents"),
        )
        if c.id in courses:
            raise ValueError(f"Duplicate course id found while loading catalog: {c.id}")
        courses[c.id] = c

    # Build reverse lookup: equivalent_id -> canonical_id
    equiv_map: Dict[str, str] = {}
    for cid, course in courses.items():
        if course.equivalents:
            for eq in course.equivalents:
                if eq not in equiv_map and eq not in courses:
                    equiv_map[eq] = cid

    return courses, equiv_map

def load_program(path: str) -> Program:
    data = json.load(open(path, "r", encoding="utf-8"))
    reqs: List[Requirement] = []
    for r in data["requirements"]:
        reqs.append(Requirement(
            id=r["id"],
            type=r["type"],
            label=r.get("label"),
            user_choice=r.get("user_choice"),
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


def _collect_descendants(req_id: str, req_by_id: Dict[str, "Requirement"], out: Set[str]):
    """Recursively collect all transitive descendant requirement IDs."""
    req = req_by_id.get(req_id)
    if req and req.from_requirements:
        for child_id in req.from_requirements:
            out.add(child_id)
            _collect_descendants(child_id, req_by_id, out)


def _prune_programs(programs: List[Program], selections: Dict[str, str]) -> List[Program]:
    """Remove non-selected branches from user_choice requirements."""
    pruned = []
    for program in programs:
        req_by_id = {r.id: r for r in program.requirements}
        remove_ids: Set[str] = set()

        for req in program.requirements:
            if not req.user_choice or not req.from_requirements:
                continue
            if req.id not in selections:
                continue
            selected_child = selections[req.id]
            for child_id in req.from_requirements:
                if child_id != selected_child:
                    remove_ids.add(child_id)
                    _collect_descendants(child_id, req_by_id, remove_ids)

        if remove_ids:
            filtered_reqs = [r for r in program.requirements if r.id not in remove_ids]
            pruned.append(Program(
                id=program.id,
                name=program.name,
                requirements=filtered_reqs,
                overlap_rules=program.overlap_rules,
                sets=program.sets,
            ))
        else:
            pruned.append(program)
    return pruned


def _has_descendant_assignments(req_id: str, program: Program, assignments: dict) -> bool:
    """Check if a requirement or any of its descendants have solver assignments."""
    key = f"{program.id}:{req_id}"
    if assignments.get(key):
        return True
    req = next((r for r in program.requirements if r.id == req_id), None)
    if req and req.from_requirements:
        return any(_has_descendant_assignments(c, program, assignments) for c in req.from_requirements)
    return False


def solve_degree_audit(courses, taken_attempts, programs, equiv_map: Dict[str, str] = None,
                       selections: Dict[str, str] = None) -> dict:
    logger.debug("=== SOLVE DEGREE AUDIT START ===")

    original_programs = programs
    if selections:
        programs = _prune_programs(programs, selections)
        logger.debug(f"Pruned programs with selections: {selections}")

    # Normalize course IDs using equivalents map
    if equiv_map:
        normalized_attempts = []
        for att in taken_attempts:
            if att.course_id not in courses and att.course_id in equiv_map:
                canonical_id = equiv_map[att.course_id]
                logger.debug(f"Equivalent mapping: {att.course_id} -> {canonical_id}")
                att = CourseAttempt(
                    attempt_id=att.attempt_id,
                    course_id=canonical_id,
                    credits_taken=att.credits_taken,
                    grading_basis=att.grading_basis,
                    term=att.term,
                    subtitle=att.subtitle,
                )
            normalized_attempts.append(att)
        taken_attempts = normalized_attempts
    
    model, x, slack, slack_bounds = build_model(courses, taken_attempts, programs)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 3.0
    
    logger.debug("Running solver...")
    status = solver.Solve(model)
    logger.debug(f"Solver status: {status} (OPTIMAL=4, FEASIBLE=2)")

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        logger.warning("No solution found!")
        return {"status": "infeasible", "message": "No solution found"}

    attempt_to_course = {a.attempt_id: a.course_id for a in taken_attempts}

    assignments: dict[str, list[dict]] = {}
    for (attempt_id, req_key), var in x.items():
        if solver.Value(var) == 1:
            assignments.setdefault(req_key, []).append({
                "attempt_id": attempt_id,
                "course_id": attempt_to_course.get(attempt_id, attempt_id),
            })
    
    # Debug: show which courses are assigned to which requirements
    logger.debug("--- Assignment Results ---")
    for req_key, assigned in assignments.items():
        courses_assigned = [a["course_id"] for a in assigned]
        logger.debug(f"  {req_key}: {courses_assigned}")

    slack_out = {k: int(solver.Value(v)) for k, v in slack.items()}
    
    # Debug: show non-zero slack (unfulfilled requirements)
    logger.debug("--- Slack (unfulfilled) ---")
    for k, v in slack_out.items():
        if v > 0:
            logger.debug(f"  {k}: {v} (needs {v} more)")

    total_slack = sum(slack_out.values())
    total_required = sum(slack_bounds.get(k, 0) for k in slack.keys())
    completion_ratio = 1.0 if total_required == 0 else max(0.0, 1.0 - total_slack / total_required)
    
    logger.debug(f"Total slack: {total_slack}, Total required: {total_required}")
    logger.debug(f"Completion ratio: {completion_ratio:.2%}")
    logger.debug("=== SOLVE DEGREE AUDIT END ===")

    # Categorize meta-requirements (those with from_requirements):
    #   "all_of" parents are structural groupings -> expand: show children, hide parent
    #   "choose_k" parents are selection reqs -> collapse: promote children to parent, hide children
    child_req_ids: Set[str] = set()
    expand_parent_ids: Set[str] = set()

    for program in programs:
        for req in program.requirements:
            if not req.from_requirements:
                continue
            parent_key = f"{program.id}:{req.id}"

            if req.type == "all_of":
                expand_parent_ids.add(parent_key)
            else:
                for child_key_suffix in req.from_requirements:
                    child_key = f"{program.id}:{child_key_suffix}"
                    child_req_ids.add(child_key)
                    child_assigns = assignments.get(child_key, [])
                    if child_assigns:
                        assignments.setdefault(parent_key, []).extend(child_assigns)

    # Hide: choose_k children (promoted to parent) + all_of parents (children shown instead)
    hide_assign = child_req_ids | expand_parent_ids
    filtered_assignments = {k: v for k, v in assignments.items()
                           if k not in hide_assign and not any(k == h or k.startswith(h + ":") for h in child_req_ids)}
    filtered_slack = {k: v for k, v in slack_out.items()
                      if k not in hide_assign
                      and k not in expand_parent_ids
                      and not any(k == c or k.startswith(c + ":") for c in child_req_ids)
                      and not any(k.startswith(p + ":") for p in expand_parent_ids)}

    # Build labels map from requirement definitions (req_key -> label)
    labels: Dict[str, str] = {}
    for program in programs:
        for req in program.requirements:
            if req.label:
                labels[f"{program.id}:{req.id}"] = req.label

    # Build choices metadata from user_choice requirements (use original programs)
    choices: List[Dict[str, Any]] = []
    for program in original_programs:
        for req in program.requirements:
            if not req.user_choice or not req.from_requirements:
                continue
            solver_pick = None
            for child_id in req.from_requirements:
                if _has_descendant_assignments(child_id, program, assignments):
                    solver_pick = child_id
                    break
            options = []
            for child_id in req.from_requirements:
                child_req = next((r for r in program.requirements if r.id == child_id), None)
                child_label = (child_req.label if child_req and child_req.label
                               else child_id.replace("_", " ").title())
                options.append({"id": child_id, "label": child_label})
            choices.append({
                "program_id": program.id,
                "requirement_id": req.id,
                "label": req.label or req.id,
                "options": options,
                "solver_pick": solver_pick,
            })

    return {
        "status": "ok",
        "completion_percentage": round(completion_ratio * 100, 1),
        "assignments": filtered_assignments,
        "slack": filtered_slack,
        "labels": labels,
        "choices": choices,
    }