"""
File: app.py
Purpose: Main FastAPI application server for the Quackademics / Better-UO-Scheduler
         backend. Defines all REST API routes, handles transcript upload and PDF
         parsing, runs the degree-audit solver, manages professor tags via a
         PostgreSQL database, and provides class/professor lookup endpoints.
Created: 2024
Authors: Aaron Reyes-Rodriguez, Daniel Asiamah

System: Better-UO-Scheduler (Quackademics)
  This file is the entry point for the Python backend service (run with uvicorn).
  It imports the degree-audit solver from the deg_guide package, the transcript
  PDF parser from parser.py, and the data-access helpers from
  apiHelperFunctions.py.  The frontend React application (frontend/) communicates
  exclusively with the endpoints defined here.
"""

# ── Standard-library imports ────────────────────────────────────────────────
from fastapi import FastAPI, UploadFile, HTTPException, Query
# asyncio: provides event-loop utilities used when running the PDF parser in a
# separate process so it does not block the async server.
import asyncio
# ProcessPoolExecutor: spawns a child process for CPU-bound PDF parsing so that
# the async event loop remains unblocked during heavy computation.
from concurrent.futures import ProcessPoolExecutor
# CORSMiddleware: allows the browser-based React frontend (on a different origin)
# to call this API without being blocked by the browser's same-origin policy.
from fastapi.middleware.cors import CORSMiddleware
# BaseModel: Pydantic base class used to define strongly-typed request bodies
# that FastAPI automatically validates and parses from incoming JSON.
from pydantic import BaseModel
# typing helpers used for type annotations throughout the module.
from typing import List, Optional, Dict, Any
import os
import re
import logging
from dotenv import load_dotenv

# Load .env file so local developers get DATABASE_URL, CORS_ORIGINS, etc.
# In production the real env vars take precedence.
load_dotenv()

# deg_guide solver: internal library that evaluates which degree requirements a
# student has satisfied given their course history.
from deg_guide.solver.model import load_courses, load_program, solve_degree_audit
# CourseAttempt: data-class representing a single course attempt (grade, term …)
from deg_guide.solver.data_types import CourseAttempt
# parse_transcript_pdf: OCR/regex-based parser that extracts course data from a
# Ducks-On-Track PDF transcript.
from parser import parse_transcript_pdf
# apiHelper: helper module providing class/professor lookup and database access.
import apiHelperFunctions as apiHelper
from pathlib import Path
import tempfile
import uuid
# psycopg2: PostgreSQL adapter used for direct database operations (health-check,
# professor-tags table management via apiHelperFunctions).
import psycopg2

# Configure logging with more readable format
logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

def log_section(title: str):
    """
    Log a prominent section header to make the server output easier to read.

    Args:
        title (str): The section title to display inside the header box.

    Returns:
        None
    """
    logger.info("=" * 60)
    logger.info(f"  {title}")
    logger.info("=" * 60)

# 1. CRITICAL FOR RENDER: Create the directory if it doesn't exist
UPLOAD_DIR = Path(tempfile.gettempdir()) / 'uploadTranscript'
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app = FastAPI(root_path="/api")

# Allow frontend (e.g. AWS Amplify) to call this API when backend is on Render
ALLOWED_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:5173, http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in ALLOWED_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    """Simple ping to check the API is up (e.g. for Render)."""
    return {"status": "ok"}

@app.get("/db-health")
def db_health():
    """Check database connectivity."""
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise HTTPException(status_code=500, detail="DATABASE_URL is not set")
    try:
        conn = psycopg2.connect(db_url, connect_timeout=5)
        conn.close()
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB connection failed: {str(e)}")

@app.get("/class/{class_id}")
def get_class(class_id: str):
  """
  Retrieve grade-distribution and statistics for a single class.

  Args:
      class_id (str): The course identifier (e.g. "CS210" or "CS 210").

  Returns:
      dict: Class data including grade distribution and stats.

  Raises:
      HTTPException 404: If the class is not found in the data.
  """
  try:
    return apiHelper.classFinder(class_id)
  except KeyError:
    raise HTTPException(status_code=404, detail=f"Class not found: {class_id}")

@app.get("/professor/{professor_id}")
def get_professor(professor_id: str):
  """
  Retrieve data for a single professor, including grade distribution, stats,
  and student-voted tags from the database.

  Args:
      professor_id (str): The professor's identifier or display name.

  Returns:
      dict: Professor record with grade data and tags list.

  Raises:
      HTTPException 404: If the professor is not found.
  """
  try:
    return apiHelper.professorFinder(professor_id)
  except KeyError:
    raise HTTPException(status_code=404, detail=f"Professor not found: {professor_id}")


