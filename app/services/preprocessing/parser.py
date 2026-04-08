import fitz  # PyMuPDF
import re


# Extract text from PDF
def extract_text_from_pdf(file):
    pdf_bytes = file.file.read()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    text = ""
    for page in doc:
        text += page.get_text()

    return text


# Clean text
def clean_text(text):
    text = text.replace("\r", "\n")
    text = re.sub(r'\n+', '\n', text)
    return text.strip()


# Extract skills 
def extract_skills_from_section(skills_lines):
    skills = []

    for line in skills_lines:
        # Split by common separators
        parts = re.split(r',|:|\||/|•', line)

        for part in parts:
            cleaned = part.strip().lower()

            # Filter noise
            if 2 < len(cleaned) < 40:
                skills.append(cleaned)

    return list(set(skills))


def merge_wrapped_lines(lines):
    merged_lines = []

    for line in lines:
        cleaned_line = line.strip()
        if not cleaned_line:
            continue

        if not merged_lines:
            merged_lines.append(cleaned_line)
            continue

        if len(cleaned_line) < 25 or merged_lines[-1].endswith(("by", "with", "using")):
            merged_lines[-1] = f"{merged_lines[-1].rstrip()} {cleaned_line}"
        else:
            merged_lines.append(cleaned_line)

    return merged_lines


# Section-based parsing
def extract_sections(text):
    sections = {
        "skills": [],
        "experience": []
    }

    # Split into lines
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    current_section = None

    # Section keywords 
    section_map = {
        "skills": ["skills", "technical skills", "core skills"],
        "experience": ["experience", "work experience", "professional experience", "work history"],
        "projects": ["projects", "project", "academic projects"],
        "education": ["education"]
    }

    extracted = {
        "skills": [],
        "experience": [],
        "projects": [],
        "education": []
    }

    # Detect sections
    for line in lines:
        lower_line = line.lower()

        # Detect section header
        found_section = None
        for key, keywords in section_map.items():
            if lower_line.strip() in keywords:
                found_section = key
                break

        if found_section:
            current_section = found_section
            continue

        # Add content under section
        if current_section in extracted:
            extracted[current_section].append(line)

    # Extract skills
    sections["skills"] = extract_skills_from_section(extracted["skills"])

    # Combine EXPERIENCE + PROJECTS
    combined_exp = extracted["experience"] + extracted["projects"]
    combined_exp = merge_wrapped_lines(combined_exp)

    # Clean experience lines
    cleaned_exp = []
    for line in combined_exp:
        line = line.strip()

        # Remove obvious headers
        if line.lower() in ["skills", "education", "projects"]:
            continue

        if len(line) < 15:
            continue

        cleaned_exp.append(line)

    sections["experience"] = cleaned_exp

    return sections


# Main Function
def parse_resume(file):
    """
    Returns:
    {
      "raw_text": "...",
      "sections": {
        "skills": [...],
        "experience": [...]
      }
    }
    """

    # Extract text
    raw_text = extract_text_from_pdf(file)

    # Clean text
    cleaned_text = clean_text(raw_text)

    # Extract structured sections
    sections = extract_sections(cleaned_text)

    return {
        "raw_text": cleaned_text,
        "sections": sections
    }