# ResumeIQ---NLP-Project

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

## How to run
Install dependencies:
pip install -r requirements.txt

Run the server:
uvicorn app.main:app --reload

Open:
http://127.0.0.1:8000/docs