class ProfessorTagsRequest(BaseModel):
    """
    Request body for the POST /professor/{professor_id}/tags endpoint.

    Attributes:
        tags (List[str]): List of tag display-names the student is voting for
            (e.g. ["Tough Grader", "Caring"]).
    """
    tags: List[str]

@app.post("/professor/{professor_id}/tags")
def update_professor_tags(professor_id: str, req: ProfessorTagsRequest):
    """
    Increment tag vote counts for a professor in the PostgreSQL database.

    Args:
        professor_id (str): The professor's identifier or display name.
        req (ProfessorTagsRequest): JSON body containing a list of tag names.

    Returns:
        dict: {"status": "success", "tags": <updated list of TagWithCount dicts>}

    Raises:
        HTTPException 404: If the professor is not found.
    """
    try:
        updated_tags = apiHelper.updateProfessorTags(professor_id, req.tags)
        return {"status": "success", "tags": updated_tags}
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Professor not found: {professor_id}")

@app.get("/class/{class_id}/professors")
def get_class_professors(class_id: str, limit: int = Query(default=50, ge=1, le=200)):
    """Return professors who taught a class (ordered by total students)."""
    return {"results": apiHelper.classProfessors(class_id, limit)}


@app.get("/suggest/classes")
def suggest_classes(q: str = Query(default="", min_length=1), limit: int = Query(default=8, ge=1, le=20)):
    """
    Return typeahead suggestions for course names matching a partial query.

    Args:
        q (str): Partial course name or ID to search for (minimum 1 character).
        limit (int): Maximum number of results to return (1–20, default 8).

    Returns:
        dict: {"results": [<course name>, ...]}
    """
    return {"results": apiHelper.classSuggestions(q, limit)}


@app.get("/suggest/professors")
def suggest_professors(q: str = Query(default="", min_length=1), limit: int = Query(default=8, ge=1, le=20)):
    """
    Return typeahead suggestions for professor names matching a partial query.

    Args:
        q (str): Partial professor name to search for (minimum 1 character).
        limit (int): Maximum number of results to return (1–20, default 8).

    Returns:
        dict: {"results": [<professor name>, ...]}
    """
    return {"results": apiHelper.professorSuggestions(q, limit)}

# Choose ONE of these options:
# Option 1: Load only CS courses (faster startup, limited matching)
#COURSES_PATH = "deg_guide/data/catalogs/cs_catalog_courses.json"

# Option 2: Load ALL catalogs (slower startup, matches more courses)
COURSES_PATH = "deg_guide/data/catalogs"

log_section("BACKEND STARTUP")
logger.info(f"Loading courses from: {COURSES_PATH}")

# Check if loading from directory or single file
courses_path = Path(COURSES_PATH)
if courses_path.is_dir():
    catalog_files = list(courses_path.glob("*.json"))
    logger.info(f"Found {len(catalog_files)} catalog files:")
    for f in sorted(catalog_files):
        logger.info(f"  - {f.name}")

COURSES, EQUIV_MAP = load_courses(COURSES_PATH)
logger.info(f"Total courses loaded: {len(COURSES)}")
logger.info(f"Equivalent course mappings: {len(EQUIV_MAP)}")

# Show breakdown by subject
subject_counts = {}
for course_id in COURSES.keys():
    # Extract subject (letters before numbers)
    match = re.match(r'^([A-Z]+)', course_id)
    if match:
        subj = match.group(1)
        subject_counts[subj] = subject_counts.get(subj, 0) + 1
logger.info(f"Subjects loaded: {len(subject_counts)}")
for subj, count in sorted(subject_counts.items()):
    logger.info(f"  {subj}: {count} courses")

logger.info("Backend ready to accept requests")

VALID_CATALOG_YEARS = ["2021-2022", "2022-2023", "2023-2024", "2024-2025", "2025-2026"]
DEFAULT_CATALOG_YEAR = "2025-2026"

# Init Professor Tags Database
try:
    apiHelper.init_db()
    logger.info("Professor tags database table initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize professor tags database: {e}")

# Mapping from program name to code (also tracks what we've implemented)
DEGREE_TYPE_MAP = {
    "Bachelor of Science": "BS",
    "Bachelor of Arts": "BA",
    
}

MAJOR_CODE_MAP = {
    "Computer Science": "CS",
    "Mathematics": "MATH",
    "Data Science": "DSCI",
}

MINOR_CODE_MAP = {
    "Mathematics": "MATH",
    "Computer Science": "CS",
}


