from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from keybert import KeyBERT
import re


# Load models
sbert_model = SentenceTransformer('all-MiniLM-L6-v2')
kw_model = KeyBERT(model=sbert_model)


# Skill hint vocabulary
VALID_SKILL_HINTS = [

    # Programming
    "python", "java", "c++", "matlab", "javascript", "typescript",

    # Machine learning and AI
    "machine learning", "deep learning", "nlp", "natural language processing",
    "computer vision", "reinforcement learning",
    "large language models", "llm", "transformers", "bert", "gpt",

    # Libraries
    "pytorch", "tensorflow", "keras", "scikit-learn",
    "pandas", "numpy", "matplotlib", "seaborn",

    # NLP and generative AI
    "langchain", "langgraph", "rag", "retrieval augmented generation",
    "embedding", "vector database", "faiss", "pinecone",

    # Backend and APIs
    "fastapi", "flask", "django", "rest api", "api",

    # Databases
    "sql", "mysql", "postgresql", "mongodb", "nosql", "sqlite",

    # Cloud
    "aws", "gcp", "azure",

    # DevOps
    "docker", "kubernetes", "ci cd", "github actions",

    # Data engineering
    "spark", "hadoop", "airflow", "etl", "data pipelines",

    # MLOps
    "mlops", "model deployment", "model serving", "monitoring",

    # Visualization
    "tableau", "power bi", "plotly",

    # General
    "feature engineering", "model evaluation", "data preprocessing"
]


# Normalize text for matching
def normalize_text(text):
    text = text.lower()

    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)

    mappings = {
        "natural language processing": "nlp",
        "large language models": "llm",
        "rest api": "api",
        "apis": "api"
    }

    for key, value in mappings.items():
        text = text.replace(key, value)

    return text


# Compute semantic similarity
def compute_similarity(resume_text, jd_text):
    embeddings = sbert_model.encode([resume_text, jd_text])

    similarity = cosine_similarity(
        [embeddings[0]], [embeddings[1]]
    )[0][0]

    return float(similarity)


# Extract keywords using KeyBERT
def extract_keywords(jd_text, top_n=30):
    keywords = kw_model.extract_keywords(
        jd_text,
        keyphrase_ngram_range=(1, 3),
        stop_words='english',
        top_n=top_n
    )

    return [kw[0].lower() for kw in keywords]


# Normalize keywords
def normalize_keyword(keyword):
    keyword = keyword.lower().strip()

    mapping = {
        "natural language processing": "nlp",
        "large language models": "llm",
        "rest api": "api",
        "apis": "api"
    }

    for key in mapping:
        if key in keyword:
            return mapping[key]

    return keyword


# Filter keywords
def filter_keywords(keywords):
    filtered = []

    for kw in keywords:
        kw = kw.lower().strip()

        if len(kw) < 3:
            continue

        if len(kw.split()) > 4:
            continue

        for skill in VALID_SKILL_HINTS:
            if skill in kw:
                filtered.append(skill)
                break

    return list(set(filtered))


# Rule-based extraction from JD
def extract_skills_from_jd(jd_text):
    jd_lower = jd_text.lower()

    found = []

    for skill in VALID_SKILL_HINTS:
        if skill in jd_lower:
            found.append(skill)

    return found


# Match keywords using regex
def keyword_match(resume_text, keywords):
    resume_lower = normalize_text(resume_text)

    matched = []
    missing = []

    for kw in keywords:
        pattern = r'\b' + re.escape(kw).replace(r'\ ', r'\s+') + r'\b'

        if re.search(pattern, resume_lower):
            matched.append(kw)
        else:
            missing.append(kw)

    return matched, missing


# Main alignment function
def run_alignment(resume_text, jd_text):
    similarity_score = compute_similarity(resume_text, jd_text)

    keywords_keybert = extract_keywords(jd_text)
    keywords_keybert = filter_keywords(keywords_keybert)

    keywords_rule = extract_skills_from_jd(jd_text)

    keywords = list(set(keywords_keybert + keywords_rule))

    keywords = [normalize_keyword(k) for k in keywords]
    keywords = list(set(keywords))

    matched, missing = keyword_match(resume_text, keywords)

    return {
        "similarity_score": round(similarity_score, 3),
        "matched_keywords": matched,
        "missing_keywords": missing
    }