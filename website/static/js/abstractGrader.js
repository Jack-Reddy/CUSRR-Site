function truncate(str, n) {
  return str.length > n ? str.slice(0, n) + "..." : str;
}

function abstractSnippet(source, maxLength = 120) {
  if (window.AbstractMarkdownEditor) {
    return truncate(window.AbstractMarkdownEditor.plainText(source || ''), maxLength);
  }
  return truncate(source || '', maxLength);
}

(function () {
  const todoGrid = document.getElementById('todoGrid');
  const completedGrid = document.getElementById('completedGrid');
  const searchInput = document.getElementById('searchInput');
  const statusButtons = document.querySelectorAll('[data-filter]');

  let presentations = [];
  let statusFilter = 'all';
  let query = '';

  function actionButtons(p) {
    if (p.status === 'done' && p.abstract_grade_id) {
      return `
        <a class="btn btn-sm btn-outline-info px-2" href="/abstract-scoring?id=${p.id}">Review</a>
        <button class="btn btn-sm btn-outline-danger px-2" type="button" data-undo-grade-id="${p.abstract_grade_id}" data-presentation-title="${encodeURIComponent(p.title || '')}">
          Undo grade
        </button>
      `;
    }

    return `<a class="btn btn-sm btn-outline-info px-2" href="/abstract-scoring?id=${p.id}">Grade</a>`;
  }

  function createCard(p) {
    const col = document.createElement('div');
    col.className = "col";
    col.dataset.card = "";
    col.dataset.status = p.status;
    col.dataset.id = p.id;
    col.dataset.title = String(p.title || '').toLowerCase();

    const preview = p.abstract_preview || p.abstract || '';

    col.innerHTML = `
        <div class="card abstract-card shadow-xs border-0 rounded-4 h-100">
          <div class="card-body d-flex gap-3 align-items-center">

            <div class="d-flex flex-column align-items-center pt-1">
              ${p.status === "done"
                ? `<span class="btn btn-success rounded-circle p-0" style="width:36px;height:36px">
                     <i class="fas fa-check"></i>
                   </span>`
                : `<span class="btn btn-secondary rounded-circle p-0" style="width:36px;height:36px">
                     <i class="far fa-circle"></i>
                   </span>`
              }
            </div>

            <div class="flex-grow-1 ms-3">
              <div class="d-flex justify-content-between align-items-start">
                <h6 class="mb-1">${p.title || 'Untitled'}</h6>
              </div>

              <p class="text-sm mb-2">${abstractSnippet(preview, 120)}</p>

              <div class="d-flex align-items-center gap-2 flex-wrap">
                ${actionButtons(p)}
              </div>
            </div>
          </div>
        </div>
      `;
    return col;
  }

  async function undoAbstractGrade(gradeId, title) {
    if (!gradeId) return;

    const decodedTitle = title ? decodeURIComponent(title) : 'this abstract';
    if (!confirm(`Undo your grade for ${decodedTitle}?`)) {
      return;
    }

    try {
      const response = await fetch(`/api/v1/abstractgrades/${gradeId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.error || data.reason || `Could not undo grade: ${response.status}`);
      }

      await loadPresentations();
    } catch (error) {
      console.error('Could not undo abstract grade', error);
      alert(error.message || 'Could not undo abstract grade.');
    }
  }

  function bindUndoButtons() {
    document.querySelectorAll('[data-undo-grade-id]').forEach((button) => {
      button.addEventListener('click', () => {
        undoAbstractGrade(button.dataset.undoGradeId, button.dataset.presentationTitle);
      });
    });
  }

  function renderCards() {
    todoGrid.innerHTML = "";
    completedGrid.innerHTML = "";

    presentations.forEach(p => {
      const card = createCard(p);
      if (p.status === "done") completedGrid.append(card);
      else todoGrid.append(card);
    });

    bindUndoButtons();
    updateProgress();
    applyFilters();
  }

  function matchesQuery(card) {
    if (!query) return true;
    return card.dataset.title.includes(query);
  }

  function matchesStatus(card) {
    return statusFilter === 'all' || card.dataset.status === statusFilter;
  }

  function applyFilters() {
    document.querySelectorAll('[data-card]').forEach(card => {
      const show = matchesStatus(card) && matchesQuery(card);
      card.style.display = show ? "" : "none";
    });
  }

  function updateProgress() {
    const cards = Array.from(document.querySelectorAll('[data-card]'));
    const total = cards.length;
    const done = cards.filter(c => c.dataset.status === 'done').length;
    const pct = total ? Math.round(done / total * 100) : 0;

    document.getElementById('progressBar').style.width = pct + "%";
    document.getElementById('progressLabel').textContent =
      `${pct}% complete · ${done}/${total}`;
  }

  searchInput.addEventListener('input', () => {
    query = searchInput.value.trim().toLowerCase();
    applyFilters();
  });

  statusButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      statusButtons.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      statusFilter = btn.dataset.filter;
      applyFilters();
    });
  });

  async function loadPresentations() {
    try {
      const res = await fetch('/api/v1/abstractgrades/dashboard-list');
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.error || data.reason || `Could not load abstracts: ${res.status}`);
      }

      presentations = await res.json();
      renderCards();
    } catch (error) {
      console.error('Could not load abstract grading cards', error);
      todoGrid.innerHTML = `<div class="col"><p class="text-danger">${error.message || 'Could not load abstracts.'}</p></div>`;
      completedGrid.innerHTML = "";
    }
  }

  loadPresentations();
})();
