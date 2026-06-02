function formatTimeRange(startStr, endStr) {
  const start = new Date(startStr);
  const end   = new Date(endStr);
  const opts = { hour: 'numeric', minute: '2-digit', hour12: true };
  return `${start.toLocaleTimeString(undefined, opts)}–${end.toLocaleTimeString(undefined, opts)}`;
}

function truncate(text, maxLen = 200) {
  if (!text) return "";
  if (text.length <= maxLen) return text;
  return text.slice(0, maxLen).trim() + '…';
}

function toLocalIsoNoTZ(val) {
  if (!val) return val;
  if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(val)) return val + ':00';
  const d = new Date(val);
  if (Number.isNaN(d.getTime())) return val;
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

function normalizeBlockPayload(raw) {
  const payload = { ...raw };

  if (payload.startTime) payload.start_time = toLocalIsoNoTZ(payload.startTime);
  else if (payload.start_time) payload.start_time = toLocalIsoNoTZ(payload.start_time);

  if (payload.endTime) payload.end_time = toLocalIsoNoTZ(payload.endTime);
  else if (payload.end_time) payload.end_time = toLocalIsoNoTZ(payload.end_time);

  delete payload.startTime;
  delete payload.endTime;

  if (payload.id === '') delete payload.id;

  return payload;
}

function formatPresenterName(p) {
  if (!p) return '';
  const first = p.firstname || p.first_name || p.first || '';
  const last  = p.lastname  || p.last_name  || p.last  || '';
  if (first || last) return `${first} ${last}`.trim();
  if (p.name) return p.name;
  if (p.email) return p.email;
  return '';
}

function abstractSnippet(source, maxLength = 75) {
  if (window.AbstractMarkdownEditor) {
    const text = window.AbstractMarkdownEditor.plainText(source || '');
    return text.length > maxLength ? text.slice(0, maxLength) + '…' : text;
  }
  return source && source.length > maxLength ? source.slice(0, maxLength) + '…' : (source || '');
}

async function fetchDays() {
  const res = await fetch('/api/v1/block-schedule/days');
  return await res.json();
}

async function fetchScheduleByDay(day) {
  const res = await fetch(`/api/v1/block-schedule/day/${day}`);
  return await res.json();
}

async function get_presentations_by_day(day) {
  const res = await fetch(`/api/v1/presentations/day/${day}`);
  return await res.json();
}

function renderOverview(sessions, overviewContainer) {
  overviewContainer.innerHTML = '';

  sessions.forEach((session, index) => {
    const html = `
      <div class="col-12 col-md-6">
        <a href="#session-${session.id}"
           class="card shadow-xs border-0 rounded-4 text-center p-3 text-decoration-none text-dark move-on-hover">
          <h6 class="mb-1 fw-bold">${session.title}</h6>
          <p class="text-sm text-secondary mb-0">${formatTimeRange(session.start_time, session.end_time)}</p>
        </a>
      </div>
    `;
    overviewContainer.insertAdjacentHTML('beforeend', html);
  });
}

