(function () {
  function toLocalDatetimeValue(val) {
    if (!val) return '';
    const d = new Date(val);
    if (Number.isNaN(d.getTime())) return '';
    const pad = (n) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }

  function fillAndShowModal(block) {
    const modalEl = document.getElementById('editBlockModal');
    if (!modalEl) return;

    // Store the block data to reapply after form cloning
    window._currentBlockData = block;

    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    modal.show();
  }

  function populateFormFields(block) {
    const modalEl = document.getElementById('editBlockModal');
    if (!modalEl) return;

    modalEl.querySelector('#editBlockId').value = block.id || '';
    modalEl.querySelector('#editBlockDay').value = block.day || '';
    modalEl.querySelector('#editBlockTitle').value = block.title || '';
    modalEl.querySelector('#editBlockDescription').value = block.description || '';
    modalEl.querySelector('#editBlockLocation').value = block.location || '';
    modalEl.querySelector('#editBlockSubLength').value = block.sub_length || '';

    try {
      const startVal = block.startTime || block.start_time || block.start || null;
      const endVal = block.endTime || block.end_time || block.end || null;
      const startInput = modalEl.querySelector('#editBlockStart');
      const endInput = modalEl.querySelector('#editBlockEnd');
      if (startInput) startInput.value = toLocalDatetimeValue(startVal);
      if (endInput) endInput.value = toLocalDatetimeValue(endVal);
    } catch (err) {
      // ignore formatting errors
    }

    // Handle both block_type and type, with validation for dropdown
    const blockType = block.block_type || block.type || '';
    const typeSelect = modalEl.querySelector('#editBlockType');
    const validTypes = ['Break', 'Keynote', 'Poster', 'Presentation', 'Blitz'];
    if (typeSelect && blockType) {
      // Find matching type case-insensitively
      const matchedType = validTypes.find(t => t.toLowerCase() === blockType.toLowerCase());
      if (matchedType) {
        typeSelect.value = matchedType;
      }
    }
  }

  function setupFormSubmit(onSubmit) {
    const form = document.getElementById('editBlockForm');
    if (!form) return;
    if (typeof onSubmit !== 'function') return;

    // Replace with clone to remove previous listeners
    const newForm = form.cloneNode(true);
    form.parentNode.replaceChild(newForm, form);

    // After cloning, repopulate the form fields with the stored block data
    if (window._currentBlockData) {
      populateFormFields(window._currentBlockData);
    }

    newForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const formData = new FormData(newForm);
      const data = Object.fromEntries(formData.entries());

      // normalize numeric field
      if (data.sub_length === "") delete data.sub_length;

      try {
        await onSubmit(data);
        bootstrap.Modal.getInstance(newForm.closest('.modal')).hide();
      } catch (err) {
        console.error('Failed to submit block form:', err);
        alert('Error saving block changes.');
      }
    });
  }

  function setupDeleteButton(onDelete) {
    const deleteBtn = document.getElementById('deleteBlockBtn');
    if (!deleteBtn) return;
    if (typeof onDelete !== 'function') return;

    // Clone to remove previous listeners
    const newBtn = deleteBtn.cloneNode(true);
    deleteBtn.parentNode.replaceChild(newBtn, deleteBtn);

    newBtn.addEventListener('click', async () => {
      if (!confirm('Are you sure you want to delete this block? This action cannot be undone.')) {
        return;
      }

      try {
        await onDelete();
        const modalEl = document.getElementById('editBlockModal');
        if (modalEl) {
          bootstrap.Modal.getInstance(modalEl).hide();
        }
      } catch (err) {
        console.error('Failed to delete block:', err);
        alert('Error deleting block.');
      }
    });
  }

  window.EditBlockModal = {
    fillAndShowModal,
    setupFormSubmit,
    setupDeleteButton,
  };
})();
