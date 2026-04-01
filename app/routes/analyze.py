# /analyze endpoint

from fastapi import APIRouter, UploadFile, File, Form
from app.services.preprocessing.parser import parse_resume
from app.services.aggregator.combine_results import run_full_pipeline

router = APIRouter()

@router.post("/analyze")
async def analyze(
    resume: UploadFile = File(...),
    job_description: str = Form(...)
):
    parsed_resume = parse_resume(resume)

    results = run_full_pipeline(parsed_resume, job_description)

    return results