def normalize_catalog_year(year_str: str) -> str:
    """
    Normalize catalog year strings to YYYY-YYYY format.
    Handles formats like: "2022-2023", "Winter 2025", "Fall 2024", "2025"
    """
    if not year_str:
        return DEFAULT_CATALOG_YEAR
    
    year_str = year_str.strip()
    
    # Already in correct format
    if year_str in VALID_CATALOG_YEARS:
        return year_str
    
    # Handle "Season YYYY" format (e.g., "Winter 2025", "Fall 2024")
    # Academic year: Fall 2024, Winter 2025, Spring 2025 -> 2024-2025
    season_year_parts = year_str.split()
    if len(season_year_parts) == 2:
        season, year = season_year_parts[0].lower(), season_year_parts[1]
        if year.isdigit():
            year_int = int(year)
            # Fall STARTS the academic year (Fall 2024 -> 2024-2025)
            # Winter/Spring/Summer are PART of the year that started previous fall
            # (Winter 2025 -> 2024-2025, Spring 2025 -> 2024-2025)
            if season == "fall":
                catalog_year = f"{year_int}-{year_int + 1}"
            else:  # winter, spring, summer
                catalog_year = f"{year_int - 1}-{year_int}"
            logger.debug(f"Catalog year mapping: '{year_str}' -> '{catalog_year}'")
            if catalog_year in VALID_CATALOG_YEARS:
                return catalog_year
    
    # Handle bare year "2025"
    if year_str.isdigit():
        year_int = int(year_str)
        catalog_year = f"{year_int - 1}-{year_int}"
        if catalog_year in VALID_CATALOG_YEARS:
            return catalog_year
    
    return DEFAULT_CATALOG_YEAR


def load_program_by_type(program_type: str, code: str, year: str):
    """
    Load a program JSON file by type, code, and catalog year.
    
    Args:
        program_type: "degree_types", "majors", or "minors"
        code: Program code (e.g., "BS", "CS", "MATH")
        year: Catalog year in YYYY-YYYY format
    
    Returns:
        Loaded program dict, or None if file doesn't exist
    """
    year = normalize_catalog_year(year)
    
    if program_type == "degree_types":
        path = f"deg_guide/data/programs/degree_types/{code}_{year}.json"
    elif program_type == "bachelor":
        path = f"deg_guide/data/programs/bachelor/{code}_{year}.json"
    elif program_type == "majors":
        path = f"deg_guide/data/programs/majors/{code}/{code}_{year}.json"
    elif program_type == "minors":
        path = f"deg_guide/data/programs/minors/{code}/{code}_{year}.json"
    else:
        return None
    
    try:
        return load_program(path)
    except Exception:
        return None


def load_cs_major(year: str):
    """Load the CS major requirements for a specific catalog year."""
    return load_program_by_type("majors", "CS", year)

'''
    { 
      "id": "math_two_course_sequence", "type": "choose_k", "k": 1,
      "from_requirements": ["seq_calc_251_252", "seq_calc_261_262", "seq_bio_calc_246_247"]
    },
'''

'''
class AuditRequest(BaseModel):
    taken_courses: List[str]

@app.post("/audit/cs")
def audit_cs(req: AuditRequest):
    return solve_degree_audit(COURSES, set(req.taken_courses), [BS, MAJOR_CS])
'''
def build_bucket_hints(programs_to_audit: list) -> dict:
    """
    Derive hint strings for open/credit-pool buckets directly from the program
    JSON structure — no hard-coded lookup tables needed on the frontend.

    Reads each requirement's type, min_credits, where, constraints, k, and
    from_set to produce strings like:
      "30 credits of 200+ level MATH courses required (15 must be 300+)"

    Args:
        programs_to_audit: list of loaded program objects (from load_program)

    Returns:
        dict keyed by "{program.id}:{requirement.id}" -> hint string
    """
    hints = {}

    for program in programs_to_audit:
        for req in program.requirements:
            req_id   = getattr(req, "id",   None)
            req_type = getattr(req, "type", None)
            if not req_id or not req_type:
                continue

            bucket_key = f"{program.id}:{req_id}"
            hint       = None

            if req_type == "credit_pool":
                min_credits = getattr(req, "min_credits", None)
                where       = getattr(req, "where", None) or {}
                subject     = where.get("subject", "")
                subject_in  = where.get("subject_in", [])
                min_num     = where.get("min_number", None)
                from_set    = getattr(req, "from_set", None)
                constraints = getattr(req, "constraints", None) or []

                # Build extra clause from sub-constraints (e.g. "15 must be 300+")
                constraint_parts = []
                for c in constraints:
                    c_min_credits = c.get("min_credits") if isinstance(c, dict) else getattr(c, "min_credits", None)
                    c_where       = (c.get("where", {}) if isinstance(c, dict) else getattr(c, "where", None)) or {}
                    c_min_num     = c_where.get("min_number")
                    if c_min_credits and c_min_num:
                        constraint_parts.append(f"{c_min_credits} must be {c_min_num}+")
                extra = f" ({', '.join(constraint_parts)})" if constraint_parts else ""

                subject_str = subject or (", ".join(subject_in) if subject_in else "")
                if subject_str and min_num:
                    hint = f"{min_credits} credits of {min_num}+ level {subject_str} courses required{extra}"
                elif from_set:
                    hint = f"{min_credits} credits from {from_set.replace('_', ' ')} required{extra}"
                elif min_credits:
                    hint = f"{min_credits} credits required{extra}"

                # Add submin-specific hints for credit_pool constraints (e.g. "credits in CS 410:499")
                # so the frontend can show "8 credits in CS 410:499 still needed" when that's the binding constraint
                for j, c in enumerate(constraints):
                    c_min_credits = c.get("min_credits") if isinstance(c, dict) else getattr(c, "min_credits", None)
                    c_where       = (c.get("where", {}) if isinstance(c, dict) else getattr(c, "where", None)) or {}
                    c_subject     = c_where.get("subject", subject)
                    c_min_num     = c_where.get("min_number")
                    c_max_num     = c_where.get("max_number")
                    if c_min_credits and c_subject:
                        if c_min_num is not None and c_max_num is not None:
                            submin_hint = f"credits in {c_subject} {c_min_num}:{c_max_num}"
                        elif c_min_num is not None:
                            submin_hint = f"credits in {c_subject} {c_min_num}+"
                        else:
                            submin_hint = f"{c_min_credits} credits from {c_subject}"
                        hints[f"{bucket_key}:submin:{j}"] = submin_hint

            elif req_type == "choose_k":
                k        = getattr(req, "k",                None)
                from_set = getattr(req, "from_set",          None)
                from_req = getattr(req, "from_requirements", None)

                if from_set and k:
                    hint = f"{k} course(s) from {from_set.replace('_', ' ')} required"
                elif from_req and k:
                    hint = f"{k} option(s) required"

            if hint:
                hints[bucket_key] = hint

    return hints


