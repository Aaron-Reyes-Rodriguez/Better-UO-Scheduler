from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass(frozen=True)
class Course:
    id: str
    subject: str
    number: int
    credits: int
    level: int
    tags: List[str]
    credits_range: Optional[Dict[str, int]] = None  # {"min": int, "max": int, "default": int}

@dataclass(frozen=True)
class Requirement:
    id: str
    type: str  # "all_of" | "choose_k" | "credits_at_least" | "credit_pool"
    courses: Optional[List[str]] = None
    from_set: Optional[str] = None
    from_requirements: Optional[List[str]] = None   
    k: Optional[int] = None
    min_credits: Optional[int] = None
    where: Optional[Dict[str, Any]] = None
    constraints: Optional[List[Dict[str, Any]]] = None
    must_be: Optional[Dict[str, Any]] = None
    exclude_courses: Optional[List[str]] = None      # explicit course ids to exclude
    exclude_from_set: Optional[str] = None           # name of a program.sets[] list to exclude

@dataclass(frozen=True)
class Program:
    id: str
    name: str
    requirements: List[Requirement]
    overlap_rules: List[Dict[str, Any]]
    sets: Dict[str, List[str]] = field(default_factory=dict)


@dataclass(frozen=True)
class CourseAttempt:
    attempt_id: str          # unique per transcript row (term+course+section, etc.)
    course_id: str           # "CS422"
    credits_taken: int
    grading_basis: str       # "graded" | "pnp"
    term: str | None = None
    subtitle: str | None = None

