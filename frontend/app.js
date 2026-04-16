/**
 * ResumeIQ — app.js
 * Served as /static/app.js by FastAPI (main.py mounts /static → frontend/)
 *
 * Backend contract (combine_results.py response shape):
 * {
 *   ats_score: number,
 *   alignment: {
 *     similarity_score: number,
 *     matched_keywords: string[],
 *     missing_keywords: string[]
 *   },
 *   skills: {
 *     validated_skills: { skill: string, evidence: string }[],
 *     missing_skills: string[]
 *   },
 *   content_quality: {
 *     bullet_scores: {
 *       bullet: string,
 *       score: number,
 *       issues: string[],
 *       suggested_rewrite: string
 *     }[]
 *   }
 * }
 */

const fileInput = document.getElementById('file-input');
const dropZone = document.getElementById('drop-zone');
const filePill = document.getElementById('file-pill');
const fileNameEl = document.getElementById('file-name');
const jdField = document.getElementById('jd-field');
const btnAnalyze = document.getElementById('btn-analyze');
const loadSampleBtn = document.getElementById('load-sample');
const errorBanner = document.getElementById('error-banner');
const btnReset = document.getElementById('btn-reset');

let currentFile = null;
let stepInterval = null;

function setFile(file) {
    if (!file) {
        return;
    }

    if (!file.name.toLowerCase().endsWith('.pdf')) {
        showError('Please upload a PDF file.');
        return;
    }

    currentFile = file;
    fileNameEl.textContent = file.name;
    filePill.style.display = 'flex';
    hideError();
    checkReady();
}

fileInput.addEventListener('change', () => setFile(fileInput.files[0]));

function handleDragOver(event) {
    event.preventDefault();
    dropZone.classList.add('over');
}

function handleDragLeave() {
    dropZone.classList.remove('over');
}

function handleDrop(event) {
    event.preventDefault();
    dropZone.classList.remove('over');
    setFile(event.dataTransfer.files[0]);
}

function checkReady() {
    btnAnalyze.disabled = !(currentFile && jdField.value.trim().length > 20);
}

jdField.addEventListener('input', checkReady);

loadSampleBtn.addEventListener('click', async () => {
    try {
        const response = await fetch('/static/sample_job_description.txt');
        if (!response.ok) {
            throw new Error();
        }

        jdField.value = (await response.text()).trim();
    } catch {
        jdField.value =
            'We are seeking a Machine Learning Engineer to build and improve NLP systems ' +
            'for resume analysis and ranking. The role requires Python, FastAPI, scikit-learn, ' +
            'PyTorch, natural language processing, machine learning, model evaluation, and data ' +
            'preprocessing. Experience with REST API development, embeddings, transformers, and ' +
            'deployment workflows is preferred. Candidates should communicate clearly, work with ' +
            'cross-functional teams, and deliver measurable improvements in model quality and ' +
            'system efficiency.';
    }

    checkReady();
});

function showPage(id) {
    document.querySelectorAll('.page').forEach((page) => page.classList.remove('active'));
    document.getElementById(`page-${id}`).classList.add('active');
}

function showError(message) {
    errorBanner.textContent = message;
    errorBanner.style.display = 'block';
}

function hideError() {
    errorBanner.style.display = 'none';
}

function startStepAnimation() {
    const steps = document.querySelectorAll('#step-list li');
    steps.forEach((step) => {
        step.className = '';
    });

    steps[0].classList.add('active');
    let index = 0;

    stepInterval = setInterval(() => {
        steps[index].classList.remove('active');
        steps[index].classList.add('done');
        index += 1;

        if (index < steps.length) {
            steps[index].classList.add('active');
        }
    }, 900);
}

function finishStepAnimation() {
    clearInterval(stepInterval);
    document.querySelectorAll('#step-list li').forEach((step) => {
        step.classList.remove('active');
        step.classList.add('done');
    });
}

btnAnalyze.addEventListener('click', async () => {
    hideError();
    showPage('loading');
    startStepAnimation();

    const formData = new FormData();
    formData.append('resume', currentFile);
    formData.append('job_description', jdField.value.trim());

    try {
        const response = await fetch('/analyze', { method: 'POST', body: formData });
        const payload = await response.json();

        if (!response.ok) {
            throw new Error(payload.detail || 'Analysis failed. Please try again.');
        }

        finishStepAnimation();
        setTimeout(() => renderResults(payload), 400);
    } catch (error) {
        finishStepAnimation();
        showPage('upload');
        showError(error.message || 'Could not reach the server. Make sure the backend is running on port 8010.');
    }
});

function renderResults(data) {
    const alignment = data.alignment || {};
    const skills = data.skills || {};
    const quality = data.content_quality || {};
    const score = data.ats_score || 0;

    const similarity = alignment.similarity_score || 0;
    const matchedKeywords = alignment.matched_keywords || [];
    const missingKeywords = alignment.missing_keywords || [];
    const validatedSkills = skills.validated_skills || [];
    const missingSkills = skills.missing_skills || [];
    const bullets = quality.bullet_scores || [];

    document.getElementById('results-meta').textContent =
        'Generated ' + new Date().toLocaleDateString('en-US', {
            month: 'long',
            day: 'numeric',
            year: 'numeric',
        });

    const circumference = 2 * Math.PI * 58;
    document.getElementById('ring-num').textContent = score;

    const ringEl = document.getElementById('ring-fg');
    if (score >= 75) {
        ringEl.style.stroke = 'var(--green)';
    } else if (score >= 50) {
        ringEl.style.stroke = 'var(--amber)';
    } else {
        ringEl.style.stroke = 'var(--red)';
    }

    requestAnimationFrame(() => {
        ringEl.style.strokeDashoffset = circumference * (1 - score / 100);
    });

    const verdictBadge = document.getElementById('verdict-badge');
    if (score >= 75) {
        verdictBadge.textContent = 'Strong match';
        verdictBadge.className = 'verdict-badge good';
    } else if (score >= 50) {
        verdictBadge.textContent = 'Moderate match';
        verdictBadge.className = 'verdict-badge warn';
    } else {
        verdictBadge.textContent = 'Low match - needs work';
        verdictBadge.className = 'verdict-badge bad';
    }

    document.getElementById('st-matched').textContent = matchedKeywords.length;
    document.getElementById('st-missing').textContent = missingKeywords.length;
    document.getElementById('st-skills').textContent = `${validatedSkills.length}/${validatedSkills.length + missingSkills.length}`;
    document.getElementById('st-bullets').textContent = bullets.length;
    document.getElementById('sim-score').textContent = `${(similarity * 100).toFixed(1)}%`;

    renderKeywords(matchedKeywords, missingKeywords);
    renderSkills(validatedSkills, missingSkills);
    renderBullets(bullets);
    showPage('results');
}

