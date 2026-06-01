# ResumeIQ: NLP-Powered ATS Resume Optimizer

ResumeIQ is a full-stack web app that scores how well a resume matches a job description. Upload a PDF resume, paste a job description, and get a detailed report covering keyword alignment, skill validation, and bullet-level quality feedback with AI-powered rewrite suggestions.

## Features

- **ATS Compatibility Score**: weighted composite score (0-100) combining semantic similarity, keyword coverage, skill validation, and bullet quality
- **Semantic Alignment**: Sentence-BERT cosine similarity between resume and job description
- **Keyword Analysis**: hybrid keyword extraction using KeyBERT and rule-based skill matching; surfaces matched and missing terms
- **Skill Validation**: cross-references JD-extracted skills against experience bullets using exact/variant matching with semantic fallback (SBERT)
- **Bullet Quality Scoring**: scores each resume bullet on action verbs, metrics, technical depth, and specificity
- **AI Rewrite Suggestions**: Gemini-powered rewrites for weak or vague bullets, with context-aware metric prompts suggesting measurable outcomes to add

## Pipeline
![Pipeline](pipeline.png)

## ATS Score Breakdown

| Component | Weight | What it measures |
|---|---|---|
| Alignment | 40% | Semantic similarity + keyword coverage |
| Skill validation | 35% | JD skills evidenced in resume experience |
| Bullet quality | 25% | Average bullet score across resume |

## Tech Stack

| Layer | Tools |
|---|---|
| Resume Parsing | PyMuPDF |
| Semantic Similarity | Sentence-BERT (`all-MiniLM-L6-v2`) |
| Keyword Extraction | KeyBERT + rule-based skill matching |
| Bullet Rewrites | Gemini API (`gemini-flash-latest`) |
| Backend | FastAPI + Uvicorn |
| Frontend | HTML, CSS, Vanilla JS |

## Getting Started

**1. Clone the repo**
```bash
git clone https://github.com/harshitamandalika/ResumeIQ---NLP-Project.git
cd ResumeIQ---NLP-Project
```

**2. Install dependencies**
```bash
pip install -r requirements.txt
```

**3. Add Gemini API key**

Create a `.env` file:
```
GOOGLE_API_KEY=your_key_here
```

**4. Run the server**
```bash
uvicorn app.main:app --reload
```

**5. Open in browser**
```
http://127.0.0.1:8000
```
