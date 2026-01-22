from __future__ import annotations

from typing import Dict, List, Set, Tuple
from ortools.sat.python import cp_model

from .data_types import Course, Requirement, Program


def matches_where(course: Course, where: dict | None) -> bool:
    """
    MVP filter. Keep tags_any for now, but you can add:
      - subject / subject_in
      - min_number / max_number
      - min_level
      - etc.
    """
    if not where:
        return True

    tags_any = where.get("tags_any")
    if tags_any:
        if not any(t in course.tags for t in tags_any):
            return False

    subject = where.get("subject")
    if subject and course.subject != subject:
        return False

    subject_in = where.get("subject_in")
    if subject_in and course.subject not in subject_in:
        return False

    min_number = where.get("min_number")
    if min_number is not None and course.number < int(min_number):
        return False

    return True


def eligible_courses_for_req(req: Requirement, program: Program, courses: Dict[str, Course]) -> List[Course]:
    # 1) explicit list
    if req.courses:
        return [courses[cid] for cid in req.courses if cid in courses]

    # 2) from_set (NEW)
    if getattr(req, "from_set", None):
        ids = program.sets.get(req.from_set, [])
        return [courses[cid] for cid in ids if cid in courses]

    # 3) where filter fallback
    where = req.where or {}
    return [c for c in courses.values() if matches_where(c, where)]


def build_model(
    courses: Dict[str, Course],
    taken_course_ids: Set[str],
    programs: List[Program],
):
    """
    Build CP-SAT model with x[c, r] assignment vars and requirement constraints.
    """
    model = cp_model.CpModel()

    # Flatten requirements with unique keys (program_id:req_id)
    reqs: List[Tuple[Program, Requirement]] = []
    for p in programs:
        for r in p.requirements:
            reqs.append((p, r))

    # Only allow taken courses to be assigned (MVP)
    taken_courses = [courses[cid] for cid in taken_course_ids if cid in courses]

    # Create assignment vars: x[(course_id, req_key)] in {0,1}
    x: Dict[Tuple[str, str], cp_model.IntVar] = {}

    # Build x vars only when a course is eligible for a requirement
    for course in taken_courses:
        for program, req in reqs:
            req_key = f"{program.id}:{req.id}"
            elig_ids = {c.id for c in eligible_courses_for_req(req, program, courses)}
            if course.id in elig_ids:
                x[(course.id, req_key)] = model.NewBoolVar(f"x_{course.id}_{req_key}")

    # No double counting across ALL requirements by default:
    # For each course, sum over all req buckets <= 1
    for course in taken_courses:
        vars_for_course = [var for (cid, _), var in x.items() if cid == course.id]
        if vars_for_course:
            model.Add(sum(vars_for_course) <= 1)

    # Add constraints per requirement
    slack: Dict[str, cp_model.IntVar] = {}

    for program, req in reqs:
        req_key = f"{program.id}:{req.id}"
        elig_courses = eligible_courses_for_req(req, program, courses)
        vars_for_req = [x[(c.id, req_key)] for c in elig_courses if (c.id, req_key) in x]

        if req.type == "all_of":
            # each specified course must be assigned to this req
            # (for all_of we expect req.courses or req.from_set to specify exact required courses)
            required_ids: List[str] = []
            if req.courses:
                required_ids = list(req.courses)
            elif getattr(req, "from_set", None):
                required_ids = list(program.sets.get(req.from_set, []))

            for cid in required_ids:
                if (cid, req_key) in x:
                    model.Add(x[(cid, req_key)] == 1)
                else:
                    # course not taken or not in catalog -> create slack 1 for missing course
                    s = model.NewIntVar(0, 1, f"slack_{req_key}_{cid}")
                    slack[f"{req_key}:{cid}"] = s
                    model.Add(s == 1)

        elif req.type == "choose_k":
            k = int(req.k or 0)
            s = model.NewIntVar(0, k, f"slack_{req_key}")
            slack[req_key] = s
            model.Add(sum(vars_for_req) + s >= k)

        elif req.type == "credits_at_least":
            min_credits = int(req.min_credits or 0)
            s = model.NewIntVar(0, min_credits, f"slack_{req_key}")
            slack[req_key] = s

            credit_sum = sum(
                c.credits * x[(c.id, req_key)]
                for c in elig_courses
                if (c.id, req_key) in x
            )
            model.Add(credit_sum + s >= min_credits)

        else:
            raise ValueError(f"Unknown requirement type: {req.type}")

    # Objective: minimize total slack (i.e., maximize completion)
    model.Minimize(sum(slack.values()) if slack else 0)

    return model, x, slack
