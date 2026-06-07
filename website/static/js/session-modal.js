(function () {
  const DEFAULT_IMG = 'https://raw.githubusercontent.com/creativetimofficial/public-assets/master/soft-ui-design-system/assets/img/color-bags.jpg';

  function formatTimeNoYear(value) {
    if (!value) return '';
    const d = new Date(value);
    if (!isNaN(d.getTime())) {
      try {
        return d.toLocaleDateString([], { month: 'short', day: 'numeric' }) +
               ' ' +
               d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      } catch (_) {}
    }
    return String(value);
  }

  function escapeHtml(value) {
    return String(value || '')
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#039;');
  }

  function abstractPreview(source, maxLength = 100) {
    const raw = String(source || '');
    const plain = window.AbstractMarkdownEditor
      ? window.AbstractMarkdownEditor.plainText(raw)
      : raw.replace(/[#*_`$!\[\]()]/g, '');
    return plain.length > maxLength ? plain.slice(0, maxLength).trim() + '…' : plain;
  }

  function buildCard(item, index, cardClass = 'session-card') {
    const card = document.createElement('div');
    card.className = `card shadow-xs border-0 rounded-4 ${cardClass}`;
    card.role = 'button';

    const timeDisplay = formatTimeNoYear(item.time);
    const preview = abstractPreview(item.abstract, 100);
    const programId = item.program_identifier || '';

    card.dataset.title = item.title || 'Untitled';
    card.dataset.time = timeDisplay;
    card.dataset.room = item.room || '';
    card.dataset.subject = item.subject || '';
    card.dataset.type = item.type || '';
    card.dataset.programId = programId;
    card.dataset.presenters = JSON.stringify(item.presenters || []);
    card.dataset.abstract = item.abstract || '';
    card.dataset.id = item.id || '';

    card.innerHTML = `
      <div class="card-body py-3">
        <div class="d-flex align-items-start gap-3">
          <div class="flex-grow-1">
            <div class="d-flex justify-content-between align-items-start">
              <div>
                ${programId ? `<span class="badge bg-dark text-white mb-2">${escapeHtml(programId)}</span>` : ''}
                <h6 class="mb-1">${escapeHtml(card.dataset.title)}</h6>
              </div>
              <div class="d-flex align-items-center gap-2">
                <span class="badge bg-gray-100 text-secondary">${escapeHtml(timeDisplay)}</span>
                <button type="button" class="btn btn-sm btn-outline-primary grade-btn" data-presentation-id="${escapeHtml(card.dataset.id)}">Grade</button>
              </div>
            </div>
            <p class="text-sm text-secondary mb-0">${escapeHtml(preview)}</p>
          </div>
        </div>
      </div>
    `;
    return card;
  }

  function openGradeModal(presentationId, title) {
    const gm = document.getElementById('gradeModal');
    if (!gm) return;
    gm.querySelector('#gPresentationId').value = presentationId || '';
    gm.querySelector('#gPresentationTitle').textContent = title || '';
    const orig = gm.querySelector('#gScoreOrig');
    const clar = gm.querySelector('#gScoreClar');
    const sign = gm.querySelector('#gScoreSign');
    if (orig) orig.value = orig.value || 2;
    if (clar) clar.value = clar.value || 2;
    if (sign) sign.value = sign.value || 2;
    gm.querySelector('#gComments').value = '';
    updateGradeScores();

    const modal = bootstrap.Modal.getOrCreateInstance(gm, { backdrop: true });
    modal.show();
  }

  async function submitGradeForm(ev) {
    ev.preventDefault();
    const gm = document.getElementById('gradeModal');
    const form = gm.querySelector('form');
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) submitBtn.disabled = true;

    const presentationId = gm.querySelector('#gPresentationId').value;
    const criteria_1 = Number(gm.querySelector('#gScoreOrig').value) || 0;
    const criteria_2 = Number(gm.querySelector('#gScoreClar').value) || 0;
    const criteria_3 = Number(gm.querySelector('#gScoreSign').value) || 0;
    const comments = gm.querySelector('#gComments').value || '';

    let userId;
    try {
      const resp = await fetch('/me', { credentials: 'same-origin' });
      if (!resp.ok) throw new Error('not authenticated');
      userId = (await resp.json()).user_id;
    } catch (e) {
      alert('You must be logged in to submit a grade.');
      if (submitBtn) submitBtn.disabled = false;
      return;
    }

    const payload = { user_id: userId, presentation_id: presentationId, criteria_1, criteria_2, criteria_3, comments };

    try {
      const resp = await fetch('/api/v1/grades/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        credentials: 'same-origin'
      });

      let errData = {};
      try { errData = await resp.json(); } catch (_) {}

      if (!resp.ok) {
        alert(errData.error || errData.message || 'Failed to submit grade');
        if (submitBtn) submitBtn.disabled = false;
        return;
      }

      const modal = bootstrap.Modal.getInstance(gm);
      if (modal) modal.hide();
      form.reset();
      alert('Grade submitted successfully');

    } catch (err) {
      console.error('Grade submit error', err);
      alert('Could not submit grade: ' + (err.message || err));
    } finally {
      if (submitBtn) submitBtn.disabled = false;
    }
  }

  function updateGradeScores() {
    const oEl = document.getElementById('gScoreOrig');
    const cEl = document.getElementById('gScoreClar');
    const sEl = document.getElementById('gScoreSign');
    const totalEl = document.getElementById('gScoreTotal');
    if (!oEl || !cEl || !sEl || !totalEl) return;
    const o = +oEl.value;
    const c = +cEl.value;
    const s = +sEl.value;
    const oVal = document.getElementById('gScoreOrigVal');
    const cVal = document.getElementById('gScoreClarVal');
    const sVal = document.getElementById('gScoreSignVal');
    if (oVal) oVal.textContent = o;
    if (cVal) cVal.textContent = c;
    if (sVal) sVal.textContent = s;
    totalEl.textContent = o + c + s;
  }

  document.addEventListener('DOMContentLoaded', () => {
    ['gScoreOrig', 'gScoreClar', 'gScoreSign'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.addEventListener('input', updateGradeScores);
    });
  });

  function fillAndShowModal(cardEl) {
    const m = document.getElementById('sessionModal');
    if (!m) return;

    m.querySelector('#mTitle').textContent = cardEl.dataset.title || '';
    m.querySelector('#mTime').textContent = cardEl.dataset.time || '';
    m.querySelector('#mRoom').textContent = cardEl.dataset.room || '';
    m.querySelector('#mSubject').textContent = cardEl.dataset.subject || '';
    m.querySelector('#mType').textContent = cardEl.dataset.type || '';
    const programIdEl = m.querySelector('#mProgramId');
    if (programIdEl) programIdEl.textContent = cardEl.dataset.programId || '';
    const abstractEl = m.querySelector('#mAbstract');
    if (window.AbstractMarkdownEditor) {
      window.AbstractMarkdownEditor.renderToElement(abstractEl, cardEl.dataset.abstract || '');
    } else {
      abstractEl.textContent = cardEl.dataset.abstract || '';
    }

    const presentersEl = m.querySelector('#mPresenters');
    if (cardEl.dataset.presenters) {
      try {
        const presenters = JSON.parse(cardEl.dataset.presenters);
        presentersEl.innerHTML = presenters.map(p => `${escapeHtml(p.firstname || p.name || '')} ${escapeHtml(p.lastname || '')}${p.email ? ` (${escapeHtml(p.email)}${p.activity ? ', ' + escapeHtml(p.activity) : ''})` : ''}`).join('<br>');
      } catch {
        presentersEl.textContent = cardEl.dataset.presenters;
      }
    } else {
      presentersEl.textContent = '';
    }

    const modal = bootstrap.Modal.getOrCreateInstance(m, { backdrop: true });
    modal.show();
  }

  function loadSessions(apiUrl, containerSelector, cardClass = 'session-card', limit = 5) {
    const container = document.querySelector(containerSelector);
    if (!container) return;

    fetch(apiUrl)
      .then(resp => resp.ok ? resp.json() : Promise.reject(resp))
      .then(items => {
        container.innerHTML = '';
        items = (items || []).filter(item => item.show_on_schedule !== false);
        if (!items || items.length === 0) {
          container.innerHTML = '<p class="text-secondary">No sessions found.</p>';
          return;
        }
        items.slice(0, limit).forEach((item, idx) => {
          container.appendChild(buildCard(item, idx, cardClass));
        });
      })
      .catch(err => {
        console.error('Failed to load sessions', err);
        container.innerHTML = '<p class="text-danger">Could not load sessions.</p>';
      });
  }

  function setupDelegatedClicks(containerSelector) {
    const container = document.querySelector(containerSelector);
    if (!container || container.dataset.sessionModalBound === 'true') return;
    container.dataset.sessionModalBound = 'true';

    container.addEventListener('click', (e) => {
      if (e.target.closest('.dropdown, [data-bs-toggle="dropdown"]')) return;

      const gradeBtn = e.target.closest('.grade-btn');
      if (gradeBtn) {
        const pid = gradeBtn.dataset.presentationId;
        const card = gradeBtn.closest('.session-card, .poster-card, .blitz-card');
        const title = card ? card.dataset.title : '';
        openGradeModal(pid, title);
        return;
      }

      if (e.target.closest('button, a')) return;
      const card = e.target.closest('.session-card, .poster-card, .blitz-card');
      if (card) fillAndShowModal(card);
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    const gm = document.getElementById('gradeModal');
    if (gm) {
      const form = gm.querySelector('form');
      if (form) form.addEventListener('submit', submitGradeForm);
    }
  });

  async function loadCards({ apiEndpoint, upcomingContainer, pastContainer, cardClass = 'session-card', limit = 5 }) {
    const upEl = document.querySelector(upcomingContainer);
    const pastEl = document.querySelector(pastContainer);
    if (!upEl || !pastEl) return console.error('Containers not found');

    try {
      const resp = await fetch(apiEndpoint);
      if (!resp.ok) throw new Error(`Network response not ok: ${resp.status}`);
      const items = (await resp.json()).filter(item => item.show_on_schedule !== false);
      const now = new Date();

      const upcoming = items.filter(i => new Date(i.time) >= now).sort((a,b) => new Date(a.time) - new Date(b.time));
      const past = items.filter(i => new Date(i.time) < now).sort((a,b) => new Date(b.time) - new Date(a.time));

      upEl.innerHTML = upcoming.length === 0 ? '<p class="text-secondary">No upcoming items.</p>' : '';
      pastEl.innerHTML = past.length === 0 ? '<p class="text-secondary">No past items.</p>' : '';

      upcoming.slice(0, limit).forEach((i, idx) => upEl.appendChild(buildCard(i, idx, cardClass)));
      past.slice(0, limit).forEach((i, idx) => pastEl.appendChild(buildCard(i, idx, cardClass)));

      [upcomingContainer, pastContainer].forEach(c => setupDelegatedClicks(c));
    } catch (err) {
      console.error('Failed to load cards:', err);
      upEl.innerHTML = '<p class="text-danger">Could not load items.</p>';
      pastEl.innerHTML = '<p class="text-danger">Could not load items.</p>';
    }
  }

  window.SessionModal = {
    buildCard,
    fillAndShowModal,
    loadSessions,
    setupDelegatedClicks,
    loadCards,
    formatTimeNoYear
  };
})();