class AttemptIn(BaseModel):
    """
    A single course-attempt record used in manual audit requests.

    Attributes:
        attempt_id (str): Unique identifier for this attempt (e.g. "2026W-CS210-01").
        course_id (str): The canonical course identifier (e.g. "CS210").
        credits_taken (int): Number of credit hours attempted.
        grading_basis (str): "graded" | "pass_fail" | "unknown".
        term (Optional[str]): Term string (e.g. "Winter 2026").
        subtitle (Optional[str]): Section subtitle for variable-title courses.
        grade (Optional[str]): Letter grade (e.g. "A-", "B+") for min_grade requirements.
    """
    attempt_id: str
    course_id: str
    credits_taken: int
    grading_basis: str
    term: Optional[str] = None
    subtitle: Optional[str] = None
    grade: Optional[str] = None


class AuditRequest(BaseModel):
    """
    Request body for manual degree-audit endpoints.

    Attributes:
        taken_attempts (List[AttemptIn]): List of all course attempts to evaluate
            against the degree requirements.
    """
    taken_attempts: List[AttemptIn]


@app.post("/upload/transcript")
async def upload_transcript(file: UploadFile):
  """
  Accept a Ducks-On-Track PDF transcript, parse it with the PDF parser,
  run the degree-audit solver against the student's declared programs, and
  return the full audit result.

  The PDF is saved to a temporary directory, parsed in a separate process
  (via ProcessPoolExecutor) to avoid blocking the async event loop, and
  then deleted after use.

  Args:
      file (UploadFile): The uploaded PDF file from the multipart form request.

  Returns:
      dict: Audit result including completion percentages, requirement groups,
            parsed student info (name, GPA, majors, minors), and the raw
            parsedData for use in subsequent re-audit calls.
  """
  log_section("TRANSCRIPT UPLOAD")
  logger.info(f"Received file: {file.filename}")
  
  data = await file.read()
  unique_filename = f"{uuid.uuid4()}_{file.filename}"
  save_to = UPLOAD_DIR / unique_filename
  with open(save_to, "wb") as f:
    f.write(data)
  logger.debug(f"File saved to: {save_to}")
  
  loop = asyncio.get_running_loop()
  with ProcessPoolExecutor(max_workers=1) as executor:
      parsedData = await loop.run_in_executor(executor, parse_transcript_pdf, save_to)
  
  log_section("PARSED TRANSCRIPT DATA")
  broad_data = parsedData.get("broad_data", {})
  
  # Display student info
  logger.info("STUDENT INFO:")
  logger.info(f"  Name: {broad_data.get('student_name', 'N/A')}")
  logger.info(f"  Student ID: {broad_data.get('student_id', 'N/A')}")
  logger.info(f"  Program: {broad_data.get('program', 'N/A')}")
  logger.info(f"  Catalog Year: {broad_data.get('catalog_year', 'N/A')}")
  
  # Display declared major(s)
  declared_majors = broad_data.get("declared_majors") or (
      [broad_data.get("declared_major")] if broad_data.get("declared_major") else []
  )
  declared_majors = [m for m in declared_majors if m and m.get("name")]
  logger.info(f"DECLARED MAJOR(S): {len(declared_majors)}")
  for i, m in enumerate(declared_majors, 1):
      logger.info(f"  {i}. {m.get('name', 'N/A')} (Catalog: {m.get('catalog_year', 'N/A')})")
  
  # Display minors
  minors = broad_data.get("minors", [])
  logger.info(f"DECLARED MINORS: {len(minors)}")
  for i, minor in enumerate(minors, 1):
      logger.info(f"  {i}. {minor.get('name', 'N/A')} (Catalog: {minor.get('catalog_year', 'N/A')})")
  
  # Display courses taken
  taken_attempts = parsedData.get("taken_attempts", [])
  logger.info(f"COURSES TAKEN: {len(taken_attempts)} total")
  for att in taken_attempts[:15]:  # Show first 15
      logger.info(f"  - {att['course_id']} ({att['credits_taken']} cr, {att['grading_basis']}, {att.get('term', 'N/A')})")
  if len(taken_attempts) > 15:
      logger.info(f"  ... and {len(taken_attempts) - 15} more courses")
  
  programs_to_audit = []
  programs_loaded_info = {}
  
  log_section("LOADING PROGRAM JSON FILES")
  
  # 1. Load degree type (BS/BA) with its catalog year
  logger.info("Step 1: Loading DEGREE TYPE")
  degree_catalog_year = normalize_catalog_year(broad_data.get("catalog_year", ""))
  program_name = broad_data.get("program", "")
  logger.info(f"  Program from transcript: '{program_name}'")
  logger.info(f"  Catalog year (normalized): '{degree_catalog_year}'")
  
  degree_code = DEGREE_TYPE_MAP.get(program_name)
  logger.info(f"  Code mapping: '{program_name}' -> '{degree_code}'")
  
  if degree_code:
      degree_json_path = f"deg_guide/data/programs/degree_types/{degree_code}_{degree_catalog_year}.json"
      logger.info(f"  Loading JSON: {degree_json_path}")
      degree_program = load_program_by_type("degree_types", degree_code, degree_catalog_year)
      if degree_program:
          programs_to_audit.append(degree_program)
          programs_loaded_info["degree_type"] = {
              "code": degree_code,
              "catalog_year": degree_catalog_year,
              "json_file": degree_json_path
          }
          logger.info(f"  ✓ Loaded: {degree_program.id}")
      else:
          logger.warning(f"  ✗ Failed to load: {degree_json_path}")

      # Load shared bachelor requirements (Written English, Upper-division, 180 credits, etc.)
      bach_program = load_program_by_type("bachelor", "BACH", degree_catalog_year)
      if not bach_program and degree_catalog_year != DEFAULT_CATALOG_YEAR:
          bach_program = load_program_by_type("bachelor", "BACH", DEFAULT_CATALOG_YEAR)
          if bach_program:
              logger.info(f"  BACH_{degree_catalog_year} not found, using {DEFAULT_CATALOG_YEAR}")
      if bach_program:
          programs_to_audit.append(bach_program)
          logger.info(f"  ✓ Loaded: {bach_program.id} (shared bachelor requirements)")
  else:
      logger.warning(f"  ✗ No code mapping for: '{program_name}'")
  
  # 2. Load major(s) – support double (or more) majors
  majors_to_load = broad_data.get("declared_majors") or (
      [broad_data.get("declared_major")] if broad_data.get("declared_major") else []
  )
  majors_to_load = [m for m in majors_to_load if m and m.get("name")]
  logger.info(f"Step 2: Loading MAJOR(S) ({len(majors_to_load)} declared)")
  loaded_majors = []
  for i, major_info in enumerate(majors_to_load, 1):
      major_name = major_info.get("name", "")
      major_catalog_year = normalize_catalog_year(major_info.get("catalog_year", ""))
      logger.info(f"  Major {i}: '{major_name}' (Catalog: {major_catalog_year})")
      major_code = MAJOR_CODE_MAP.get(major_name)
      logger.info(f"    Code mapping: '{major_name}' -> '{major_code}'")
      if major_code:
          major_json_path = f"deg_guide/data/programs/majors/{major_code}/{major_code}_{major_catalog_year}.json"
          logger.info(f"    Loading JSON: {major_json_path}")
          major_program = load_program_by_type("majors", major_code, major_catalog_year)
          if major_program:
              programs_to_audit.append(major_program)
              loaded_majors.append({
                  "code": major_code,
                  "name": major_info.get("name"),
                  "catalog_year": major_catalog_year,
                  "json_file": major_json_path
              })
              logger.info(f"    ✓ Loaded: {major_program.id}")
          else:
              logger.warning(f"    ✗ Failed to load: {major_json_path}")
      else:
          logger.warning(f"    ✗ No code mapping for: '{major_name}'")
  if loaded_majors:
      programs_loaded_info["major"] = loaded_majors[0]
      programs_loaded_info["majors"] = loaded_majors
  
  # 3. Load minors with their respective catalog years
  logger.info(f"Step 3: Loading MINORS ({len(minors)} declared)")
  minors = broad_data.get("minors", [])
  
  loaded_minors = []
  for i, minor in enumerate(minors, 1):
      minor_name = minor.get("name", "")
      minor_catalog_year = normalize_catalog_year(minor.get("catalog_year", ""))
      logger.info(f"  Minor {i}: '{minor_name}' (Catalog: {minor_catalog_year})")
      
      minor_code = MINOR_CODE_MAP.get(minor_name)
      logger.info(f"    Code mapping: '{minor_name}' -> '{minor_code}'")
      
      if minor_code:
          minor_json_path = f"deg_guide/data/programs/minors/{minor_code}/{minor_code}_{minor_catalog_year}.json"
          logger.info(f"    Loading JSON: {minor_json_path}")
          minor_program = load_program_by_type("minors", minor_code, minor_catalog_year)
          if minor_program:
              programs_to_audit.append(minor_program)
              loaded_minors.append({
                  "code": minor_code,
                  "name": minor.get("name"),
                  "catalog_year": minor_catalog_year,
                  "json_file": minor_json_path
              })
              logger.info(f"    ✓ Loaded: {minor_program.id}")
          else:
              logger.warning(f"    ✗ Failed to load: {minor_json_path}")
      else:
          logger.warning(f"    ✗ No code mapping for: '{minor_name}'")
  
  if loaded_minors:
      programs_loaded_info["minors"] = loaded_minors

  # 4. Build course attempts
  log_section("RUNNING DEGREE AUDIT")
  attempts = [
        CourseAttempt(
            attempt_id=a["attempt_id"],
            course_id=a["course_id"],
            credits_taken=a["credits_taken"],
            grading_basis=a["grading_basis"],
            term=a.get('term'),      
            subtitle=a.get('subtitle'),
            grade=a.get('grade'),
        )
        for a in parsedData["taken_attempts"]
    ]
  
  logger.info(f"Course attempts to evaluate: {len(attempts)}")
  logger.info(f"Programs to audit: {[p.id for p in programs_to_audit]}")
  logger.info(f"Course catalog loaded: {len(COURSES)} courses available")
  
  # Check which courses match the catalog
  matched_courses = [a for a in attempts if a.course_id in COURSES]
  unmatched_courses = [a for a in attempts if a.course_id not in COURSES]
  logger.info(f"Courses matched in catalog: {len(matched_courses)}")
  if unmatched_courses:
      logger.warning(f"Courses NOT in catalog ({len(unmatched_courses)}): {[a.course_id for a in unmatched_courses[:10]]}")
  
  # 5. Run the solver
  logger.info("Running solver...")
  returnData = solve_degree_audit(COURSES, attempts, programs_to_audit, EQUIV_MAP)
  returnData["programs_loaded"] = programs_loaded_info
  returnData["student_name"] = broad_data.get("student_name")
  returnData["broad_data"] = broad_data
  returnData["parsedData"] = parsedData  # frontend stores this for re-audit calls
  returnData["bucket_hints"] = build_bucket_hints(programs_to_audit)

  return returnData


