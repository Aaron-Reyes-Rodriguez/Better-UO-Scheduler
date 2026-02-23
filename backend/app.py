from fastapi import FastAPI, UploadFile
import asyncio
from concurrent.futures import ProcessPoolExecutor
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
from deg_guide.solver.model import load_courses, load_program, solve_degree_audit
from deg_guide.solver.data_types import CourseAttempt
from parser import parse_transcript_pdf
import apiHelperFunctions as apiHelper
from pathlib import Path
import tempfile

# 1. CRITICAL FOR RENDER: Create the directory if it doesn't exist
UPLOAD_DIR = Path(tempfile.gettempdir()) / 'uploadTranscript'
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app = FastAPI()

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

@app.get("/class/{class_id}")
def get_class(class_id: str):
  return apiHelper.classFinder(class_id)

@app.get("/professor/{professor_id}")
def get_professor(professor_id: str):
  return apiHelper.professorFinder(professor_id)

COURSES = load_courses("deg_guide/data/catalogs/cs_catalog_coursesv2.json")
#COURSES = load_courses("deg_guide/data/catalogs") this is to load all the courses from the catalogs folder

VALID_CATALOG_YEARS = ["2021-2022", "2022-2023", "2023-2024", "2024-2025", "2025-2026"]
DEFAULT_CATALOG_YEAR = "2025-2026"

# Mapping from program name to code (also tracks what we've implemented)
DEGREE_TYPE_MAP = {
    "Bachelor of Science": "BS",
    "Bachelor of Arts": "BA",
}

MAJOR_CODE_MAP = {
    "Computer Science": "CS",
}

MINOR_CODE_MAP = {
    "Mathematics": "MATH",
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
    season_year_parts = year_str.split()
    if len(season_year_parts) == 2:
        season, year = season_year_parts[0].lower(), season_year_parts[1]
        if year.isdigit():
            year_int = int(year)
            # Fall/Winter terms belong to the academic year starting that fall
            # Spring/Summer terms belong to the academic year that started previous fall
            if season in ["fall", "winter"]:
                catalog_year = f"{year_int}-{year_int + 1}"
            else:  # spring, summer
                catalog_year = f"{year_int - 1}-{year_int}"
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
class AttemptIn(BaseModel):
    attempt_id: str
    course_id: str
    credits_taken: int
    grading_basis: str
    term: Optional[str] = None
    subtitle: Optional[str] = None


class AuditRequest(BaseModel):
    taken_attempts: List[AttemptIn]


@app.post("/upload/transcript")
async def upload_transcript(file: UploadFile):
  data = await file.read()
  save_to = UPLOAD_DIR / file.filename
  with open(save_to, "wb") as f:
    f.write(data)
  loop = asyncio.get_running_loop()
  with ProcessPoolExecutor(max_workers=1) as executor:
      parsedData = await loop.run_in_executor(executor, parse_transcript_pdf, save_to)
  
  broad_data = parsedData.get("broad_data", {})
  programs_to_audit = []
  programs_loaded_info = {}
  
  # 1. Load degree type (BS/BA) with its catalog year
  degree_catalog_year = normalize_catalog_year(broad_data.get("catalog_year", ""))
  program_name = broad_data.get("program", "")
  degree_code = DEGREE_TYPE_MAP.get(program_name)
  if degree_code:
      degree_program = load_program_by_type("degree_types", degree_code, degree_catalog_year)
      if degree_program:
          programs_to_audit.append(degree_program)
          programs_loaded_info["degree_type"] = {
              "code": degree_code,
              "catalog_year": degree_catalog_year
          }
  
  # 2. Load major with its catalog year
  declared_major = broad_data.get("declared_major", {})
  major_name = declared_major.get("name", "")
  major_catalog_year = normalize_catalog_year(declared_major.get("catalog_year", ""))
  major_code = MAJOR_CODE_MAP.get(major_name)
  if major_code:
      major_program = load_program_by_type("majors", major_code, major_catalog_year)
      if major_program:
          programs_to_audit.append(major_program)
          programs_loaded_info["major"] = {
              "code": major_code,
              "name": declared_major.get("name"),
              "catalog_year": major_catalog_year
          }
  
  # 3. Load minors with their respective catalog years
  minors = broad_data.get("minors", [])
  loaded_minors = []
  for minor in minors:
      minor_name = minor.get("name", "")
      minor_catalog_year = normalize_catalog_year(minor.get("catalog_year", ""))
      minor_code = MINOR_CODE_MAP.get(minor_name)
      if minor_code:
          minor_program = load_program_by_type("minors", minor_code, minor_catalog_year)
          if minor_program:
              programs_to_audit.append(minor_program)
              loaded_minors.append({
                  "code": minor_code,
                  "name": minor.get("name"),
                  "catalog_year": minor_catalog_year
              })
  if loaded_minors:
      programs_loaded_info["minors"] = loaded_minors

  attempts = [
        CourseAttempt(
            attempt_id=a["attempt_id"],
            course_id=a["course_id"],
            credits_taken=a["credits_taken"],
            grading_basis=a["grading_basis"],
            term=a.get('term'),      
            subtitle=a.get('subtitle'),
        )
        for a in parsedData["taken_attempts"]
    ]
  
  returnData = solve_degree_audit(COURSES, attempts, programs_to_audit)
  returnData["programs_loaded"] = programs_loaded_info
  apiHelper.saveTranscriptData(returnData)
  return returnData

@app.get("/transcriptData")
def get_transcriptData():
  return apiHelper.getTranscriptData()

@app.get("/catalog-years")
def get_catalog_years():
    """Return available catalog years for CS major."""
    return {"years": VALID_CATALOG_YEARS, "default": DEFAULT_CATALOG_YEAR}


@app.post("/audit/cs")
def audit_cs(req: AuditRequest, year: str = DEFAULT_CATALOG_YEAR, degree_type: str = "BS"):
    """
    Audit CS major requirements.
    
    Args:
        year: Catalog year (e.g., "2022-2023")
        degree_type: "BS" or "BA"
    """
    year = normalize_catalog_year(year)
    programs = []
    
    # Load degree type
    degree_program = load_program_by_type("degree_types", degree_type.upper(), year)
    if degree_program:
        programs.append(degree_program)
    
    # Load CS major
    major_cs = load_cs_major(year)
    if major_cs:
        programs.append(major_cs)
    
    attempts = [
        CourseAttempt(
            attempt_id=a.attempt_id,
            course_id=a.course_id,
            credits_taken=a.credits_taken,
            grading_basis=a.grading_basis,
            term=a.term,
            subtitle=a.subtitle,
        )
        for a in req.taken_attempts
    ]
    return solve_degree_audit(COURSES, attempts, programs)


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