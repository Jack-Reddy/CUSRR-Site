(function () {
    const todoGrid = document.getElementById('todoGrid');
    const completedGrid = document.getElementById('completedGrid');
    const searchInput = document.getElementById('searchInput');
    const trackMenu = document.getElementById('trackFilter');
    const statusButtons = document.querySelectorAll('[data-filter]');
  
    let statusFilter = 'all';   // 'all' | 'todo' | 'done'
    let trackFilter = '';       // '' or a track (lowercased)
    let query = '';             // lowercased search string
  
    function updateProgress() {
      const cards = Array.from(document.querySelectorAll('[data-card]'));
      const total = cards.length;
      const done  = cards.filter(c => c.dataset.status === 'done').length;
      const pct   = total ? Math.round(done / total * 100) : 0;
      const bar   = document.getElementById('progressBar');
      const lbl   = document.getElementById('progressLabel');
      if (bar) bar.style.width = pct + '%';
      if (lbl) lbl.textContent = `${pct}% complete · ${done}/${total}`;
    }
  
    function matchesQuery(card) {
      if (!query) return true;
      const t = (card.dataset.title || '').toLowerCase();
      const a = (card.dataset.authors || '').toLowerCase();
      const r = (card.dataset.track || '').toLowerCase();
      return (t.includes(query) || a.includes(query) || r.includes(query));
    }
  
    function matchesStatus(card) {
      return statusFilter === 'all' || (card.dataset.status === statusFilter);
    }
  
    function matchesTrack(card) {
      if (!trackFilter) return true;
      return (card.dataset.track || '').toLowerCase() === trackFilter;
    }
  
    function applyFilters() {
      document.querySelectorAll('[data-card]').forEach(card => {
        const show = matchesStatus(card) && matchesTrack(card) && matchesQuery(card);
        card.style.display = show ? '' : 'none';
      });
    }
  
    // Search: live filter
    searchInput.addEventListener('input', () => {
      query = searchInput.value.trim().toLowerCase();
      applyFilters();
    });
  
    // Status buttons (All / To Do / Completed)
    statusButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        statusButtons.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        statusFilter = btn.getAttribute('data-filter'); // all | todo | done
        applyFilters();
      });
    });
  
    // Track dropdown
    trackMenu.addEventListener('click', (e) => {
      const item = e.target.closest('[data-track]');
      if (!item) return;
      trackFilter = (item.getAttribute('data-track') || '').toLowerCase();
      applyFilters();
    });
  
    // Toggle circle: move card between grids
    document.addEventListener('click', (e) => {
      const btn = e.target.closest('.status-toggle');
      if (!btn) return;
      const col = btn.closest('[data-card]');
      if (!col) return;
  
      const isDone = col.dataset.status === 'done';
      if (isDone) {
        col.dataset.status = 'todo';
        btn.classList.remove('btn-success');
        btn.classList.add('btn-outline-secondary');
        btn.setAttribute('aria-pressed', 'false');
        btn.title = 'Mark as completed';
        btn.innerHTML = '<i class="far fa-circle"></i>';
        todoGrid.append(col);
      } else {
        col.dataset.status = 'done';
        btn.classList.remove('btn-outline-secondary');
        btn.classList.add('btn-success');
        btn.setAttribute('aria-pressed', 'true');
        btn.title = 'Move back to To-Do';
        btn.innerHTML = '<i class="fas fa-check"></i>';
        completedGrid.append(col);
      }
  
      updateProgress();
      applyFilters();
    });
  
    // init
    updateProgress();
    applyFilters();
  })();