class ReAuditRequest(BaseModel):
    """
    Request body for the /re-audit endpoint.

    Attributes:
        parsedData (Dict[str, Any]): The parsedData dict returned by the initial
            /upload/transcript call, containing taken_attempts and broad_data.
        selections (Dict[str, str]): User's track/domain/concentration choices
            keyed by requirement group ID.
    """
    parsedData: Dict[str, Any]
    selections: Dict[str, str]


@app.post("/re-audit")
def re_audit(req: ReAuditRequest):
  """Re-run the degree audit with user-selected tracks/domains/concentrations."""
  parsedData = req.parsedData
  selections = req.selections
  broad_data = parsedData.get("broad_data", {})

  programs_to_audit = []
  programs_loaded_info: Dict[str, Any] = {}

  # Load degree type
  degree_catalog_year = normalize_catalog_year(broad_data.get("catalog_year", ""))
  degree_code = DEGREE_TYPE_MAP.get(broad_data.get("program", ""))
  if degree_code:
      degree_program = load_program_by_type("degree_types", degree_code, degree_catalog_year)
      if degree_program:
          programs_to_audit.append(degree_program)
          programs_loaded_info["degree_type"] = {
              "code": degree_code,
              "catalog_year": degree_catalog_year,
          }
      bach_program = load_program_by_type("bachelor", "BACH", degree_catalog_year)
      if not bach_program and degree_catalog_year != DEFAULT_CATALOG_YEAR:
          bach_program = load_program_by_type("bachelor", "BACH", DEFAULT_CATALOG_YEAR)
      if bach_program:
          programs_to_audit.append(bach_program)

  # Load majors
  majors_to_load = broad_data.get("declared_majors") or (
      [broad_data.get("declared_major")] if broad_data.get("declared_major") else []
  )
  majors_to_load = [m for m in majors_to_load if m and m.get("name")]
  loaded_majors = []
  for major_info in majors_to_load:
      major_code = MAJOR_CODE_MAP.get(major_info.get("name", ""))
      if not major_code:
          continue
      major_catalog_year = normalize_catalog_year(major_info.get("catalog_year", ""))
      major_program = load_program_by_type("majors", major_code, major_catalog_year)
      if major_program:
          programs_to_audit.append(major_program)
          loaded_majors.append({
              "code": major_code,
              "name": major_info.get("name"),
              "catalog_year": major_catalog_year,
          })
  if loaded_majors:
      programs_loaded_info["major"] = loaded_majors[0]
      programs_loaded_info["majors"] = loaded_majors

  # Load minors
  loaded_minors = []
  for minor in broad_data.get("minors", []):
      minor_code = MINOR_CODE_MAP.get(minor.get("name", ""))
      if not minor_code:
          continue
      minor_catalog_year = normalize_catalog_year(minor.get("catalog_year", ""))
      minor_program = load_program_by_type("minors", minor_code, minor_catalog_year)
      if minor_program:
          programs_to_audit.append(minor_program)
          loaded_minors.append({
              "code": minor_code,
              "name": minor.get("name"),
              "catalog_year": minor_catalog_year,
          })
  if loaded_minors:
      programs_loaded_info["minors"] = loaded_minors

  # Build course attempts
  attempts = [
      CourseAttempt(
          attempt_id=a["attempt_id"],
          course_id=a["course_id"],
          credits_taken=a["credits_taken"],
          grading_basis=a["grading_basis"],
          term=a.get("term"),
          subtitle=a.get("subtitle"),
          grade=a.get("grade"),
      )
      for a in parsedData.get("taken_attempts", [])
  ]

  # Run solver with selections
  returnData = solve_degree_audit(COURSES, attempts, programs_to_audit, EQUIV_MAP, selections=selections)
  returnData["programs_loaded"] = programs_loaded_info
  returnData["student_name"] = broad_data.get("student_name")
  returnData["broad_data"] = broad_data
  returnData["parsedData"] = parsedData
  returnData["bucket_hints"] = build_bucket_hints(programs_to_audit)

  return returnData


