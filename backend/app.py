from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

from deg_guide.solver.model import load_courses, load_program, solve_degree_audit

app = FastAPI()

COURSES = load_courses("deg_guide/data/catalog_courses.json")
MAJOR_CS = load_program("deg_guide/data/programs/majors/CS.json")
BS = load_program("deg_guide/data/programs/uo_degree_types/BS.json")

class AuditRequest(BaseModel):
    taken_courses: List[str]

@app.post("/audit/cs")
def audit_cs(req: AuditRequest):
    return solve_degree_audit(COURSES, set(req.taken_courses), [BS, MAJOR_CS])



#for temp testing run uvicorn app:app --reload.  Then go to http://127.0.0.1:8000/docs. go to the post/audit/cs. and try it out. 

'''
{ "taken_courses": ["MATH251", "MATH252"] } to test BS
 or 

 {
  "taken_courses": ["CS210", "CS211", "CS315"] to test CS degree
}
'''