function renderDetails(sessions, detailsContainer, presentations) {
  detailsContainer.innerHTML = '';

  for (let i = 0; i < sessions.length; i++) {
    const session = sessions[i];

    const editBlockBtnHtml = (typeof window !== 'undefined' && window.IS_ORGANIZER) ?
      `<button type="button" class="btn btn-sm btn-outline-primary float-end ms-2" onclick="editBlock(${session.id})">Edit Block</button>` : '';

    const nonPresentationLabel = session.is_presentation === false
      ? `<span class="badge bg-secondary ms-2">Not a Presentation Block</span>`
      : '';

    let html = `
      <section id="session-${session.id}" class="card shadow-xs border-0 rounded-4 p-3 mb-3">
        <div class="d-flex align-items-start justify-content-between">
          <div>
            <h5 class="fw-bold mb-1">${session.title}${nonPresentationLabel}</h5>
          </div>
          ${editBlockBtnHtml}
        </div>
        <p class="text-secondary mb-1">${formatTimeRange(session.start_time, session.end_time)}</p>
        ${session.location ? `<p class="text-secondary mb-1">${session.location}</p>` : ""}
        ${session.description ? `<p class="small mb-0">${session.description}</p>` : ""}
    `;

    let session_presentations = [];
    if (presentations && Array.isArray(presentations)) {
      const match = presentations.find(item => item.block && item.block.id === session.id);
      if (match && Array.isArray(match.presentations)) {
        session_presentations = match.presentations;
      }
    }

    html += `<div class="row gx-3 gy-3 mt-3 poster-list" data-session-id="${session.id}">`;

    session_presentations.forEach((presentation, j) => {
      let cardHtml = '';
      if (window.SessionModal && typeof window.SessionModal.buildCard === 'function') {
        const cardEl = window.SessionModal.buildCard(presentation, j, 'session-card');
        cardEl.classList.add('h-100');
        cardHtml = cardEl.outerHTML;
      } else {
        cardHtml = `
          <div class="card border-0 shadow-xs rounded-4 h-100 p-3" id="poster-${presentation.id}">
            <h6 class="fw-bold mb-1">${presentation.title}</h6>
            <p class="text-sm text-secondary mb-1">${(presentation.presenters || []).map(formatPresenterName).filter(Boolean).join(", ")}</p>
            <p class="text-sm mb-0">${presentation.abstract ? abstractSnippet(presentation.abstract, 75) : ""}</p>
          </div>
        `;
      }

      const col = `
        <div class="col-12 col-md-6 col-lg-4 swappable" data-presentation-id="${presentation.id}">
          ${cardHtml}
        </div>
      `;
      html += col;
    });

    html += `</div>`;
    html += `</section>`;
    detailsContainer.insertAdjacentHTML('beforeend', html);
  }
}

async function saveCurrentOrder() {
  if (!window.IS_ORGANIZER) {
    throw new Error('Not authorized to save order');
  }

  const lists = Array.from(document.querySelectorAll('.poster-list'));
  const orders = [];
  lists.forEach(list => {
    const scheduleId = list.dataset.sessionId || list.getAttribute('data-session-id');
    const items = Array.from(list.querySelectorAll('.swappable'));
    items.forEach((item, idx) => {
      const pid = item.dataset.presentationId || item.getAttribute('data-presentation-id');
      if (pid) {
        orders.push({
          presentation_id: parseInt(pid, 10),
          schedule_id: parseInt(scheduleId, 10),
          num_in_block: idx
        });
      }
    });
  });

  if (orders.length === 0) return { ok: true, message: 'No posters to save' };

  try {
    const res = await fetch('/api/v1/presentations/order', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ orders })
    });
    return await res.json();
  } catch (err) {
    console.error('Failed to save order', err);
    throw err;
  }
}

document.addEventListener('click', async (e) => {
  const btn = e.target.closest && e.target.closest('#save-order-btn');
  if (!btn) return;
  btn.disabled = true;
  btn.textContent = 'Saving...';
  try {
    const result = await saveCurrentOrder();
    if (result && result.ok) {
      btn.textContent = 'Saved';
      setTimeout(() => btn.textContent = 'Save Order', 1500);
    } else {
      btn.textContent = 'Save Failed';
      console.error('Save failed', result);
    }
  } catch (err) {
    btn.textContent = 'Save Error';
  } finally {
    btn.disabled = false;
  }
});

function initSortables() {
  if (typeof Sortable === 'undefined') return;
  document.querySelectorAll('.poster-list').forEach(list => {
    if (list._sortableInitialized) return;
    new Sortable(list, {
      animation: 150,
      ghostClass: 'sortable-ghost',
      group: 'schedule-presentations',
      draggable: '.swappable',
      onEnd: function (evt) {
        console.log('Presentation moved', evt);
      }
    });
    list._sortableInitialized = true;
  });
}

async function loadForDay(day, overview, details) {
  const sessions = await fetchScheduleByDay(day);
  const presentations = await get_presentations_by_day(day);
  renderOverview(sessions, overview);
  renderDetails(sessions, details, presentations);

  if (window.SessionModal && typeof window.SessionModal.setupDelegatedClicks === 'function') {
    window.SessionModal.setupDelegatedClicks('#schedule-details');
  }

  if (typeof Sortable !== 'undefined') {
    initSortables();
  }
}

