# final output + ATS score

from app.services.alignment.sbert_similarity import run_alignment
from app.services.skill_analysis.skill_validator import run_skill_analysis
from app.services.content_quality.bullet_scorer import run_content_quality

def run_full_pipeline(parsed_resume, jd_text):

    print("Parsed Resume:", parsed_resume)
    
    alignment = run_alignment(parsed_resume["raw_text"], jd_text)
    skills = run_skill_analysis(parsed_resume["sections"], jd_text)
    content = run_content_quality(parsed_resume["sections"]["experience"])

    ats_score = compute_ats_score(alignment, skills, content)

    return {
        "ats_score": ats_score,
        "alignment": alignment,
        "skills": skills,
        "content_quality": content
    }

def compute_ats_score(alignment, skills, content):
    return 50  # dummy for now

