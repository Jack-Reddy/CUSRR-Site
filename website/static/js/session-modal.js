(function () {
  const DEFAULT_IMG = 'https://raw.githubusercontent.com/creativetimofficial/public-assets/master/soft-ui-design-system/assets/img/color-bags.jpg';
  let currentUserPromise = null;
  let canGradePromise = null;

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
      : raw.replace(/<[^>]*>/g, '').replace(/[#*_`$!\[\]()]/g, '');
    return plain.length > maxLength ? plain.slice(0, maxLength).trim() + '…' : plain;
  }

  function timeValue(item) {
    const d = new Date(item?.time || '');
    return isNaN(d.getTime()) ? Number.MAX_SAFE_INTEGER : d.getTime();
  }

  function sortByProgramOrder(items) {
    return (items || []).slice().sort((a, b) => {
      const timeDiff = timeValue(a) - timeValue(b);
      if (timeDiff !== 0) return timeDiff;
      const aId = a.program_identifier || String(a.id || '');
      const bId = b.program_identifier || String(b.id || '');
      return aId.localeCompare(bId);
    });
  }

  function visibleItems(items) {
    return sortByProgramOrder((items || []).filter(item => item && item.show_on_schedule !== false));
  }

  async function fetchJson(url, options = {}) {
    const resp = await fetch(url, { credentials: 'same-origin', ...options });
    if (!resp.ok) {
      let body = '';
      try { body = await resp.text(); } catch (_) {}
      throw new Error(`${url} failed with ${resp.status}: ${body || resp.statusText}`);
    }
    return await resp.json();
  }

  function loadCurrentUser() {
    if (!currentUserPromise) {
      currentUserPromise = fetch('/me', { credentials: 'same-origin', cache: 'no-store' })
        .then(resp => resp.ok ? resp.json() : null)
        .catch(() => null);
    }
    return currentUserPromise;
  }

  function rolesFor(user) {
    const roles = new Set(
      String(user?.auth || '')
        .split(',')
        .map(role => role.trim().toLowerCase())
        .filter(Boolean)
    );
    if (roles.has('admin')) roles.add('organizer');
    return roles;
  }

  async function canUseNormalGrading() {
    if (!canGradePromise) {
      canGradePromise = loadCurrentUser().then(user => {
        const roles = rolesFor(user);
        return roles.has('organizer') || roles.has('abstract_grader');
      });
    }
    return canGradePromise;
  }

  function buildCard(item, index, cardClass = 'session-card', options = {}) {
    const card = document.createElement('div');
    card.className = `card shadow-xs border-0 rounded-4 ${cardClass}`;
    card.role = 'button';

    const timeDisplay = formatTimeNoYear(item.time);
    const preview = abstractPreview(item.abstract, 100);
    const programId = item.program_identifier || '';
    const showGradeButton = options.showGradeButton === true;

    card.dataset.title = item.title || 'Untitled';
    card.dataset.time = timeDisplay;
    card.dataset.room = item.room || item.schedule_title || '';
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
                ${showGradeButton ? `<button type="button" class="btn btn-sm btn-outline-primary grade-btn" data-presentation-id="${escapeHtml(card.dataset.id)}">Grade</button>` : ''}
              </div>
            </div>
            <p class="text-sm text-secondary mb-0">${escapeHtml(preview)}</p>
          </div>
        </div>
      </div>
    `;
    return card;
  }

  function renderItems(containerSelector, items, cardClass = 'session-card', limit = 5, emptyText = 'No sessions found.', options = {}) {
    const container = document.querySelector(containerSelector);
    if (!container) return;

    container.innerHTML = '';
    const rows = visibleItems(items);
    if (!rows.length) {
      container.innerHTML = `<p class="text-secondary">${escapeHtml(emptyText)}</p>`;
      return;
    }

    rows.slice(0, limit).forEach((item, idx) => {
      container.appendChild(buildCard(item, idx, cardClass, options));
    });
  }

  async function refreshUndoGradeButton(presentationId) {
    const undoBtn = document.getElementById('gUndoGradeBtn');
    if (!undoBtn) return;

    undoBtn.classList.add('d-none');
    undoBtn.disabled = true;
    undoBtn.dataset.presentationId = presentationId || '';

    if (!presentationId || !(await canUseNormalGrading())) {
      return;
    }

    try {
      const result = await fetchJson(`/api/v1/grades/mine/${encodeURIComponent(presentationId)}`);
      if (result && result.grade) {
        undoBtn.classList.remove('d-none');
        undoBtn.disabled = false;
      }
    } catch (error) {
      console.warn('Could not check existing grade', error);
    }
  }

  async function openGradeModal(presentationId, title) {
    if (!(await canUseNormalGrading())) {
      alert('Only organizers and abstract graders can submit presentation grades.');
      return;
    }

    const gm = document.getElementById('gradeModal');
    if (!gm) return;
    gm.querySelector('#gPresentationId').value = presentationId || '';
    gm.querySelector('#gPresentationTitle').textContent = title || '';
    const orig = gm.querySelector('#gScoreOrig');
    const clar = gm.querySelector('#gScoreClar');
    const sign = gm.querySelector('#gScoreSign');
    if (orig) orig.value = 2;
    if (clar) clar.value = 2;
    if (sign) sign.value = 2;
    gm.querySelector('#gComments').value = '';
    updateGradeScores();
    refreshUndoGradeButton(presentationId);

    const modal = bootstrap.Modal.getOrCreateInstance(gm, { backdrop: true });
    modal.show();
  }

  async function submitGradeForm(ev) {
    ev.preventDefault();
    const gm = document.getElementById('gradeModal');
    const form = gm.querySelector('form');
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) submitBtn.disabled = true;

    if (!(await canUseNormalGrading())) {
      alert('Only organizers and abstract graders can submit presentation grades.');
      if (submitBtn) submitBtn.disabled = false;
      return;
    }

    const presentationId = gm.querySelector('#gPresentationId').value;
    const criteria_1 = Number(gm.querySelector('#gScoreOrig').value) || 0;
    const criteria_2 = Number(gm.querySelector('#gScoreClar').value) || 0;
    const criteria_3 = Number(gm.querySelector('#gScoreSign').value) || 0;
    const comments = gm.querySelector('#gComments').value || '';

    let userId;
    try {
      const user = await loadCurrentUser();
      if (!user || !user.user_id) throw new Error('not authenticated');
      userId = user.user_id;
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

      await refreshUndoGradeButton(presentationId);
      alert('Grade submitted successfully.');

    } catch (err) {
      console.error('Grade submit error', err);
      alert('Could not submit grade: ' + (err.message || err));
    } finally {
      if (submitBtn) submitBtn.disabled = false;
    }
  }

  async function undoGrade() {
    const gm = document.getElementById('gradeModal');
    const presentationId = gm?.querySelector('#gPresentationId')?.value;
    const undoBtn = document.getElementById('gUndoGradeBtn');
    if (!presentationId || !undoBtn) return;

    if (!confirm('Undo your grade for this presentation?')) return;

    undoBtn.disabled = true;
    try {
      const resp = await fetch(`/api/v1/grades/mine/${encodeURIComponent(presentationId)}`, {
        method: 'DELETE',
        credentials: 'same-origin'
      });
      let data = {};
      try { data = await resp.json(); } catch (_) {}
      if (!resp.ok) {
        alert(data.error || data.message || 'Could not undo grade.');
        undoBtn.disabled = false;
        return;
      }
      undoBtn.classList.add('d-none');
      alert('Grade undone.');
    } catch (error) {
      console.error('Undo grade error', error);
      alert('Could not undo grade: ' + (error.message || error));
      undoBtn.disabled = false;
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

  function fillAndShowModal(cardEl) {
    const m = document.getElementById('sessionModal');
    if (!m) return;

    m.querySelector('#mTitle').textContent = cardEl.dataset.title || '';
    m.querySelector('#mTime').textContent = cardEl.dataset.time || '';
    m.querySelector('#mRoom').textContent = cardEl.dataset.room || '';
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

  async function loadSessions(apiUrl, containerSelector, cardClass = 'session-card', limit = 5) {
    const container = document.querySelector(containerSelector);
    if (!container) return;

    try {
      let items = visibleItems(await fetchJson(apiUrl));

      if (!items.length && apiUrl.includes('/recent')) {
        items = visibleItems(await fetchJson('/program/list'));
      }

      const showGradeButton = await canUseNormalGrading();
      renderItems(containerSelector, items, cardClass, limit, 'No sessions found.', { showGradeButton });
    } catch (err) {
      console.error('Failed to load sessions', err);
      container.innerHTML = '<p class="text-danger">Could not load sessions.</p>';
    }
  }

  async function loadCards({ apiEndpoint, upcomingContainer, pastContainer, cardClass = 'session-card', limit = 50 }) {
    try {
      const items = visibleItems(await fetchJson(apiEndpoint));
      const now = Date.now();
      const upcoming = [];
      const past = [];

      items.forEach((item) => {
        const t = timeValue(item);
        if (t === Number.MAX_SAFE_INTEGER || t >= now) {
          upcoming.push(item);
        } else {
          past.push(item);
        }
      });

      const showGradeButton = await canUseNormalGrading();
      renderItems(upcomingContainer, upcoming, cardClass, limit, 'No upcoming sessions found.', { showGradeButton });
      renderItems(pastContainer, past.reverse(), cardClass, limit, 'No past sessions found.', { showGradeButton });
    } catch (err) {
      console.error('Failed to load cards', err);
      const upcomingEl = document.querySelector(upcomingContainer);
      const pastEl = document.querySelector(pastContainer);
      if (upcomingEl) upcomingEl.innerHTML = '<p class="text-danger">Could not load sessions.</p>';
      if (pastEl) pastEl.innerHTML = '<p class="text-danger">Could not load sessions.</p>';
    }
  }

  function setupDelegatedClicks(containerSelector) {
    const container = document.querySelector(containerSelector);
    if (!container || container.dataset.sessionModalBound === 'true') return;
    container.dataset.sessionModalBound = 'true';

    container.addEventListener('click', (e) => {
      if (e.target.closest('.dropdown, [data-bs-toggle="dropdown"]')) return;

      const gradeBtn = e.target.closest('.grade-btn');
      if (gradeBtn) {
        e.stopPropagation();
        const card = gradeBtn.closest('.session-card, .poster-card, .blitz-card');
        openGradeModal(gradeBtn.dataset.presentationId, card?.dataset.title || '');
        return;
      }

      const card = e.target.closest('.session-card, .poster-card, .blitz-card');
      if (!card) return;
      fillAndShowModal(card);
    });
  }

  window.SessionModal = {
    loadSessions,
    loadCards,
    setupDelegatedClicks,
    openGradeModal,
    canUseNormalGrading
  };

  document.addEventListener('DOMContentLoaded', () => {
    ['gScoreOrig', 'gScoreClar', 'gScoreSign'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.addEventListener('input', updateGradeScores);
    });

    const undoBtn = document.getElementById('gUndoGradeBtn');
    if (undoBtn && undoBtn.dataset.bound !== 'true') {
      undoBtn.dataset.bound = 'true';
      undoBtn.addEventListener('click', undoGrade);
    }

    loadSessions('/api/v1/presentations/recent', '#recent-sessions', 'session-card', 5);
    loadSessions('/program/list?type=Poster', '#poster-sessions', 'poster-card', 6);
    loadSessions('/program/list?type=Blitz', '#blitz-sessions', 'session-card', 6);
    setupDelegatedClicks('#recent-sessions');
    setupDelegatedClicks('#poster-sessions');
    setupDelegatedClicks('#blitz-sessions');

    const gradeForm = document.querySelector('#gradeModal form');
    if (gradeForm && gradeForm.dataset.bound !== 'true') {
      gradeForm.dataset.bound = 'true';
      gradeForm.addEventListener('submit', submitGradeForm);
    }
  });
})();
