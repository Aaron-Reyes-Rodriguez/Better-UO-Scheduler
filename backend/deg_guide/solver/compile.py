from __future__ import annotations
from typing import Dict, List, Set, Tuple
from ortools.sat.python import cp_model

from .data_types import Course, Requirement, Program

def matches_where(course: Course, where: dict | None) -> bool:
    if not where:
        return True
    tags_any = where.get("tags_any")
    if tags_any:
        if not any(t in course.tags for t in tags_any):
            return False
    # extend later: subject, level >=, credits, etc.
    return True

def eligible_courses_for_req(req: Requirement, courses: Dict[str, Course]) -> List[Course]:
    if req.courses:
        return [courses[cid] for cid in req.courses if cid in courses]
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
    reqs: List[Tuple[str, Requirement]] = []
    for p in programs:
        for r in p.requirements:
            reqs.append((p.id, r))

    # Create assignment vars: x[(course_id, req_key)] in {0,1}
    x: Dict[Tuple[str, str], cp_model.IntVar] = {}

    # Only allow taken courses to be assigned (MVP). Later you can add planned courses y_c.
    taken_courses = [courses[cid] for cid in taken_course_ids if cid in courses]

    for course in taken_courses:
        for pid, req in reqs:
            req_key = f"{pid}:{req.id}"
            # Only create var if course is eligible for that requirement
            elig = course in eligible_courses_for_req(req, courses)
            if elig:
                x[(course.id, req_key)] = model.NewBoolVar(f"x_{course.id}_{req_key}")

    # No double counting across ALL requirements by default:
    # For each course, sum over all req buckets <= 1
    for course in taken_courses:
        vars_for_course = [var for (cid, _), var in x.items() if cid == course.id]
        if vars_for_course:
            model.Add(sum(vars_for_course) <= 1)

    # Add constraints per requirement
    slack: Dict[str, cp_model.IntVar] = {}

    for pid, req in reqs:
        req_key = f"{pid}:{req.id}"
        elig_courses = eligible_courses_for_req(req, courses)
        vars_for_req = [x[(c.id, req_key)] for c in elig_courses if (c.id, req_key) in x]

        if req.type == "all_of":
            # each specified course must be assigned to this req
            # (for all_of we expect req.courses to be set)
            for cid in (req.courses or []):
                if (cid, req_key) in x:
                    model.Add(x[(cid, req_key)] == 1)
                else:
                    # course not taken or not in catalog -> create slack 1 for missing course
                    s = model.NewIntVar(0, 1, f"slack_{req_key}_{cid}")
                    slack[f"{req_key}:{cid}"] = s
                    # force slack to 1 (missing)
                    model.Add(s == 1)

        elif req.type == "choose_k":
            k = int(req.k or 0)
            # slack = max(0, k - sum(vars_for_req))
            s = model.NewIntVar(0, k, f"slack_{req_key}")
            slack[req_key] = s
            model.Add(sum(vars_for_req) + s >= k)

        elif req.type == "credits_at_least":
            min_credits = int(req.min_credits or 0)
            # sum(credits * x) + slack >= min_credits
            s = model.NewIntVar(0, min_credits, f"slack_{req_key}")
            slack[req_key] = s
            model.Add(sum(c.credits * x[(c.id, req_key)]
                          for c in elig_courses
                          if (c.id, req_key) in x) + s >= min_credits)

        else:
            raise ValueError(f"Unknown requirement type: {req.type}")

    # Objective: minimize total slack (i.e., maximize completion)
    model.Minimize(sum(slack.values()) if slack else 0)

    return model, x, slack