@app.get("/catalog-years")
def get_catalog_years():
    """Return available catalog years for CS major."""
    return {"years": VALID_CATALOG_YEARS, "default": DEFAULT_CATALOG_YEAR}


@app.get("/backend-info")
def get_backend_info():
    """Return backend configuration and loaded data info."""
    return {
        "courses_path": COURSES_PATH,
        "courses_loaded": len(COURSES),
        "sample_course_ids": list(COURSES.keys())[:20],
        "valid_catalog_years": VALID_CATALOG_YEARS,
        "default_catalog_year": DEFAULT_CATALOG_YEAR,
        "supported_mappings": {
            "degree_types": DEGREE_TYPE_MAP,
            "majors": MAJOR_CODE_MAP,
            "minors": MINOR_CODE_MAP
        }
    }


@app.post("/audit/cs")
def audit_cs(req: AuditRequest, year: str = DEFAULT_CATALOG_YEAR, degree_type: str = "BS"):
    """
    Run a degree audit specifically for the CS major without a transcript upload.
    Useful for manual testing or integrations that supply course attempts directly.

    Args:
        req (AuditRequest): JSON body with a list of course attempts.
        year (str): Catalog year string (e.g. "2022-2023"). Defaults to the
            current default catalog year.
        degree_type (str): "BS" or "BA". Defaults to "BS".

    Returns:
        dict: Solver audit result with status, completion percentage, and
              a breakdown of each requirement group.
    """
    log_section("CS AUDIT REQUEST")
    logger.info(f"Request params: year={year}, degree_type={degree_type}")
    year = normalize_catalog_year(year)
    logger.info(f"Normalized year: {year}")
    
    programs = []
    
    # Load degree type
    degree_json = f"deg_guide/data/programs/degree_types/{degree_type.upper()}_{year}.json"
    logger.info(f"Loading degree JSON: {degree_json}")
    degree_program = load_program_by_type("degree_types", degree_type.upper(), year)
    if degree_program:
        programs.append(degree_program)
        logger.info(f"  ✓ Loaded: {degree_program.id}")
    else:
        logger.warning(f"  ✗ Failed to load: {degree_json}")
    
    # Load CS major
    major_json = f"deg_guide/data/programs/majors/CS/CS_{year}.json"
    logger.info(f"Loading major JSON: {major_json}")
    major_cs = load_cs_major(year)
    if major_cs:
        programs.append(major_cs)
        logger.info(f"  ✓ Loaded: {major_cs.id}")
    else:
        logger.warning(f"  ✗ Failed to load: {major_json}")
    
    logger.info(f"Programs to audit: {[p.id for p in programs]}")
    
    attempts = [
        CourseAttempt(
            attempt_id=a.attempt_id,
            course_id=a.course_id,
            credits_taken=a.credits_taken,
            grading_basis=a.grading_basis,
            term=a.term,
            subtitle=a.subtitle,
            grade=getattr(a, "grade", None),
        )
        for a in req.taken_attempts
    ]
    
    logger.info(f"Course attempts: {len(attempts)}")
    for att in attempts[:10]:
        logger.info(f"  - {att.course_id} ({att.credits_taken} cr)")
    if len(attempts) > 10:
        logger.info(f"  ... and {len(attempts) - 10} more")
    
    logger.info("Running solver...")
    result = solve_degree_audit(COURSES, attempts, programs, EQUIV_MAP)
    
    log_section("CS AUDIT RESULTS")
    logger.info(f"Status: {result.get('status')}")
    logger.info(f"Completion: {result.get('completion_percentage', 'N/A')}%")
    return result


