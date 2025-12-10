(function () {
  const ASSIGNABLE_BLOCK_TYPES = ['poster', 'presentation', 'blitz'];
  let blocksPromise = null;

  function toLocalDatetimeValue(val) {
    if (!val) return '';
    const d = new Date(val);
    if (Number.isNaN(d.getTime())) return '';
    const pad = (n) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }

  async function fetchAssignableBlocks() {
    if (blocksPromise) return blocksPromise;
    const query = ASSIGNABLE_BLOCK_TYPES.length ? `?types=${ASSIGNABLE_BLOCK_TYPES.join(',')}` : '';
    blocksPromise = fetch(`/api/v1/block-schedule/${query}`)
      .then((resp) => {
        if (!resp.ok) throw new Error(`Failed to load blocks: ${resp.status}`);
        return resp.json();
      })
      .then((blocks) => {
        // sort by day then start_time for a stable dropdown
        return blocks.slice().sort((a, b) => {
          if (a.day !== b.day) return a.day.localeCompare(b.day);
          return new Date(a.start_time) - new Date(b.start_time);
        });
      })
      .catch((err) => {
        console.error(err);
        return [];
      });
    return blocksPromise;
  }

  function populateScheduleOptions(selectEl, blocks, selectedId) {
    if (!selectEl) return;
    selectEl.innerHTML = '<option value="">Unassigned</option>';
    blocks.forEach((block) => {
      const label = `${block.day} — ${block.title || 'Untitled'} (${block.start_time || ''})`;
      const opt = document.createElement('option');
      opt.value = block.id;
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

    modalEl.querySelector('#editPresentationTitle').value = presentation.title || '';
    modalEl.querySelector('#editPresentationAbstract').value = presentation.abstract || '';
    modalEl.querySelector('#editPresentationSubject').value = presentation.subject || '';

    const typeInput = modalEl.querySelector('#editPresentationType');
    if (typeInput) typeInput.value = presentation.type || '';

    const timeInput = modalEl.querySelector('#editPresentationTime');
    if (timeInput) timeInput.value = toLocalDatetimeValue(presentation.time);

    const scheduleSelect = modalEl.querySelector('#editPresentationSchedule');
    const blocks = await fetchAssignableBlocks();
    populateScheduleOptions(scheduleSelect, blocks, presentation.schedule_id);

    // populate hidden presentation id so the form includes it explicitly
    const idInput = modalEl.querySelector('#editPresentationId');
    if (idInput) idInput.value = presentation.id || '';

    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    modal.show();
  }

  function setupFormSubmit(onSubmit) {
    const form = document.getElementById('editPresentationForm');
    if (!form) return;

    // Replace the form with a clone to remove any previously attached listeners.
    // This prevents multiple submissions being sent when the modal is opened repeatedly.
    const newForm = form.cloneNode(true);
    form.parentNode.replaceChild(newForm, form);

    newForm.addEventListener('submit', async (e) => {
      e.preventDefault();

      // Read data from the cloned form that is currently in the DOM
      const formData = new FormData(newForm);
      const data = Object.fromEntries(formData.entries());

      if (data.schedule_id === '') delete data.schedule_id;

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
