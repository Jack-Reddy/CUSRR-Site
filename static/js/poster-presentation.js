(function () {
  const DEFAULT_IMG = 'https://raw.githubusercontent.com/creativetimofficial/public-assets/master/soft-ui-design-system/assets/img/color-bags.jpg';

  function formatTimeMaybe(value) {
    if (!value) return '';
    const d = new Date(value);
    if (!isNaN(d.getTime())) {
      try {
        return d.toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' });
      } catch (_) {}
    }
    return String(value);
  }

  function buildCard(pres, index) {
    const card = document.createElement('div');
    card.className = 'card shadow-xs border-0 rounded-4 poster-card';
    card.role = 'button';

    card.dataset.title = pres.title || 'Untitled';
    card.dataset.time = formatTimeMaybe(pres.time);
    card.dataset.room = pres.room || '';
    card.dataset.abstract = pres.abstract || '';
    card.dataset.img = pres.image_url || DEFAULT_IMG;

    const timeDisplay = card.dataset.time || '';

    card.innerHTML = `
      <div class="card-body py-3">
        <div class="d-flex align-items-start gap-3">
          <img src="${card.dataset.img}"
               alt="thumb" class="rounded-3" style="width:56px;height:56px;object-fit:cover;">
          <div class="flex-grow-1">
            <div class="d-flex justify-content-between align-items-start">
              <h6 class="mb-1">${card.dataset.title}</h6>
              <span class="badge bg-gray-100 text-secondary">${timeDisplay}</span>
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

  async function loadPosters() {
    const upcomingContainer = document.getElementById('upcoming-poster-container');
    const pastContainer = document.getElementById('past-poster-container');

    if (!upcomingContainer || !pastContainer) {
      console.error('Poster containers not found!');
      return;
    }

    try {
      const response = await fetch('/api/v1/presentations/type/poster');
      if (!response.ok) {
        throw new Error(`Network response was not ok: ${response.status} ${response.statusText}`);
      }

      const posters = await response.json();
      const now = new Date();

      const upcoming = posters.filter(p => new Date(p.time) >= now);
      const past = posters.filter(p => new Date(p.time) < now);

      // Sort: soonest upcoming first, most recent past first
      upcoming.sort((a, b) => new Date(a.time) - new Date(b.time));
      past.sort((a, b) => new Date(b.time) - new Date(a.time));

      // Clear containers
      upcomingContainer.innerHTML = '';
      pastContainer.innerHTML = '';

      if (past.length === 0) {
        pastContainer.innerHTML = '<p class="text-secondary">No past posters.</p>';
      } else {
        past.slice(0, 5).forEach((pres, idx) => {
          const card = buildCard(pres, idx);
          pastContainer.appendChild(card);
        });
      }

      if (upcoming.length === 0) {
        upcomingContainer.innerHTML = '<p class="text-secondary">No upcoming posters.</p>';
      } else {
        upcoming.slice(0, 5).forEach((pres, idx) => {
          const card = buildCard(pres, idx);
          upcomingContainer.appendChild(card);
        });
      }

      console.log(`Loaded ${posters.length} posters (${past.length} past, ${upcoming.length} upcoming).`);
    } catch (err) {
      console.error('Failed to load posters:', err);
      upcomingContainer.innerHTML = '<p class="text-danger">Could not load posters.</p>';
      pastContainer.innerHTML = '<p class="text-danger">Could not load posters.</p>';
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    loadPosters();
  });
})();
