(function () {
  const DEFAULT_IMG = 'https://raw.githubusercontent.com/creativetimofficial/public-assets/master/soft-ui-design-system/assets/img/color-bags.jpg';

  function formatTimeMaybe(value) {
    if (!value) return '';
    // Try to parse only if Date can understand it
    const d = new Date(value);
    if (!isNaN(d.getTime())) {
      try {
        return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      } catch (_) {
        // Fallback to raw
      }
    }
    return String(value);
  }

  function buildCard(pres, index) {
    const card = document.createElement('div');
    card.className = 'card shadow-xs border-0 rounded-4 upcoming-card';
    card.role = 'button';

    // Data for modal
    card.dataset.title    = pres.title    || 'Untitled';
    card.dataset.time     = formatTimeMaybe(pres.time);
    card.dataset.location = pres.location || '';
    card.dataset.authors  = pres.authors  || '';
    card.dataset.abstract = pres.abstract || '';
    card.dataset.img      = pres.image_url || DEFAULT_IMG;

    const timeDisplay = card.dataset.time || '';

    card.innerHTML = `
      <div class="card-body py-3">
        <div class="d-flex align-items-start gap-3">
          <img src="${card.dataset.img}"
               alt="thumb" class="rounded-3" style="width:56px;height:56px;object-fit:cover;">
          <div class="flex-grow-1">
            <div class="d-flex justify-content-between align-items-start">
              <h6 class="mb-1">${(pres.type || 'Presentation')}: ${card.dataset.title}</h6>
              <div class="d-flex align-items-center">
                <span class="badge bg-gray-100 text-secondary me-2">${timeDisplay}</span>
                <div class="dropdown">
                  <button type="button"
                          class="btn btn-sm btn-link text-secondary px-2 mb-0"
                          id="upcMenu${index+1}"
                          data-bs-toggle="dropdown"
                          aria-expanded="false"
                          aria-haspopup="true">⋮</button>
                  <ul class="dropdown-menu dropdown-menu-end" aria-labelledby="upcMenu${index+1}">
                    <li><a class="dropdown-item" href="#">View</a></li>
                    <li><a class="dropdown-item" href="#">Add to calendar</a></li>
                    <li><hr class="dropdown-divider"></li>
                    <li><a class="dropdown-item text-danger" href="#">Remove</a></li>
                  </ul>
                </div>
              </div>
            </div>
            <p class="text-sm text-secondary mb-0">
              ${
                pres.abstract
                  ? (pres.abstract.length > 100 ? pres.abstract.slice(0, 100) + '…' : pres.abstract)
                  : ''
              }
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

    m.querySelector('#mTitle').textContent    = cardEl.dataset.title    || '';
    m.querySelector('#mTime').textContent     = cardEl.dataset.time     || '';
    m.querySelector('#mLocation').textContent = cardEl.dataset.location || '';
    m.querySelector('#mAuthors').textContent  = cardEl.dataset.authors  || '';
    m.querySelector('#mAbstract').textContent = cardEl.dataset.abstract || '';

    const img = m.querySelector('#mImg');
    if (cardEl.dataset.img) { img.src = cardEl.dataset.img; img.classList.remove('d-none'); }
    else { img.classList.add('d-none'); }

    const modal = bootstrap.Modal.getOrCreateInstance(m, { backdrop: true });
    modal.show();
  }

  async function loadRecentPresentations() {
    const container = document.getElementById('upcoming-container');
    if (!container) {
      console.error('Upcoming container not found!');
      return;
    }

    try {
      const response = await fetch('/api/v1/presentations/recent');
      if (!response.ok) {
        throw new Error(`Network response was not ok: ${response.status} ${response.statusText}`);
      }

      const presentations = await response.json();

      if (!presentations || presentations.length === 0) {
        console.log('No presentations found.');
        container.innerHTML = '<p class="text-secondary">No upcoming presentations.</p>';
        return;
      }

      container.innerHTML = '';
      presentations.forEach((pres, idx) => {
        const card = buildCard(pres, idx);
        container.appendChild(card);
      });

      console.log(`Loaded ${presentations.length} upcoming presentations.`);
    } catch (err) {
      console.error('Failed to load recent presentations:', err);
      const container = document.getElementById('upcoming-container');
      if (container) {
        container.innerHTML = '<p class="text-danger">Could not load upcoming presentations.</p>';
      }
    }
  }

  // Event delegation for all future cards
  function setupDelegatedClicks() {
    const container = document.getElementById('upcoming-container');
    if (!container) return;

    container.addEventListener('click', (e) => {
      // Don’t open if clicking inside dropdowns, buttons, or links
      if (e.target.closest('.dropdown, [data-bs-toggle="dropdown"], button, a')) return;

      const card = e.target.closest('.upcoming-card');
      if (!card || !container.contains(card)) return;

      fillAndShowModal(card);
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    setupDelegatedClicks();
    loadRecentPresentations();
  });
})();
