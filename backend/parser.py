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
    # Preserve things like "110T" -> "PS110T" (can't int() those)
    return f"{subj.strip().upper()}{num.strip().upper()}"


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

def strip_disallowed_sections(text: str) -> str:
    """
    Remove blocks that should NOT contribute to the degree:
    - Excess credits
    - Insufficient - Does not count towards degree
    - Over The Limit - Does not count towards degree

    Keep In-progress (it counts as planned/in-progress courses).
    """
    disallowed_headers = [
        r"Excess credits",
        r"Insufficient\s*-\s*Does not count towards degree",
        r"Over The Limit\s*-\s*Does not count towards degree",
    ]

    # Start cutting from each disallowed header until the next known header OR end of file.
    # Known “next headers” at end of the PDF:
    # - In-progress
    # - Legend
    # - Disclaimer
    # - (or another disallowed header)
    next_header = r"(?:In-progress|Legend|Disclaimer|" + "|".join(disallowed_headers) + r")"

    cleaned = text
    for hdr in disallowed_headers:
        cleaned = re.sub(
            rf"(?is)\b{hdr}\b.*?(?=\b{next_header}\b|$)",
            "",
            cleaned,
        )
    return cleaned


def parse_course_lines(text: str) -> List[ParsedLine]:
    """
    Match course attempts anywhere in a line, not only when the line starts with SUBJECT NUMBER.

    This catches rows like:
      "College Composition II/III WR 122 College Composition II A- 4 Spring 2023"
      "Computer Science I CS 210 Computer Science I A 4 Fall 2023"
      "PS 110T Social Science Group B 4.5 Fall 2020"
      "GEOG 120T Science A 6 Fall 2020"
      "COLT 212 ... IP (4) Winter 2026"
    """

    # Course number: allow trailing letter(s) (110T, 345M, 372M) so "372M" is not parsed as "372".
    # Credits: allow decimals (4.5) and parentheses (IP (4))

    text = strip_disallowed_sections(text)
    
    course_anywhere_re = re.compile(
        rf"(?m)"
        rf"(?P<subj>[A-Z]{{2,5}})\s+"
        rf"(?P<num>\d{{2,3}}[A-Z]*)\s+"
        rf"(?P<title>[^\n]+?)\s+"
        rf"(?P<grade>{GRADE_RE}(?:\s*\([\d.]+\))?)\s+"
        rf"(?P<credits>\(?[\d.]+\)?)\s+"
        rf"(?P<term>{TERM_RE})\b"
    )

    out: List[ParsedLine] = []
    for m in course_anywhere_re.finditer(text):
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
    seen = set()
    deduped: List[ParsedLine] = []
    for ln in out:
        key = (ln.course_id, ln.term_text, ln.grade, ln.credits)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(ln)
    return deduped

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


TERM_RE = r"(?:Fall|Winter|Spring|Summer)\s+\d{4}"
YEAR_RANGE_RE = r"\d{4}\s*-\s*\d{4}"
CATALOG_RE = rf"(?:{YEAR_RANGE_RE}|{TERM_RE})"


def parse_broad_data(text: str) -> Dict[str, Any]:
    def grab(pattern: str) -> Optional[str]:
        m = re.search(pattern, text, flags=re.IGNORECASE)
        return m.group(1).strip() if m else None

    def norm_catalog(s: Optional[str]) -> Optional[str]:
        if not s:
            return None
        if re.fullmatch(YEAR_RANGE_RE, s.strip()):
            return re.sub(r"\s*", "", s)  # "2022 - 2023" -> "2022-2023"
        return s.strip()
    
    def clean_name(s: Optional[str]) -> Optional[str]:
        if not s:
            return None
        s = s.strip()
        # Remove trailing tokens that DegreeWorks PDFs sometimes append
        s = re.sub(r"\s+(section|requirement[s]?|block[s]?)\s*$", "", s, flags=re.IGNORECASE)
        return s.strip()

    broad: Dict[str, Any] = {}

    # -------------------------
    # Student name (strip trailing "Degree progress")
    # -------------------------
    name = grab(r"\bStudent name\s+([^\n]+)")
    if name:
        name = re.sub(r"\s+Degree progress\s*$", "", name, flags=re.IGNORECASE).strip()
    broad["student_name"] = name

    # -------------------------
    # Program / Level
    # -------------------------
    program = grab(r"\bProgram\s+(.+?)\s+College\b")
    broad["program"] = program.rstrip("-").strip() if program else None
    broad["level"] = grab(r"\bLevel\s+([A-Za-z]+)\b")

    # -------------------------
    # GPA (handle same-line OR next-line)
    # -------------------------
    gpa = (
        grab(r"\bUO GPA\s+([0-9.]+)\b")
        or grab(r"\bUO GPA\s*\n\s*([0-9.]+)\b")
        or grab(r"\bCumulative GPA\s+([0-9.]+)\b")
        or grab(r"\bOverall GPA\s+([0-9.]+)\b")
        or grab(r"\bUO GPA:\s*([0-9.]+)\b")
        or grab(r"\bGPA:\s*([0-9.]+)\b")
    )
    broad["gpa"] = float(gpa) if gpa else None

    # -------------------------
    # Earned credits
    # -------------------------
    earned = grab(r"\bEarned Credits\s+([0-9.]+)\b")
    broad["earned_credits"] = float(earned) if earned else None

    # -------------------------
    # Degree-level catalog year (Degree in ...)
    # Capture degree title on one line, then find catalog year later in the same block
    # -------------------------
    degree_block = re.search(
        rf"(?is)\bDegree in[^\n]*\n.*?\bCatalog year:\s*(?P<catalog>{CATALOG_RE})",
        text,
    )
    broad["catalog_year"] = norm_catalog(degree_block.group("catalog")) if degree_block else None

    # -------------------------
    # Major(s) – support double (or more) majors (Major in <name> ... Catalog year: <...>)
    # Capture name only to end-of-line; use finditer to get every block.
    # -------------------------
    majors_list: List[Dict[str, Optional[str]]] = []
    for mb in re.finditer(
        rf"(?is)\bMajor in\s+(?P<name>[^\n]+).*?\bCatalog year:\s*(?P<catalog>{CATALOG_RE})",
        text,
    ):
        nm = clean_name(mb.group("name"))
        if not nm:
            continue
        cy = norm_catalog(mb.group("catalog"))
        majors_list.append({"name": nm, "catalog_year": cy})
    broad["declared_majors"] = majors_list
    broad["declared_major"] = majors_list[0] if majors_list else None

    # -------------------------
    # Minors (Minor in <name> ... Catalog year: <...>)
    # Again capture name ONLY to end-of-line.
    # Use a dict to de-duplicate by name.
    # -------------------------
    minors_map: Dict[str, str] = {}
    for mb in re.finditer(
        rf"(?is)\bMinor in\s+(?P<name>[^\n]+).*?\bCatalog year:\s*(?P<catalog>{CATALOG_RE})",
        text,
    ):
        #nm = mb.group("name").strip()
        nm = clean_name(mb.group("name"))
        if not nm:
            continue
        cy = norm_catalog(mb.group("catalog"))
        # keep first occurrence per name (or overwrite—either is fine; choose overwrite to be safe)
        minors_map[nm] = cy

    broad["minors"] = [{"name": n, "catalog_year": minors_map[n]} for n in sorted(minors_map.keys())]

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
