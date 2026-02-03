import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import pdfplumber

# -------- patterns --------
GRADE_RE = r"(?:A\+|A-|A|B\+|B-|B|C\+|C-|C|D\+|D-|D|F|P\*|P|NP|W|IP)"
TERM_RE = r"(Fall|Winter|Spring|Summer)\s+\d{4}"

TERM_TO_CODE = {"Fall": "F", "Winter": "W", "Spring": "S", "Summer": "U"}  # U=summer


@dataclass
class ParsedLine:
    course_id: str      # "MATH251"
    term_text: str      # "Winter 2026"
    credits: Optional[float]
    grade: str          # "A-" / "IP" / "P*" / etc.
    status: str         # "completed" | "in_progress" | "unknown"
    grading_basis: str  # "graded" | "pass_fail" | "unknown"


def extract_pdf_text(path: str) -> str:
    chunks: List[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            chunks.append(page.extract_text() or "")
    return "\n".join(chunks)


def canonical_course_id(subj: str, num: str) -> str:
    return f"{subj.strip().upper()}{int(num)}"


def parse_float_maybe(s: str) -> Optional[float]:
    s = s.strip().strip("()")
    try:
        return float(s)
    except ValueError:
        return None


def term_to_attempt_prefix(term_text: str) -> str:
    # "Winter 2026" -> "2026W"
    season, year = term_text.split()
    return f"{int(year)}{TERM_TO_CODE.get(season, 'X')}"


def grade_to_grading_basis(grade: str) -> str:
    # Adjust if your school uses different tokens
    if grade in {"P", "P*", "NP"}:
        return "pass_fail"
    if grade == "W":
        return "graded"  # withdrew still from a graded course typically; change if you want "unknown"
    if grade == "IP":
        return "graded"  # most in-progress are graded; change if you can detect otherwise
    return "graded"


def normalize_grade_and_credits(raw_grade: str, raw_credits: str) -> Tuple[str, Optional[float], str]:
    raw_grade = raw_grade.strip()

    # handle "IP (4)" if merged
    m = re.match(r"^(IP)\s*\(([\d.]+)\)$", raw_grade)
    if m:
        return "IP", parse_float_maybe(m.group(2)), "in_progress"

    if raw_grade == "IP":
        return "IP", parse_float_maybe(raw_credits), "in_progress"

    return raw_grade, parse_float_maybe(raw_credits), "completed"


def parse_course_lines(text: str) -> List[ParsedLine]:
    """
    Matches rows like:
      "MATH 251 Calculus I A- 4 Winter 2026"
      "COLT 212 Top Comp Wrld Cinema IP (4) Winter 2026"
    """
    course_line_re = re.compile(
        rf"(?m)^(?P<subj>[A-Z]{{2,5}})\s+(?P<num>\d{{2,3}})\s+"
        rf"(?P<title>.+?)\s+"
        rf"(?P<grade>{GRADE_RE}(?:\s*\([\d.]+\))?)\s+"
        rf"(?P<credits>\(?[\d.]+\)?)\s+"
        rf"(?P<term>{TERM_RE})"
        rf".*$"
    )

    out: List[ParsedLine] = []
    for m in course_line_re.finditer(text):
        course_id = canonical_course_id(m.group("subj"), m.group("num"))
        raw_grade = m.group("grade")
        raw_credits = m.group("credits")
        term_text = m.group("term")

        grade, credits, status = normalize_grade_and_credits(raw_grade, raw_credits)
        grading_basis = grade_to_grading_basis(grade)

        out.append(
            ParsedLine(
                course_id=course_id,
                term_text=term_text,
                credits=credits,
                grade=grade,
                status=status,
                grading_basis=grading_basis,
            )
        )
    return out


def build_attempts_and_grades(lines: List[ParsedLine]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    - taken_attempts: list of {attempt_id, course_id, credits_taken, grading_basis}
    - class_grades: dict keyed by attempt_id -> {course_id, grade, status}
    """
    taken_attempts: List[Dict[str, Any]] = []
    class_grades: Dict[str, Any] = {}

    # Count sections per term+course so repeats become -02, -03, etc.
    counter: Dict[Tuple[str, str], int] = {}

    for ln in lines:
        term_prefix = term_to_attempt_prefix(ln.term_text)
        key = (term_prefix, ln.course_id)
        counter[key] = counter.get(key, 0) + 1
        section = f"{counter[key]:02d}"  # 01, 02, ...

        attempt_id = f"{term_prefix}-{ln.course_id}-{section}"

        taken_attempts.append(
            {
                "attempt_id": attempt_id,
                "course_id": ln.course_id,
                "credits_taken": int(ln.credits) if ln.credits is not None else 0,
                "grading_basis": ln.grading_basis,
            }
        )

        class_grades[attempt_id] = {
            "course_id": ln.course_id,
            "grade": ln.grade,
            "status": ln.status,  # "completed" or "in_progress"
        }

    return taken_attempts, class_grades


def parse_broad_data(text: str) -> Dict[str, Any]:
    def grab(pattern: str) -> Optional[str]:
        m = re.search(pattern, text, flags=re.IGNORECASE)
        return m.group(1).strip() if m else None

    broad: Dict[str, Any] = {}

    # --- program / level ---
    # Typical DegreeWorks-ish: "Program <...> College <...>"
    broad["program"] = grab(r"\bProgram\s+(.+?)\s+College\b")
    broad["level"] = grab(r"\bLevel\s+([A-Za-z]+)\b")  # Undergraduate/Graduate/etc

    # --- GPA ---
    gpa = grab(r"\bUO GPA\s+([0-9.]+)\b") or grab(r"\bGPA\s+([0-9.]+)\b")
    broad["gpa"] = float(gpa) if gpa else None

    # --- earned credits ---
    earned = grab(r"\bEarned Credits\s+([0-9.]+)\b")
    broad["earned_credits"] = float(earned) if earned else None

    # --- catalog year ---
    # Try multiple patterns because PDFs differ
    catalog_year = (
        grab(r"\bCatalog Year\s+(\d{4}\s*-\s*\d{4})\b")
        or grab(r"\bCatalog\s+(\d{4}\s*-\s*\d{4})\b")
        or grab(r"\b(\d{4}\s*-\s*\d{4})\s+UO catalog\b")
    )
    # Normalize spacing: "2025 - 2026" -> "2025-2026"
    if catalog_year:
        catalog_year = re.sub(r"\s*", "", catalog_year)  # remove all spaces
    broad["catalog_year"] = catalog_year

    # --- major/minors ---
    major = grab(r"\bMajor\s+(.+?)\s+Minors\b")
    minors_raw = grab(r"\bMinors\s+(.+?)\s+Academic Standing\b")

    # minors list split
    minors_list: List[str] = []
    if minors_raw:
        minors_list = [m.strip() for m in minors_raw.split(",") if m.strip()]

    # Build recommended structure (with catalog year on each)
    broad["declared_major"] = (
        {"name": major, "catalog_year": catalog_year}
        if major
        else None
    )

    broad["minors"] = [
        {"name": m, "catalog_year": catalog_year}
        for m in minors_list
    ]

    # You can keep catalog_year inside broad_data or drop it.
    # If you ONLY want it attached to major/minors, uncomment next line:
    # broad.pop("catalog_year", None)

    return broad

def parse_transcript_pdf(path: str) -> Dict[str, Any]:
    text = extract_pdf_text(path)
    
    broad_data = parse_broad_data(text)
    '''
    # keep this minimal; expand as you like
    broad_data = {}
    # example broad fields (optional)
    m = re.search(r"Student name\s+(.+?)\n", text, flags=re.IGNORECASE)
    if m:
        broad_data["student_name"] = m.group(1).strip()
    m = re.search(r"Student ID\s+(\d+)", text, flags=re.IGNORECASE)
    if m:
        broad_data["student_id"] = m.group(1).strip()
    '''
    lines = parse_course_lines(text)
    taken_attempts, class_grades = build_attempts_and_grades(lines)

    return {
        "broad_data": broad_data,
        "taken_attempts": taken_attempts,
        "class_grades": class_grades,
    }


if __name__ == "__main__":
    result = parse_transcript_pdf("deg_guide/data/records/Test_Transcript.pdf")
    print("attempts:", len(result["taken_attempts"]))
    print(result["taken_attempts"][:3])
    # print(result["class_grades"])
