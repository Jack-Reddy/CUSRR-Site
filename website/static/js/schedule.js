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

function formatPresenterName(p) {
  if (!p) return '';
  const first = p.firstname || p.first_name || p.first || '';
  const last  = p.lastname  || p.last_name  || p.last  || '';
  if (first || last) return `${first} ${last}`.trim();
  if (p.name) return p.name;
  if (p.email) return p.email;
  return '';
}


// -----------------------------
// Fetch Data
// -----------------------------
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

// -----------------------------
// Render Overview Blocks (Top Section)
// -----------------------------
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

// -----------------------------
// Render Full Details (Bottom Section)
// -----------------------------
function renderDetails(sessions, detailsContainer, presentations) {
  detailsContainer.innerHTML = '';

  for (let i = 0; i < sessions.length; i++) {
    const session = sessions[i];

    // start section and include session metadata
    const editBlockBtnHtml = (typeof window !== 'undefined' && window.IS_ORGANIZER) ?
      `<button type="button" class="btn btn-sm btn-outline-primary float-end ms-2" onclick="editBlock(${session.id})">Edit Block</button>` : '';

    let html = `
      <section id="session-${session.id}" class="card shadow-xs border-0 rounded-4 p-3 mb-3">
        <div class="d-flex align-items-start justify-content-between">
          <h5 class="fw-bold mb-1">${session.title}</h5>
          ${editBlockBtnHtml}
        </div>
        <p class="text-secondary mb-1">${formatTimeRange(session.start_time, session.end_time)}</p>
        ${session.location ? `<p class="text-secondary mb-1">${session.location}</p>` : ""}
        ${session.description ? `<p class="small mb-0">${session.description}</p>` : ""}
    `;

    // find presentations that belong to this session/block
    let session_presentations = [];
    if (presentations && Array.isArray(presentations)) {
      const match = presentations.find(item => item.block && item.block.id === session.id);
      if (match && Array.isArray(match.presentations)) {
        session_presentations = match.presentations;
      }
    }

    // if there are presentations, render them inside the session card in a row (3 per row using col-lg-4)
    if (session_presentations.length > 0) {
      // NOTE: add class "poster-list" so Sortable can initialize on this container
      html += `<div class="row gx-3 gy-3 mt-3 poster-list" data-session-id="${session.id}">`;
     

      session_presentations.forEach((presentation, j) => {
        // include the real presentation id so we can persist ordering
        const col = `
          <div class="col-12 col-md-6 col-lg-4 swappable" data-presentation-id="${presentation.id}">
            <div class="card border-0 shadow-xs rounded-4 h-100 p-3" id="poster-${presentation.id}">
              <h6 class="fw-bold mb-1">${presentation.title}</h6>
              <p class="text-sm text-secondary mb-1">${(presentation.presenters || []).map(formatPresenterName).filter(Boolean).join(", ")}</p>
              <p class="text-sm mb-0">${presentation.abstract ? truncate(presentation.abstract, 75) : ""}</p>
            </div>
          </div>
        `;
        html += col;
      });

      html += `</div>`; // close row
    }

    html += `</section>`; // close section
    detailsContainer.insertAdjacentHTML('beforeend', html);
  }
}

// Gather current order for all poster lists and POST to API
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

// Attach save button handler if present
document.addEventListener('click', async (e) => {
  const btn = e.target.closest && e.target.closest('#save-order-btn');
  if (!btn) return;
  btn.disabled = true;
  btn.textContent = 'Saving...';
  try {
    const result = await saveCurrentOrder();
    // basic feedback
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

// -----------------------------
// Init Sortable for poster lists (organizers only; Sortable lib must be loaded)
// -----------------------------
function initSortables() {
  if (typeof Sortable === 'undefined') return;
  document.querySelectorAll('.poster-list').forEach(list => {
    // avoid double-init
    if (list._sortableInitialized) return;
    new Sortable(list, {
      animation: 150,
      ghostClass: 'sortable-ghost',
      // allow dragging by grabbing the swappable element anywhere
      draggable: '.swappable',
      onEnd: function (evt) {
        // placeholder: persist order via fetch() if desired
        console.log('Poster moved', evt);
      }
    });
    list._sortableInitialized = true;
  });
}

// -----------------------------
// Load & Render Both Sections
// -----------------------------
async function loadForDay(day, overview, details) {
  const sessions = await fetchScheduleByDay(day);
  const presentations = await get_presentations_by_day(day);
  renderOverview(sessions, overview);
  renderDetails(sessions, details, presentations);

  // initialize Sortable after DOM nodes are in place (only if library is present)
  if (typeof Sortable !== 'undefined') {
    initSortables();
  }
}

// -----------------------------
// Main UI Init
// -----------------------------
async function initializeScheduleUI() {
  const daySelect = document.getElementById('day-select');
  const overview = document.getElementById('schedule-overview');
  const details = document.getElementById('schedule-details');

  const days = await fetchDays();

  // Populate day selector
  daySelect.innerHTML = '';
  days.forEach(day => {
    const opt = document.createElement('option');
    opt.value = day;
    opt.textContent = day;
    daySelect.appendChild(opt);
  });

  // Auto-load first day
  if (days.length > 0) {
    loadForDay(days[0], overview, details);
  }

  // On day change
  daySelect.addEventListener('change', () => {
    loadForDay(daySelect.value, overview, details);
  });
}

// -----------------------------
// Run when DOM is ready
// -----------------------------
document.addEventListener('DOMContentLoaded', initializeScheduleUI);

// Open block editor for a given session id
async function editBlock(blockId) {
  try {
    const resp = await fetch(`/api/v1/block-schedule/${blockId}`);
    if (!resp.ok) throw new Error(`Failed to fetch block: ${resp.status}`);
    const block = await resp.json();

    if (window.EditBlockModal) {
      window.EditBlockModal.fillAndShowModal(block);
      window.EditBlockModal.setupFormSubmit(async (data) => {
          // normalize datetime-local values and map to snake_case keys the backend expects
          // Keep local time intact: datetime-local inputs are like `YYYY-MM-DDTHH:MM`.
          function toLocalIsoNoTZ(val) {
            if (!val) return val;
            // If already in `YYYY-MM-DDTHH:MM` form, just add seconds
            if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(val)) return val + ':00';
            // Otherwise try to build a local datetime string from Date object without converting to UTC
            const d = new Date(val);
            if (Number.isNaN(d.getTime())) return val;
            const pad = (n) => String(n).padStart(2, '0');
            return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
          }

          if (data.start_time) {
            data.start_time = toLocalIsoNoTZ(data.start_time);
            delete data.start_time;
          }
          if (data.end_time) {
            data.end_time = toLocalIsoNoTZ(data.end_time);
            delete data.end_time;
          }

        const id = data.id || blockId;
        const putResp = await fetch(`/api/v1/block-schedule/${id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data)
        });
        if (!putResp.ok) throw new Error(`Failed to save block: ${putResp.status}`);

        // Reload the current day's schedule
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
