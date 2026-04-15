from app.services.skill_analysis.skill_validator import run_skill_analysis

sections = {
    "skills": ["Python", "FastAPI", "Machine Learning"],
    "experience": [
        "Built REST APIs using FastAPI for an NLP application.",
        "Trained transformer-based models for text classification.",
        "Worked on data preprocessing and model evaluation using Python."
    ]
}

jd_text = """
We are looking for someone with experience in Python, FastAPI, NLP,
transformers, Docker, and model evaluation.
"""

result = run_skill_analysis(sections, jd_text)
print(result)