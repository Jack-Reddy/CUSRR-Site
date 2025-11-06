(function () {
  const DEFAULT_IMG = 'https://raw.githubusercontent.com/creativetimofficial/public-assets/master/soft-ui-design-system/assets/img/color-bags.jpg';

  function formatTimeNoYear(value) {
    if (!value) return '';
    const d = new Date(value);
    if (!isNaN(d.getTime())) {
      try {
        // show day/month + time, omit year
        return d.toLocaleDateString([], { month: 'short', day: 'numeric' }) +
               ' ' +
               d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      } catch (_) {}
    }
    return String(value);
  }

  function buildCard(item, index, cardClass = 'session-card') {
    const card = document.createElement('div');
    card.className = `card shadow-xs border-0 rounded-4 ${cardClass}`;
    card.role = 'button';

    // store data for modal
    card.dataset.title = item.title || 'Untitled';
    card.dataset.time = formatTimeNoYear(item.time);
    card.dataset.room = item.room || '';
    card.dataset.subject = item.subject || '';
    card.dataset.type = item.type || '';
    card.dataset.presenters = JSON.stringify(item.presenters || []);
    card.dataset.abstract = item.abstract || '';
    card.dataset.img = item.image_url || DEFAULT_IMG;

    const timeDisplay = card.dataset.time || '';

    card.innerHTML = `
      <div class="card-body py-3">
        <div class="d-flex align-items-start gap-3">
          <img src="${card.dataset.img}" alt="thumb" class="rounded-3" style="width:56px;height:56px;object-fit:cover;">
          <div class="flex-grow-1">
            <div class="d-flex justify-content-between align-items-start">
              <h6 class="mb-1">${card.dataset.title}</h6>
              <span class="badge bg-gray-100 text-secondary">${timeDisplay}</span>
            </div>
            <p class="text-sm text-secondary mb-0">
              ${item.abstract ? (item.abstract.length > 100 ? item.abstract.slice(0, 100) + '…' : item.abstract) : ''}
            </p>
          </div>
        </div>
      </div>
    `;
    return card;
  }

  function fillAndShowModal(cardEl) {
    const m = document.getElementById('sessionModal');
    if (!m) return;

    m.querySelector('#mTitle').textContent = cardEl.dataset.title || '';
    m.querySelector('#mTime').textContent = cardEl.dataset.time || '';
    m.querySelector('#mRoom').textContent = cardEl.dataset.room || '';
    m.querySelector('#mSubject').textContent = cardEl.dataset.subject || '';
    m.querySelector('#mType').textContent = cardEl.dataset.type || '';
    m.querySelector('#mAbstract').textContent = cardEl.dataset.abstract || '';

    const presentersEl = m.querySelector('#mPresenters');
    if (cardEl.dataset.presenters) {
      try {
        const presenters = JSON.parse(cardEl.dataset.presenters);
        presentersEl.innerHTML = presenters.map(p => `${p.firstname} ${p.lastname} (${p.email}${p.activity ? ', ' + p.activity : ''})`).join('<br>');
      } catch {
        presentersEl.textContent = cardEl.dataset.presenters;
      }
    } else {
      presentersEl.textContent = '';
    }

    const img = m.querySelector('#mImg');
    if (cardEl.dataset.img) { img.src = cardEl.dataset.img; img.classList.remove('d-none'); }
    else { img.classList.add('d-none'); }

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
    if (!container) return;
    container.addEventListener('click', (e) => {
      if (e.target.closest('.dropdown, [data-bs-toggle="dropdown"], button, a')) return;
      const card = e.target.closest('.session-card, .poster-card, .blitz-card');
      if (card) fillAndShowModal(card);
    });
  }

  async function loadCards({ apiEndpoint, upcomingContainer, pastContainer, cardClass = 'session-card', limit = 5 }) {
    const upEl = document.querySelector(upcomingContainer);
    const pastEl = document.querySelector(pastContainer);
    if (!upEl || !pastEl) return console.error('Containers not found');

    try {
      const resp = await fetch(apiEndpoint);
      if (!resp.ok) throw new Error(`Network response not ok: ${resp.status}`);
      const items = await resp.json();
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


