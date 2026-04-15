from app.services.content_quality.bullet_scorer import run_content_quality

experience = [
    "Built REST APIs using FastAPI for an NLP application.",
    "Trained transformer-based models for text classification.",
    "Worked on frontend development.",
    "Optimized inference latency by 35% using model pruning."
]

result = run_content_quality(experience)
print(result)