async function initializeScheduleUI() {
  const daySelect = document.getElementById('day-select');
  const overview = document.getElementById('schedule-overview');
  const details = document.getElementById('schedule-details');
  const addBlockBtn = document.getElementById('add-block-btn');

  const days = await fetchDays();

  daySelect.innerHTML = '';
  days.forEach(day => {
    const opt = document.createElement('option');
    opt.value = day;
    opt.textContent = day;
    daySelect.appendChild(opt);
  });

  if (days.length > 0) {
    loadForDay(days[0], overview, details);
  }

  daySelect.addEventListener('change', () => {
    loadForDay(daySelect.value, overview, details);
  });

  if (addBlockBtn && window.IS_ORGANIZER) {
    addBlockBtn.addEventListener('click', async (e) => {
      e.preventDefault();
      const label = document.getElementById('editBlockModalLabel');
      if (label) label.textContent = 'Add Schedule Block';

      const deleteBtn = document.getElementById('deleteBlockBtn');
      if (deleteBtn) deleteBtn.style.display = 'none';

      if (window.EditBlockModal) {
        const sessions = await fetchScheduleByDay(daySelect.value);

        let defaultStartTime = '';
        let defaultEndTime = '';

        if (sessions.length > 0) {
          const firstBlockStart = new Date(sessions[0].start_time);
          const pad = (n) => String(n).padStart(2, '0');
          const dateStr = `${firstBlockStart.getFullYear()}-${pad(firstBlockStart.getMonth() + 1)}-${pad(firstBlockStart.getDate())}`;

          defaultStartTime = `${dateStr}T09:00`;
          defaultEndTime = `${dateStr}T10:00`;
        }

        window.EditBlockModal.fillAndShowModal({
          id: '',
          day: daySelect.value || '',
          title: '',
          description: '',
          location: '',
          type: '',
          sub_length: '',
          start_time: defaultStartTime,
          end_time: defaultEndTime
        });

        window.EditBlockModal.setupFormSubmit(async (data) => {
          const payload = normalizeBlockPayload(data);
          const resp = await fetch('/api/v1/block-schedule/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
          });
          if (!resp.ok) throw new Error(`Failed to create block: ${resp.status}`);

          await loadForDay(daySelect.value, overview, details);
        });
      }
    });
  }
}

document.addEventListener('DOMContentLoaded', initializeScheduleUI);

async function editBlock(blockId) {
  try {
    const resp = await fetch(`/api/v1/block-schedule/${blockId}`);
    if (!resp.ok) throw new Error(`Failed to fetch block: ${resp.status}`);
    const block = await resp.json();

    const label = document.getElementById('editBlockModalLabel');
    if (label) label.textContent = 'Edit Schedule Block';

    const deleteBtn = document.getElementById('deleteBlockBtn');
    if (deleteBtn) deleteBtn.style.display = 'block';

    if (window.EditBlockModal) {
      window.EditBlockModal.fillAndShowModal(block);
      window.EditBlockModal.setupFormSubmit(async (data) => {
        const payload = normalizeBlockPayload(data);
        const id = payload.id || blockId;
        delete payload.id;

        const putResp = await fetch(`/api/v1/block-schedule/${id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        if (!putResp.ok) throw new Error(`Failed to save block: ${putResp.status}`);

        const daySelect = document.getElementById('day-select');
        const overview = document.getElementById('schedule-overview');
        const details = document.getElementById('schedule-details');
        await loadForDay(daySelect.value, overview, details);
      });

      window.EditBlockModal.setupDeleteButton(async () => {
        const deleteResp = await fetch(`/api/v1/block-schedule/${blockId}`, {
          method: 'DELETE',
          headers: { 'Content-Type': 'application/json' }
        });
        if (!deleteResp.ok) throw new Error(`Failed to delete block: ${deleteResp.status}`);

        const daySelect = document.getElementById('day-select');
        const overview = document.getElementById('schedule-overview');
        const details = document.getElementById('schedule-details');
        await loadForDay(daySelect.value, overview, details);
      });
    } else {
      alert('Block editor not available.');
    }
  } catch (err) {
    console.error('Failed to open block editor', err);
    alert('Could not load block for editing.');
  }
}
