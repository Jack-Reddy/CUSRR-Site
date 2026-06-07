(function () {
  const blocksCache = new Map();

  async function fetchAssignableBlocks() {
    const key = '__all__';
    if (blocksCache.has(key)) return blocksCache.get(key);

    const promise = fetch('/api/v1/block-schedule/')
      .then((resp) => {
        if (!resp.ok) throw new Error(`Failed to load blocks: ${resp.status}`);
        return resp.json();
      })
      .then((blocks) => {
        return blocks.slice().sort((a, b) => {
          if (a.day !== b.day) return a.day.localeCompare(b.day);
          return new Date(a.start_time) - new Date(b.start_time);
        });
      })
      .catch((err) => {
        console.error(err);
        return [];
      });

    blocksCache.set(key, promise);
    return promise;
  }

  function formatBlockTime(block) {
    const start = block.start_time ? new Date(block.start_time) : null;
    if (!start || Number.isNaN(start.getTime())) return '';
    return start.toLocaleString([], { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
  }

  function populateScheduleOptions(selectEl, blocks, selectedId) {
    if (!selectEl) return;
    selectEl.innerHTML = '<option value="">Unassigned</option>';
    blocks.forEach((block) => {
      const label = `${block.day} — ${block.title || 'Untitled'}${block.type ? ' — ' + block.type : ''} (${formatBlockTime(block)})`;
      const opt = document.createElement('option');
      opt.value = String(block.id);
      opt.textContent = label;
      selectEl.appendChild(opt);
    });
    
    if (selectedId !== undefined && selectedId !== null && selectedId !== '') {
      selectEl.value = String(selectedId);
    }
  }

  async function fillAndShowModal(presentation) {
    const modalEl = document.getElementById('editPresentationModal');
    if (!modalEl) return;

    window._currentPresentationData = presentation;

    const blocks = await fetchAssignableBlocks();
    window._assignableBlocks = blocks;

    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    modal.show();
  }
  
  function populateFormFields(presentation) {
    const modalEl = document.getElementById('editPresentationModal');
    if (!modalEl) return;

    modalEl.querySelector('#editPresentationTitle').value = presentation.title || '';
    modalEl.querySelector('#editPresentationAbstract').value = presentation.abstract || '';
    modalEl.querySelector('#editPresentationSubject').value = presentation.subject || '';

    const typeSelect = modalEl.querySelector('#editPresentationType');
    if (typeSelect) {
      typeSelect.value = presentation.type || 'Presentation';
    }

    const showOnScheduleCheckbox = modalEl.querySelector('#editPresentationShowOnSchedule');
    if (showOnScheduleCheckbox) {
      showOnScheduleCheckbox.checked = presentation.show_on_schedule !== false;
    }

    const scheduleSelect = modalEl.querySelector('#editPresentationSchedule');
    if (window._assignableBlocks) {
      populateScheduleOptions(scheduleSelect, window._assignableBlocks, presentation.schedule_id);
    }

    const idInput = modalEl.querySelector('#editPresentationId');
    if (idInput) idInput.value = presentation.id || '';
  }

  function setupFormSubmit(onSubmit) {
    const form = document.getElementById('editPresentationForm');
    if (!form) return;

    const newForm = form.cloneNode(true);
    form.parentNode.replaceChild(newForm, form);

    if (window._currentPresentationData) {
      populateFormFields(window._currentPresentationData);
    }

    newForm.addEventListener('submit', async (e) => {
      e.preventDefault();

      const formData = new FormData(newForm);
      const data = Object.fromEntries(formData.entries());

      const showOnScheduleCheckbox = newForm.querySelector('#editPresentationShowOnSchedule');
      if (showOnScheduleCheckbox) {
        data.show_on_schedule = showOnScheduleCheckbox.checked;
      }

      try {
        await onSubmit(data);
        bootstrap.Modal.getInstance(newForm.closest('.modal')).hide();
      } catch (err) {
        console.error('Failed to submit presentation form:', err);
        alert('Error saving presentation changes.');
      }
    });
  }

  window.EditPresentationModal = {
    fillAndShowModal,
    setupFormSubmit,
  };
})();
