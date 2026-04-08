# /analyze endpoint

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.services.preprocessing.parser import parse_resume
from app.services.aggregator.combine_results import run_full_pipeline

router = APIRouter()

@router.post("/analyze")
async def analyze(
    resume: UploadFile = File(...),
    job_description: str = Form(...)
):
    if not resume.filename or not resume.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Resume upload must be a PDF file.")

    if not job_description.strip():
        raise HTTPException(status_code=400, detail="Job description cannot be empty.")

    try:
        parsed_resume = parse_resume(resume)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Unable to parse the uploaded resume.") from exc

    if not parsed_resume.get("raw_text"):
        raise HTTPException(status_code=400, detail="The uploaded resume did not contain readable text.")

    results = run_full_pipeline(parsed_resume, job_description)

    return results