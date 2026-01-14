from dataclasses import dataclass
from typing import List, Dict, Any, Optional

@dataclass(frozen=True)
class Course:
    id: str
    subject: str
    number: int
    credits: int
    level: int
    tags: List[str]

@dataclass(frozen=True)
class Requirement:
    id: str
    type: str  # "all_of" | "choose_k" | "credits_at_least"
    courses: Optional[List[str]] = None
    k: Optional[int] = None
    min_credits: Optional[int] = None
    where: Optional[Dict[str, Any]] = None

@dataclass(frozen=True)
class Program:
    id: str
    name: str
    requirements: List[Requirement]
    overlap_rules: List[Dict[str, Any]]