function renderKeywords(matched, missing) {
    const hitEl = document.getElementById('kw-hit');
    const missEl = document.getElementById('kw-miss');

    hitEl.innerHTML = matched.length
        ? matched.map((keyword) => `<span class="kw hit">${escHtml(keyword)}</span>`).join('')
        : '<span class="empty-note">None detected</span>';

    missEl.innerHTML = missing.length
        ? missing.map((keyword) => `<span class="kw miss">${escHtml(keyword)}</span>`).join('')
        : '<span class="empty-note" style="color:var(--green)">No missing keywords - great coverage!</span>';
}

function renderSkills(validated, missingSkills) {
    const verifiedSkillsEl = document.getElementById('skills-verified');

    if (validated.length) {
        verifiedSkillsEl.innerHTML = validated.map((skill) => {
            const percent = skill.evidence && skill.evidence !== 'Mentioned in the resume' ? 80 : 45;
            return `
                <div class="skill-item">
                    <div class="skill-left">
                        <div class="skill-name">${escHtml(skill.skill)}</div>
                        <div class="skill-evidence">${escHtml(skill.evidence || 'Found in resume')}</div>
                        <div class="skill-bar-track">
                            <div class="skill-bar-fill" data-pct="${percent}"></div>
                        </div>
                    </div>
                    <span class="skill-badge ev">Evidenced</span>
                </div>`;
        }).join('');
    } else {
        verifiedSkillsEl.innerHTML = '<p class="empty-note">No validated skills were found.</p>';
    }

    document.getElementById('skills-missing').innerHTML = missingSkills.length
        ? missingSkills.map((skill) => `<span class="kw miss">${escHtml(skill)}</span>`).join('')
        : '<span class="empty-note" style="color:var(--green)">All required skills are present!</span>';

    requestAnimationFrame(() => {
        document.querySelectorAll('.skill-bar-fill').forEach((el) => {
            el.style.width = `${el.dataset.pct}%`;
        });
    });
}

function renderBullets(bullets) {
    const bulletsEl = document.getElementById('bullets-list');

    if (!bullets.length) {
        bulletsEl.innerHTML = '<p class="empty-note">No experience bullets were detected in the resume.</p>';
        return;
    }

    bulletsEl.innerHTML = bullets.map((bullet) => {
        const score = bullet.score || 0;
        const scoreClass = score >= 70 ? 'good' : score >= 45 ? 'warn' : 'bad';

        const issuesHtml = bullet.issues && bullet.issues.length
            ? `<div>
                     <div class="bc-issues-label">Issues detected</div>
                     <div class="bc-issue-list">
                         ${bullet.issues.map((issue) => `<span class="bc-issue">${escHtml(issue)}</span>`).join('')}
                     </div>
                 </div>`
            : '';

        const rewriteHtml = bullet.suggested_rewrite
            ? `<div class="bc-rewrite">
                     <div class="bc-rewrite-label">Suggested rewrite</div>
                     <div class="bc-rewrite-text">${escHtml(bullet.suggested_rewrite)}</div>
                 </div>`
            : '<p class="bc-strong">&#10003; This bullet is strong - no rewrite needed.</p>';

        return `
            <div class="bullet-card">
                <div class="bc-header">
                    <span class="bc-score ${scoreClass}">${score}/100</span>
                    <div class="bc-bar"><div class="bc-fill ${scoreClass}" style="width:${score}%"></div></div>
                </div>
                <div class="bc-original">${escHtml(bullet.bullet)}</div>
                ${issuesHtml}
                ${rewriteHtml}
            </div>`;
    }).join('');
}

document.querySelectorAll('.tab-bar .tab').forEach((btn) => {
    btn.addEventListener('click', () => {
        const tabName = btn.dataset.tab;

        document.querySelectorAll('.tab-bar .tab').forEach((tab) => tab.classList.remove('active'));
        document.querySelectorAll('.tab-pane').forEach((pane) => pane.classList.remove('active'));

        btn.classList.add('active');
        document.getElementById(`pane-${tabName}`).classList.add('active');

        if (tabName === 'skills') {
            requestAnimationFrame(() => {
                document.querySelectorAll('.skill-bar-fill').forEach((el) => {
                    el.style.width = `${el.dataset.pct}%`;
                });
            });
        }
    });
});

btnReset.addEventListener('click', () => {
    currentFile = null;
    fileInput.value = '';
    filePill.style.display = 'none';
    jdField.value = '';
    btnAnalyze.disabled = true;
    clearInterval(stepInterval);
    document.querySelectorAll('#step-list li').forEach((step) => {
        step.className = '';
    });
    hideError();
    showPage('upload');
});

function escHtml(value) {
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}