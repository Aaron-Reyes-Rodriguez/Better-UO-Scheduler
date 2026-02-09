from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional

from deg_guide.solver.model import load_courses, load_program, solve_degree_audit
from deg_guide.solver.data_types import CourseAttempt

from pydantic import BaseModel
from parser import parse_transcript_pdf

app = FastAPI()

COURSES = load_courses("deg_guide/data/catalogs/cs_catalog_coursesv2.json")
#COURSES = load_courses("deg_guide/data/catalogs") this is to load all the courses from the catalogs folder
MAJOR_CS = load_program("deg_guide/data/programs/majors/CS.json")
BS = load_program("deg_guide/data/programs/degree_types/BS.json")

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


@app.post("/audit/cs")
def audit_cs(req: AuditRequest):
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
    return solve_degree_audit(COURSES, attempts, [MAJOR_CS])


class TranscriptParseRequest(BaseModel):
    pdf_path: str  # local path (easy for dev)

@app.post("/transcript/parse")
def transcript_parse(req: TranscriptParseRequest):
    return parse_transcript_pdf(req.pdf_path)



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