# class TranscriptParseRequest(BaseModel):
#     pdf_path: str  # local path (easy for dev)

# @app.post("/transcript/parse")
# def transcript_parse(req: TranscriptParseRequest):
#     return parse_transcript_pdf(req.pdf_path)



#for temp testing run uvicorn app:app --reload.  Then go to http://127.0.0.1:8000/docs. go to the post/audit/cs. and try it out. 

'''
{
  "taken_attempts": [
    { "attempt_id": "2026W-MATH251-01", "course_id": "MATH251", "credits_taken": 4, "grading_basis": "graded" },
    { "attempt_id": "2026S-MATH252-01", "course_id": "MATH252", "credits_taken": 4, "grading_basis": "graded" },
    { "attempt_id": "2026S-CS210-01", "course_id": "CS210", "credits_taken": 4, "grading_basis": "graded" },
    { "attempt_id": "2026S-CS211-01", "course_id": "CS211", "credits_taken": 4, "grading_basis": "graded" },
    { "attempt_id": "2026S-CS212-01", "course_id": "CS212", "credits_taken": 4, "grading_basis": "graded" },
    { "attempt_id": "2026S-CS399-01", "course_id": "CS313", "credits_taken": 4, "grading_basis": "graded" },
    { "attempt_id": "2026S-CS410-01", "course_id": "CS410", "credits_taken": 4, "grading_basis": "graded" },
    { "attempt_id": "2026S-CS433-01", "course_id": "CS433", "credits_taken": 4, "grading_basis": "graded" }
  ]
}


{
  "taken_attempts": [
    { "attempt_id": "2025F-CS399-A", "course_id": "CS399", "credits_taken": 2, "grading_basis": "graded", "subtitle": "Independent Study A" },
    { "attempt_id": "2026W-CS399-B", "course_id": "CS399", "credits_taken": 2, "grading_basis": "graded", "subtitle": "Independent Study B" },
    { "attempt_id": "2026W-CS210-01", "course_id": "CS210", "credits_taken": 4, "grading_basis": "graded" },
    { "attempt_id": "2026S-CS211-01", "course_id": "CS211", "credits_taken": 4, "grading_basis": "graded" },
    { "attempt_id": "2026S-CS315-01", "course_id": "CS315", "credits_taken": 4, "grading_basis": "pnp" }
  ]
}


{
  "taken_attempts": [
    { "attempt_id": "2026W-CS310-01", "course_id": "CS310", "credits_taken": 4, "grading_basis": "graded" },
    { "attempt_id": "2026W-CS315-01", "course_id": "CS315", "credits_taken": 4, "grading_basis": "graded" },
    { "attempt_id": "2026S-CS410-01", "course_id": "CS410", "credits_taken": 4, "grading_basis": "graded" },
    { "attempt_id": "2026S-CS411-01", "course_id": "CS411", "credits_taken": 4, "grading_basis": "graded" },
    { "attempt_id": "2026S-CS422-01", "course_id": "CS422", "credits_taken": 4, "grading_basis": "pnp" },
    { "attempt_id": "2026F-CS423-01", "course_id": "CS423", "credits_taken": 4, "grading_basis": "graded" }
  ]
}



for the transcripts:

{
  "pdf_path": "deg_guide/data/records/Test_Transcript.pdf"
}

'''
