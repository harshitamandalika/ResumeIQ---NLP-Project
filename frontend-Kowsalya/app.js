/**
 * ResumeIQ — app.js
 * Served as /static/app.js by FastAPI (main.py mounts /static → frontend/)
 *
 * Backend contract (combine_results.py response shape):
 * {
 *   ats_score: number,
 *   alignment: {
 *     similarity_score: number,          // 0.0 – 1.0
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

/* ─── Element refs ─── */
const fileInput     = document.getElementById('file-input');
const dropZone      = document.getElementById('drop-zone');
const filePill      = document.getElementById('file-pill');
const fileNameEl    = document.getElementById('file-name');
const jdField       = document.getElementById('jd-field');
const btnAnalyze    = document.getElementById('btn-analyze');
const loadSampleBtn = document.getElementById('load-sample');
const errorBanner   = document.getElementById('error-banner');
const btnReset      = document.getElementById('btn-reset');

let currentFile  = null;
let stepInterval = null;

/* ════════════════════════════════════════
   FILE HANDLING
════════════════════════════════════════ */
function setFile(file) {
  if (!file) return;
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

/* Drag-and-drop */
function handleDragOver(e) {
  e.preventDefault();
  dropZone.classList.add('over');
}

function handleDragLeave() {
  dropZone.classList.remove('over');
}

function handleDrop(e) {
  e.preventDefault();
  dropZone.classList.remove('over');
  setFile(e.dataTransfer.files[0]);
}

/* ════════════════════════════════════════
   FORM READINESS
════════════════════════════════════════ */
function checkReady() {
  btnAnalyze.disabled = !(currentFile && jdField.value.trim().length > 20);
}

jdField.addEventListener('input', checkReady);

/* ════════════════════════════════════════
   SAMPLE JOB DESCRIPTION
   Fetches /static/sample_job_description.txt served by FastAPI
════════════════════════════════════════ */
loadSampleBtn.addEventListener('click', async () => {
  try {
    const res = await fetch('/static/sample_job_description.txt');
    if (!res.ok) throw new Error();
    jdField.value = (await res.text()).trim();
  } catch {
    /* Fallback if file not found */
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

/* ════════════════════════════════════════
   PAGE NAVIGATION
════════════════════════════════════════ */
function showPage(id) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.getElementById('page-' + id).classList.add('active');
}

/* ════════════════════════════════════════
   ERROR BANNER
════════════════════════════════════════ */
function showError(msg) {
  errorBanner.textContent = msg;
  errorBanner.style.display = 'block';
}

function hideError() {
  errorBanner.style.display = 'none';
}

/* ════════════════════════════════════════
   LOADING STEPS ANIMATION
════════════════════════════════════════ */
function startStepAnimation() {
  const steps = document.querySelectorAll('#step-list li');
  steps.forEach(li => (li.className = ''));
  steps[0].classList.add('active');
  let idx = 0;

  stepInterval = setInterval(() => {
    steps[idx].classList.remove('active');
    steps[idx].classList.add('done');
    idx += 1;
    if (idx < steps.length) steps[idx].classList.add('active');
  }, 900);
}

function finishStepAnimation() {
  clearInterval(stepInterval);
  document.querySelectorAll('#step-list li').forEach(li => {
    li.classList.remove('active');
    li.classList.add('done');
  });
}

/* ════════════════════════════════════════
   ANALYZE — POST to /analyze
════════════════════════════════════════ */
btnAnalyze.addEventListener('click', async () => {
  hideError();
  showPage('loading');
  startStepAnimation();

  const formData = new FormData();
  formData.append('resume', currentFile);
  formData.append('job_description', jdField.value.trim());

  try {
    const res     = await fetch('/analyze', { method: 'POST', body: formData });
    const payload = await res.json();

    if (!res.ok) {
      throw new Error(payload.detail || 'Analysis failed. Please try again.');
    }

    finishStepAnimation();
    setTimeout(() => renderResults(payload), 400);

  } catch (err) {
    finishStepAnimation();
    showPage('upload');
    showError(err.message || 'Could not reach the server. Make sure the backend is running on port 8010.');
  }
});

/* ════════════════════════════════════════
   RENDER RESULTS
════════════════════════════════════════ */
function renderResults(data) {
  const alignment = data.alignment        || {};
  const skills    = data.skills           || {};
  const quality   = data.content_quality  || {};
  const score     = data.ats_score        || 0;

  const sim            = alignment.similarity_score  || 0;
  const matched        = alignment.matched_keywords  || [];
  const missing        = alignment.missing_keywords  || [];
  const validated      = skills.validated_skills     || [];
  const missingSkills  = skills.missing_skills       || [];
  const bullets        = quality.bullet_scores       || [];

  /* Meta line */
  document.getElementById('results-meta').textContent =
    'Generated ' + new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });

  /* ATS ring */
  const circ = 2 * Math.PI * 58; // 364.42
  document.getElementById('ring-num').textContent = score;

  const ringEl = document.getElementById('ring-fg');
  if (score >= 75)      ringEl.style.stroke = 'var(--green)';
  else if (score >= 50) ringEl.style.stroke = 'var(--amber)';
  else                  ringEl.style.stroke = 'var(--red)';

  /* Trigger ring animation on next frame */
  requestAnimationFrame(() => {
    ringEl.style.strokeDashoffset = circ * (1 - score / 100);
  });

  /* Verdict badge */
  const vb = document.getElementById('verdict-badge');
  if (score >= 75) {
    vb.textContent = 'Strong match';
    vb.className   = 'verdict-badge good';
  } else if (score >= 50) {
    vb.textContent = 'Moderate match';
    vb.className   = 'verdict-badge warn';
  } else {
    vb.textContent = 'Low match — needs work';
    vb.className   = 'verdict-badge bad';
  }

  /* Mini stats */
  document.getElementById('st-matched').textContent = matched.length;
  document.getElementById('st-missing').textContent = missing.length;
  document.getElementById('st-skills').textContent  = validated.length + '/' + (validated.length + missingSkills.length);
  document.getElementById('st-bullets').textContent = bullets.length;
  document.getElementById('sim-score').textContent  = (sim * 100).toFixed(1) + '%';

  /* Keywords */
  renderKeywords(matched, missing);

  /* Skills */
  renderSkills(validated, missingSkills);

  /* Bullets */
  renderBullets(bullets);

  showPage('results');
}

/* ─── Keywords ─── */
function renderKeywords(matched, missing) {
  const hitEl  = document.getElementById('kw-hit');
  const missEl = document.getElementById('kw-miss');

  hitEl.innerHTML = matched.length
    ? matched.map(k => `<span class="kw hit">${escHtml(k)}</span>`).join('')
    : '<span class="empty-note">None detected</span>';

  missEl.innerHTML = missing.length
    ? missing.map(k => `<span class="kw miss">${escHtml(k)}</span>`).join('')
    : '<span class="empty-note" style="color:var(--green)">No missing keywords — great coverage!</span>';
}

/* ─── Skills ─── */
function renderSkills(validated, missingSkills) {
  const svEl = document.getElementById('skills-verified');

  if (validated.length) {
    svEl.innerHTML = validated.map(s => {
      /* Score bar width: 80% if strong evidence, 45% if only mentioned */
      const pct = (s.evidence && s.evidence !== 'Mentioned in the resume') ? 80 : 45;
      return `
        <div class="skill-item">
          <div class="skill-left">
            <div class="skill-name">${escHtml(s.skill)}</div>
            <div class="skill-evidence">${escHtml(s.evidence || 'Found in resume')}</div>
            <div class="skill-bar-track">
              <div class="skill-bar-fill" data-pct="${pct}"></div>
            </div>
          </div>
          <span class="skill-badge ev">Evidenced</span>
        </div>`;
    }).join('');
  } else {
    svEl.innerHTML = '<p class="empty-note">No validated skills were found.</p>';
  }

  document.getElementById('skills-missing').innerHTML = missingSkills.length
    ? missingSkills.map(s => `<span class="kw miss">${escHtml(s)}</span>`).join('')
    : '<span class="empty-note" style="color:var(--green)">All required skills are present!</span>';

  /* Animate bars after paint */
  requestAnimationFrame(() => {
    document.querySelectorAll('.skill-bar-fill').forEach(el => {
      el.style.width = el.dataset.pct + '%';
    });
  });
}

/* ─── Bullets ─── */
function renderBullets(bullets) {
  const bl = document.getElementById('bullets-list');

  if (!bullets.length) {
    bl.innerHTML = '<p class="empty-note">No experience bullets were detected in the resume.</p>';
    return;
  }

  bl.innerHTML = bullets.map(b => {
    const sc  = b.score || 0;
    const cls = sc >= 70 ? 'good' : sc >= 45 ? 'warn' : 'bad';

    const issuesHtml = (b.issues && b.issues.length)
      ? `<div>
           <div class="bc-issues-label">Issues detected</div>
           <div class="bc-issue-list">
             ${b.issues.map(i => `<span class="bc-issue">${escHtml(i)}</span>`).join('')}
           </div>
         </div>`
      : '';

    const rewriteHtml = b.suggested_rewrite
      ? `<div class="bc-rewrite">
           <div class="bc-rewrite-label">Suggested rewrite</div>
           <div class="bc-rewrite-text">${escHtml(b.suggested_rewrite)}</div>
         </div>`
      : `<p class="bc-strong">&#10003; This bullet is strong — no rewrite needed.</p>`;

    return `
      <div class="bullet-card">
        <div class="bc-header">
          <span class="bc-score ${cls}">${sc}/100</span>
          <div class="bc-bar"><div class="bc-fill ${cls}" style="width:${sc}%"></div></div>
        </div>
        <div class="bc-original">${escHtml(b.bullet)}</div>
        ${issuesHtml}
        ${rewriteHtml}
      </div>`;
  }).join('');
}

/* ════════════════════════════════════════
   TABS
════════════════════════════════════════ */
document.querySelectorAll('.tab-bar .tab').forEach(btn => {
  btn.addEventListener('click', () => {
    const tabName = btn.dataset.tab;

    document.querySelectorAll('.tab-bar .tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));

    btn.classList.add('active');
    document.getElementById('pane-' + tabName).classList.add('active');

    /* Re-trigger bar animations when switching to skills tab */
    if (tabName === 'skills') {
      requestAnimationFrame(() => {
        document.querySelectorAll('.skill-bar-fill').forEach(el => {
          el.style.width = el.dataset.pct + '%';
        });
      });
    }
  });
});

/* ════════════════════════════════════════
   RESET
════════════════════════════════════════ */
btnReset.addEventListener('click', () => {
  currentFile            = null;
  fileInput.value        = '';
  filePill.style.display = 'none';
  jdField.value          = '';
  btnAnalyze.disabled    = true;
  clearInterval(stepInterval);
  document.querySelectorAll('#step-list li').forEach(li => (li.className = ''));
  hideError();
  showPage('upload');
});

/* ════════════════════════════════════════
   UTILITY
════════════════════════════════════════ */
function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
