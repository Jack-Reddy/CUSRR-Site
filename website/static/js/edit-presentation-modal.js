(function () {
  const blocksCache = new Map(); // cache blocks per type key

  async function fetchAssignableBlocks(presentationType) {
    const normalizedType = (presentationType || '').toLowerCase();
    const key = normalizedType || '__all__';
    if (blocksCache.has(key)) return blocksCache.get(key);

    const query = normalizedType ? `?types=${encodeURIComponent(normalizedType)}` : '';
    const promise = fetch(`/api/v1/block-schedule/${query}`)
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

    blocksCache.set(key, promise);
    return promise;
  }

  function populateScheduleOptions(selectEl, blocks, selectedId) {
    if (!selectEl) return;
    selectEl.innerHTML = '<option value="">Unassigned</option>';
    blocks.forEach((block) => {
      const label = `${block.day} — ${block.title || 'Untitled'} (${block.start_time || ''})`;
      const opt = document.createElement('option');
      opt.value = String(block.id);
      opt.textContent = label;
      selectEl.appendChild(opt);
    });
    
    // Set the selected value after all options are added
    if (selectedId !== undefined && selectedId !== null && selectedId !== '') {
      selectEl.value = String(selectedId);
      console.log('Setting schedule dropdown to:', selectedId, 'Result:', selectEl.value);
    }
  }

  async function fillAndShowModal(presentation) {
    const modalEl = document.getElementById('editPresentationModal');
    if (!modalEl) return;

    // Store the presentation data to reapply after form cloning
    window._currentPresentationData = presentation;

    // Pre-fetch blocks filtered by presentation type (if provided)
    const blocks = await fetchAssignableBlocks(presentation.type || '');
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

    const scheduleSelect = modalEl.querySelector('#editPresentationSchedule');
    if (window._assignableBlocks) {
      populateScheduleOptions(scheduleSelect, window._assignableBlocks, presentation.schedule_id);
    }

    // populate hidden presentation id so the form includes it explicitly
    const idInput = modalEl.querySelector('#editPresentationId');
    if (idInput) idInput.value = presentation.id || '';
  }

  function setupFormSubmit(onSubmit) {
    const form = document.getElementById('editPresentationForm');
    if (!form) return;

    // Replace the form with a clone to remove any previously attached listeners.
    // This prevents multiple submissions being sent when the modal is opened repeatedly.
    const newForm = form.cloneNode(true);
    form.parentNode.replaceChild(newForm, form);

    // After cloning, repopulate the form fields with the stored presentation data
    if (window._currentPresentationData) {
      populateFormFields(window._currentPresentationData);
    }

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
