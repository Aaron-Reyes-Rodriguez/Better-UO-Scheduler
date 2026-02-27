from __future__ import annotations

from typing import Dict, List, Set, Tuple
from ortools.sat.python import cp_model
import logging

from .data_types import Course, Requirement, Program, CourseAttempt

logger = logging.getLogger(__name__)


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
    
    max_number = where.get("max_number")
    if max_number is not None and course.number > int(max_number):
        return False

    return True


def eligible_courses_for_req(req: Requirement, program: Program, courses: Dict[str, Course]) -> List[Course]:

    if getattr(req, "from_requirements", None):
        return []

    # 1) explicit list
    if req.courses:
        candidates = [courses[cid] for cid in req.courses if cid in courses]

    # 2) from_set
    elif getattr(req, "from_set", None):
        ids = program.sets.get(req.from_set, [])
        candidates = [courses[cid] for cid in ids if cid in courses]

    # 3) where filter fallback
    else:
        where = req.where or {}
        candidates = [c for c in courses.values() if matches_where(c, where)]

    # ✅ NEW: apply exclusions (MVP)
    excluded_ids = set(req.exclude_courses or [])
    if getattr(req, "exclude_from_set", None):
        excluded_ids.update(program.sets.get(req.exclude_from_set, []))

    if excluded_ids:
        candidates = [c for c in candidates if c.id not in excluded_ids]

    return candidates

def matches_attempt_where(att: CourseAttempt, where: dict | None) -> bool:
    if not where:
        return True
    gb = where.get("grading_basis")
    if gb and getattr(att, "grading_basis", None) != gb:
        return False
    return True

def _slacks_for_req_key(slack: Dict[str, cp_model.IntVar], req_key: str) -> List[cp_model.IntVar]:
    # child slack vars can be stored as:
    # - slack[req_key] for choose_k / credits_at_least / credit_pool
    # - slack[f"{req_key}:{cid}"] for all_of
    out = []
    for k, v in slack.items():
        if k == req_key or k.startswith(req_key + ":"):
            out.append(v)
    return out

