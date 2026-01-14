import json
from typing import Dict, List, Set, Any
from ortools.sat.python import cp_model

from .data_types import Course, Requirement, Program
from .compile import build_model

def load_courses(path: str) -> Dict[str, Course]:
    data = json.load(open(path, "r", encoding="utf-8"))
    courses = {}
    for row in data:
        c = Course(
            id=row["id"],
            subject=row["subject"],
            number=int(row["number"]),
            credits=int(row["credits"]),
            level=int(row["level"]),
            tags=list(row.get("tags", [])),
        )
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
            k=r.get("k"),
            min_credits=r.get("min_credits"),
            where=r.get("where"),
        ))
    return Program(
        id=data["id"],
        name=data["name"],
        requirements=reqs,
        overlap_rules=list(data.get("overlap_rules", [])),
    )

def solve_degree_audit(
    courses: Dict[str, Course],
    taken: Set[str],
    programs: List[Program],
) -> dict:
    model, x, slack = build_model(courses, taken, programs)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 3.0  # keep snappy for API
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {"status": "infeasible", "message": "No solution found"}

    # Build assignment results
    assignments = {}
    for (cid, req_key), var in x.items():
        if solver.Value(var) == 1:
            assignments.setdefault(req_key, []).append(cid)

    slack_out = {k: int(solver.Value(v)) for k, v in slack.items()}

    # Simple completion score: 1 - (slack / total_required)
    total_slack = sum(slack_out.values())
    # total_required is not perfect here; good enough MVP: use slack upper bounds
    total_required = sum(v.Proto().domain[-1] for v in slack.values()) if slack else 0
    completion = 1.0 if total_required == 0 else max(0.0, 1.0 - total_slack / total_required)

    return {
        "status": "ok",
        "completion precentage": completion,
        "assignments": assignments,
        "slack": slack_out,
    }
