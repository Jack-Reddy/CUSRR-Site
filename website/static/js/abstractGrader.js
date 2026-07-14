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

  let presentations = []; // loaded from API
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
    col.dataset.title = p.title.toLowerCase();
  
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
                <h6 class="mb-1">${p.title}</h6>
              </div>
  
              <p class="text-sm mb-2">${ abstractSnippet(p.abstract || "", 120) }</p>
  
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
  
  // Render cards
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

  // Filters
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

  // Progress bar
  function updateProgress() {
    const cards = Array.from(document.querySelectorAll('[data-card]'));
    const total = cards.length;
    const done  = cards.filter(c => c.dataset.status === 'done').length;
    const pct = total ? Math.round(done / total * 100) : 0;

    document.getElementById('progressBar').style.width = pct + "%";
    document.getElementById('progressLabel').textContent =
      `${pct}% complete · ${done}/${total}`;
  }

  // Search
  searchInput.addEventListener('input', () => {
    query = searchInput.value.trim().toLowerCase();
    applyFilters();
  });

  // Status filter buttons
  statusButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      statusButtons.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      statusFilter = btn.dataset.filter;
      applyFilters();
    });
  });

  // Load presentations from API
  async function loadPresentations() {
    const res = await fetch("/api/v1/presentations");
    presentations = (await res.json()).filter(p => p.show_on_schedule !== false);

    const meRes = await fetch("/me");
    const meData = await meRes.json();

    if (!meData.authenticated || !meData.user_id) {
      console.warn("No logged-in user; skipping completion sync.");
      renderCards();
      return;
    }

    const completedRes = await fetch(`/api/v1/abstractgrades/completed/${meData.user_id}`);
    const completedData = await completedRes.json();
    const completedIds = new Set(completedData.completed || []);
    const gradeByPresentationId = new Map(
      (completedData.grades || []).map((grade) => [grade.presentation_id, grade.id])
    );

    presentations.forEach(p => {
      if (completedIds.has(p.id)) {
        p.status = "done";
        p.abstract_grade_id = gradeByPresentationId.get(p.id);
      } else {
        p.status = "todo";
        p.abstract_grade_id = null;
      }
    });

    // Render
    renderCards();
  }

  // Init
  loadPresentations();
})();