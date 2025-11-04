async function loadRecentPresentations() {
  const container = document.getElementById('upcoming-container');
  
  if (!container) {
    console.error('Upcoming container not found!');
    return;
  }

  try {
    const response = await fetch('/routes/presentations/recent');

    if (!response.ok) {
      throw new Error(`Network response was not ok: ${response.status} ${response.statusText}`);
    }

    const presentations = await response.json();

    if (!presentations || presentations.length === 0) {
      console.log('No presentations found.');
      container.innerHTML = '<p class="text-secondary">No upcoming presentations.</p>';
      return;
    }

    // Clear container
    container.innerHTML = '';

    presentations.forEach((pres, index) => {
      const card = document.createElement('div');
      card.className = 'card shadow-xs border-0 rounded-4';

      // Handle time safely
      let timeDisplay = pres.time || '';
      try {
        // Attempt to parse as Date only if it's in a standard format
        const parsedTime = new Date(pres.time);
        if (!isNaN(parsedTime.getTime())) {
          timeDisplay = parsedTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        }
      } catch (e) {
        console.warn(`Failed to parse time for presentation "${pres.title}":`, pres.time);
      }

      card.innerHTML = `
        <div class="card-body py-3">
          <div class="d-flex align-items-start gap-3">
            <img src="${pres.image_url || 'https://raw.githubusercontent.com/creativetimofficial/public-assets/master/soft-ui-design-system/assets/img/color-bags.jpg'}"
                 alt="thumb" class="rounded-3" style="width:56px;height:56px;object-fit:cover;">
            <div class="flex-grow-1">
              <div class="d-flex justify-content-between align-items-start">
                <h6 class="mb-1">${pres.type || 'Presentation'}: ${pres.title || 'Untitled'}</h6>
                <div class="d-flex align-items-center">
                  <span class="badge bg-gray-100 text-secondary me-2">${timeDisplay}</span>
                  <div class="dropdown">
                    <button type="button"
                            class="btn btn-sm btn-link text-secondary px-2 mb-0"
                            id="upcMenu${index+1}"
                            data-bs-toggle="dropdown"
                            aria-expanded="false"
                            aria-haspopup="true">
                      ⋮
                    </button>
                    <ul class="dropdown-menu dropdown-menu-end" aria-labelledby="upcMenu${index+1}">
                      <li><a class="dropdown-item" href="#">View</a></li>
                      <li><a class="dropdown-item" href="#">Add to calendar</a></li>
                      <li><hr class="dropdown-divider"></li>
                      <li><a class="dropdown-item text-danger" href="#">Remove</a></li>
                    </ul>
                  </div>
                </div>
              </div>
              <p class="text-sm text-secondary mb-0">${pres.abstract ? (pres.abstract.length > 100 ? pres.abstract.slice(0, 100) + '...' : pres.abstract) : ''}</p>
            </div>
          </div>
        </div>
      `;

      container.appendChild(card);
    });

    console.log(`Loaded ${presentations.length} upcoming presentations.`);

  } catch (err) {
    console.error('Failed to load recent presentations:', err);
    container.innerHTML = '<p class="text-danger">Could not load upcoming presentations.</p>';
  }
}

// Run after DOM is ready
document.addEventListener('DOMContentLoaded', loadRecentPresentations);
