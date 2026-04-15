from app.services.aggregator.combine_results import compute_ats_score

alignment = {
    "similarity_score": 0.82,
    "matched_keywords": ["python", "fastapi", "nlp"],
    "missing_keywords": ["docker"]
}

skills = {
    "validated_skills": [
        {"skill": "python"},
        {"skill": "fastapi"},
        {"skill": "nlp"},
    ],
    "missing_skills": ["docker"]
}

content = {
    "bullet_scores": [
        {"score": 75},
        {"score": 75},
        {"score": 20},
        {"score": 95}
    ]
}

print("ATS Score:", compute_ats_score(alignment, skills, content))