def build_model(
    courses: Dict[str, Course],
    #taken_course_ids: Set[str],
    taken_attempts: List[CourseAttempt],
    programs: List[Program],
):
    """
    Build CP-SAT model with x[c, r] assignment vars and requirement constraints.
    """
    logger.debug("=== BUILD MODEL START ===")
    logger.debug(f"Total courses in catalog: {len(courses)}")
    logger.debug(f"Total attempts: {len(taken_attempts)}")
    logger.debug(f"Programs: {[p.id for p in programs]}")
    
    model = cp_model.CpModel()

    # Flatten requirements with unique keys (program_id:req_id)
    reqs: List[Tuple[Program, Requirement]] = []
    for p in programs:
        for r in p.requirements:
            reqs.append((p, r))
    logger.debug(f"Total requirements across all programs: {len(reqs)}")

    # Only allow taken courses to be assigned (MVP)
    #taken_courses = [courses[cid] for cid in taken_course_ids if cid in courses]
    taken_attempt_objs = [
        (att, courses[att.course_id])
        for att in taken_attempts
        if att.course_id in courses
    ]
    logger.debug(f"Matched attempts (found in catalog): {len(taken_attempt_objs)}")

    # Create assignment vars: x[(attempt_id, req_key)] in {0,1}

    x: Dict[Tuple[str, str], cp_model.IntVar] = {}
    

    # Build x vars only when a course is eligible for a requirement

    '''
    for course in taken_courses:
        for program, req in reqs:
            req_key = f"{program.id}:{req.id}"
            elig_ids = {c.id for c in eligible_courses_for_req(req, program, courses)}
            if course.id in elig_ids:
                x[(course.id, req_key)] = model.NewBoolVar(f"x_{course.id}_{req_key}")
    '''
    for att, course in taken_attempt_objs:
        for program, req in reqs:
            
            if getattr(req, "from_requirements", None):
                continue

            req_key = f"{program.id}:{req.id}"
            elig_ids = {c.id for c in eligible_courses_for_req(req, program, courses)}
            
            if req.must_be and not matches_attempt_where(att, req.must_be):
                continue
            
            if course.id in elig_ids:
                x[(att.attempt_id, req_key)] = model.NewBoolVar(f"x_{att.attempt_id}_{req_key}")


    # No double counting WITHIN each program (but allow sharing across programs)
    # This allows BS courses to also count toward Major/Minor requirements
    logger.debug("--- Setting up no-double-counting constraints (per-program) ---")
    for program in programs:
        program_prefix = f"{program.id}:"
        for att, _course in taken_attempt_objs:
            vars_for_att_in_program = [
                var for (aid, req_key), var in x.items() 
                if aid == att.attempt_id and req_key.startswith(program_prefix)
            ]
            if vars_for_att_in_program:
                model.Add(sum(vars_for_att_in_program) <= 1)
    logger.debug(f"Created per-program no-double-counting constraints for {len(programs)} programs")


    # Add constraints per requirement
    # Add constraints per requirement
    slack: Dict[str, cp_model.IntVar] = {}
    slack_bounds: Dict[str, int] = {}  # {req_key: max_possible_slack}

    deferred_meta: List[Tuple[Program, Requirement]] = []

    for program, req in reqs:
        # defer meta requirements for second pass
        if getattr(req, "from_requirements", None):
            deferred_meta.append((program, req))
            continue

        req_key = f"{program.id}:{req.id}"
        elig_course_ids = {c.id for c in eligible_courses_for_req(req, program, courses)}

        vars_for_req = [
            x[(att.attempt_id, req_key)]
            for att, course in taken_attempt_objs
            if course.id in elig_course_ids and (att.attempt_id, req_key) in x
        ]

        if req.type == "all_of":
            required_ids: List[str] = []
            if req.courses:
                required_ids = list(req.courses)
            elif getattr(req, "from_set", None):
                required_ids = list(program.sets.get(req.from_set, []))

            for cid in required_ids:
                matching_attempt_vars = [
                    x[(att.attempt_id, req_key)]
                    for att, course in taken_attempt_objs
                    if course.id == cid and (att.attempt_id, req_key) in x
                ]
                s = model.NewIntVar(0, 1, f"slack_{req_key}_{cid}")
                slack_key = f"{req_key}:{cid}"
                slack[slack_key] = s
                slack_bounds[slack_key] = 1

                # satisfied if any matching attempt assigned, else slack=1
                model.Add(sum(matching_attempt_vars) + s >= 1)

        elif req.type == "choose_k":
            k = int(req.k or 0)
            s = model.NewIntVar(0, k, f"slack_{req_key}")
            slack[req_key] = s
            slack_bounds[req_key] = k
            model.Add(sum(vars_for_req) + s >= k)

        elif req.type == "credits_at_least":
            min_credits = int(req.min_credits or 0)
            s = model.NewIntVar(0, min_credits, f"slack_{req_key}")
            slack[req_key] = s
            slack_bounds[req_key] = min_credits

            credit_sum = sum(
                att.credits_taken * x[(att.attempt_id, req_key)]
                for att, course in taken_attempt_objs
                if course.id in elig_course_ids and (att.attempt_id, req_key) in x
            )
            model.Add(credit_sum + s >= min_credits)

        elif req.type == "credit_pool":
            pool_min = int(req.min_credits or 0)
            s = model.NewIntVar(0, pool_min, f"slack_{req_key}")
            slack[req_key] = s
            slack_bounds[req_key] = pool_min

            pool_credit_sum = sum(
                att.credits_taken * x[(att.attempt_id, req_key)]
                for att, course in taken_attempt_objs
                if course.id in elig_course_ids and (att.attempt_id, req_key) in x
            )
            model.Add(pool_credit_sum + s >= pool_min)

            for j, rule in enumerate(req.constraints or []):
                sub_where_course = rule.get("where") or {}
                sub_where_attempt = rule.get("where_attempt") or None

                subset_sum = sum(
                    att.credits_taken * x[(att.attempt_id, req_key)]
                    for att, course in taken_attempt_objs
                    if course.id in elig_course_ids
                    and (att.attempt_id, req_key) in x
                    and matches_where(course, sub_where_course)
                    and matches_attempt_where(att, sub_where_attempt)
                )

                if "min_credits" in rule:
                    m = int(rule["min_credits"])
                    s2 = model.NewIntVar(0, m, f"slack_{req_key}_submin_{j}")
                    slack_key = f"{req_key}:submin:{j}"
                    slack[slack_key] = s2
                    slack_bounds[slack_key] = m
                    model.Add(subset_sum + s2 >= m)

                if "max_credits" in rule:
                    model.Add(subset_sum <= int(rule["max_credits"]))

        else:
            raise ValueError(f"Unknown requirement type: {req.type}")


    # ---- PASS 2: meta requirements (choose_k from_requirements) ----
    for program, req in deferred_meta:
        req_key = f"{program.id}:{req.id}"

        if req.type == "choose_k":
            k = int(req.k or 0)
            parent_slack = model.NewIntVar(0, k, f"slack_{req_key}")
            slack[req_key] = parent_slack
            slack_bounds[req_key] = k

            sat_vars: List[cp_model.IntVar] = []

            for child_id in (req.from_requirements or []):
                child_key = f"{program.id}:{child_id}"
                child_slacks = _slacks_for_req_key(slack, child_key)

                sat = model.NewBoolVar(f"sat_{req_key}_from_{child_id}")

                if not child_slacks:
                    model.Add(sat == 1)
                    sat_vars.append(sat)
                    continue

                M = 1000
                sum_sl = model.NewIntVar(0, M, f"sumslack_{req_key}_{child_id}")
                model.Add(sum_sl == sum(child_slacks))
                model.Add(sum_sl == 0).OnlyEnforceIf(sat)
                model.Add(sum_sl >= 1).OnlyEnforceIf(sat.Not())
                sat_vars.append(sat)

            model.Add(sum(sat_vars) + parent_slack >= k)

        #added type logic handler that was throwing an error with transcript upload. (2022-2023 json had type all_types which was throwing hands.)
        elif req.type == "all_of":
            # Every child requirement must be satisfied
            all_child_slacks: List[cp_model.IntVar] = []
            total_bound = 0

            for child_id in (req.from_requirements or []):
                child_key = f"{program.id}:{child_id}"
                child_slacks = _slacks_for_req_key(slack, child_key)
                all_child_slacks.extend(child_slacks)
                total_bound += sum(
                    slack_bounds.get(k, 1)
                    for k in slack
                    if k == child_key or k.startswith(child_key + ":")
                )

            bound = max(total_bound, 1)
            parent_slack = model.NewIntVar(0, bound, f"slack_{req_key}")
            slack[req_key] = parent_slack
            slack_bounds[req_key] = bound
            model.Add(parent_slack == sum(all_child_slacks) if all_child_slacks else 0)

        else:
            raise ValueError(f"{req_key}: from_requirements supported for choose_k and all_of only, got '{req.type}'")
        
    model.Minimize(sum(slack.values()) if slack else 0)
    
    logger.debug(f"Model built with {len(x)} assignment variables and {len(slack)} slack variables")
    logger.debug("=== BUILD MODEL END ===")

    return model, x, slack, slack_bounds
