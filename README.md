# ResumeIQ---NLP-Project

ResumeIQ is a course project prototype for resume to job description analysis. The application parses a resume PDF, compares it with a target job description, and returns an ATS style score with keyword, skill, and bullet level feedback.

## Run

1. Create or reuse the local `.venv`.
2. Install dependencies with `pip install -r requirements.txt`.
3. Start the app with `python -m uvicorn app.main:app --reload --port 8010`.
4. Open `http://127.0.0.1:8010` in a browser.

## Demo Assets

- Sample resume PDF: `data/sample_resume.pdf`
- Sample job description: `frontend/sample_job_description.txt`

The browser UI lets you upload a PDF resume, paste a job description, load the sample job description, and inspect the returned analysis.

## JSON Format (DO NOT CHANGE)

### Input (from preprocessing)
{
  "raw_text": "...",
  "sections": {
    "skills": [],
    "experience": []
  }
}

### Output (final response)
{
  "ats_score": 50,
  "alignment": {
    "similarity_score": 0.0,
    "matched_keywords": [],
    "missing_keywords": []
  },
  "skills": {
    "validated_skills": [],
    "missing_skills": []
  },
  "content_quality": {
    "bullet_scores": []
  }
}