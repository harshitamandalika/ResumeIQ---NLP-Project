const form = document.getElementById("analyze-form");
const statusNode = document.getElementById("status");
const resultsNode = document.getElementById("results");
const submitButton = document.getElementById("submit-button");
const loadSampleButton = document.getElementById("load-sample");
const jobDescriptionInput = document.getElementById("job_description");

const atsScoreNode = document.getElementById("ats-score");
const similarityNode = document.getElementById("similarity-score");
const matchedKeywordsNode = document.getElementById("matched-keywords");
const missingKeywordsNode = document.getElementById("missing-keywords");
const validatedSkillsNode = document.getElementById("validated-skills");
const missingSkillsNode = document.getElementById("missing-skills");
const bulletScoresNode = document.getElementById("bullet-scores");

function setStatus(message, isError = false) {
    statusNode.textContent = message;
    statusNode.style.color = isError ? "#b91c1c" : "#5e6768";
}

function clearResults() {
    matchedKeywordsNode.innerHTML = "";
    missingKeywordsNode.innerHTML = "";
    validatedSkillsNode.innerHTML = "";
    missingSkillsNode.innerHTML = "";
    bulletScoresNode.innerHTML = "";
}

function renderTags(container, items, missing = false) {
    container.innerHTML = "";

    if (!items.length) {
        container.innerHTML = '<p class="empty">None</p>';
        return;
    }

    items.forEach((item) => {
        const tag = document.createElement("span");
        tag.className = `tag${missing ? " missing" : ""}`;
        tag.textContent = item;
        container.appendChild(tag);
    });
}

function renderValidatedSkills(items) {
    validatedSkillsNode.innerHTML = "";

    if (!items.length) {
        validatedSkillsNode.innerHTML = '<p class="empty">No supported skills were found.</p>';
        return;
    }

    items.forEach((item) => {
        const card = document.createElement("div");
        card.className = "skill-card";
        card.innerHTML = `
            <p><strong>${item.skill}</strong></p>
            <p>${item.evidence}</p>
        `;
        validatedSkillsNode.appendChild(card);
    });
}

function renderBulletScores(items) {
    bulletScoresNode.innerHTML = "";

    if (!items.length) {
        bulletScoresNode.innerHTML = '<p class="empty">No experience bullets were available for scoring.</p>';
        return;
    }

    items.forEach((item) => {
        const card = document.createElement("div");
        card.className = "bullet-card";

        const issueMarkup = item.issues.length
            ? `<ul class="issue-list">${item.issues.map((issue) => `<li>${issue}</li>`).join("")}</ul>`
            : '<p class="empty">This bullet is already strong.</p>';

        const rewriteMarkup = item.suggested_rewrite
            ? `<p class="subsection-title"><strong>Suggested rewrite</strong></p><p>${item.suggested_rewrite}</p>`
            : "";

        card.innerHTML = `
            <p class="bullet-meta">Score ${item.score}/100</p>
            <p>${item.bullet}</p>
            <p><strong>Issues</strong></p>
            ${issueMarkup}
            ${rewriteMarkup}
        `;

        bulletScoresNode.appendChild(card);
    });
}

function renderResults(data) {
    atsScoreNode.textContent = data.ats_score;
    similarityNode.textContent = `Semantic similarity score: ${data.alignment.similarity_score}`;

    renderTags(matchedKeywordsNode, data.alignment.matched_keywords);
    renderTags(missingKeywordsNode, data.alignment.missing_keywords, true);
    renderValidatedSkills(data.skills.validated_skills);
    renderTags(missingSkillsNode, data.skills.missing_skills, true);
    renderBulletScores(data.content_quality.bullet_scores);

    resultsNode.classList.remove("hidden");
}

async function loadSampleJobDescription() {
    const response = await fetch("/static/sample_job_description.txt");
    const text = await response.text();
    jobDescriptionInput.value = text.trim();
    setStatus("Loaded the sample job description.");
}

loadSampleButton.addEventListener("click", async () => {
    try {
        await loadSampleJobDescription();
    } catch {
        setStatus("Could not load the sample job description.", true);
    }
});

form.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearResults();
    resultsNode.classList.add("hidden");

    const formData = new FormData(form);
    setStatus("Analyzing the resume. The first request may take longer while the NLP models load.");
    submitButton.disabled = true;

    try {
        const response = await fetch("/analyze", {
            method: "POST",
            body: formData,
        });

        const payload = await response.json();

        if (!response.ok) {
            throw new Error(payload.detail || "Analysis failed.");
        }

        renderResults(payload);
        setStatus("Analysis complete.");
    } catch (error) {
        setStatus(error.message || "Analysis failed.", true);
    } finally {
        submitButton.disabled = false;
    }
});