"""
File: data_types.py
Purpose: Define the core data structures used by the degree audit solver.
Authors: Daniel Asiamah

System: Better-UO-Scheduler (Quackademics)
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass(frozen=True)
class Course:
    """Represents a catalog course definition with parsing-friendly traits."""
    id: str
    subject: str
    number: int
    credits: int
    level: int
    tags: List[str]
    credits_range: Optional[Dict[str, int]] = None  # {"min": int, "max": int, "default": int}
    equivalents: Optional[List[str]] = None  # ["MATH251", "MATH241"] - older/alternate course IDs

@dataclass(frozen=True)
class Requirement:
    """Represents a specific degree requirement rule (all_of, choose_k, etc)."""
    id: str
    type: str  # "all_of" | "choose_k" | "credits_at_least" | "credit_pool"
    label: Optional[str] = None                        # human-readable name for frontend display
    user_choice: Optional[bool] = None                   # if True, frontend shows a dropdown for this choose_k
    courses: Optional[List[str]] = None
    from_set: Optional[str] = None
    from_requirements: Optional[List[str]] = None   
    k: Optional[int] = None
    min_credits: Optional[int] = None
    where: Optional[Dict[str, Any]] = None
    constraints: Optional[List[Dict[str, Any]]] = None
    must_be: Optional[Dict[str, Any]] = None
    exclude_courses: Optional[List[str]] = None        # explicit course ids to exclude
    exclude_from_set: Optional[str] = None             # name of a program.sets[] list to exclude

@dataclass(frozen=True)
class Program:
    """Represents an entire degree program composed of rule sets and requirements."""
    id: str
    name: str
    requirements: List[Requirement]
    overlap_rules: List[Dict[str, Any]]
    sets: Dict[str, List[str]] = field(default_factory=dict)


@dataclass(frozen=True)
class CourseAttempt:
    """Represents a student's attempt at a course from the parsed transcript."""
    attempt_id: str          # unique per transcript row (term+course+section, etc.)
    course_id: str           # "CS422"
    credits_taken: int
    grading_basis: str       # "graded" | "pnp"
    term: str | None = None
    subtitle: str | None = None
    grade: str | None = None  # letter grade: "A", "B-", "C+", etc.; or "P", "P*", "NP", "W", "IP"

