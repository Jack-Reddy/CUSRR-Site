(function () {
  function populateFormFields(presentation) {
    const modalEl = document.getElementById('editPresentationModal');
    if (!modalEl) return;

    modalEl.querySelector('#editPresentationTitle').value = presentation.title || '';
    modalEl.querySelector('#editPresentationAbstract').value = presentation.abstract || '';
    modalEl.querySelector('#editPresentationSubject').value = presentation.subject || '';
    modalEl.querySelector('#editPresentationDepartment').value = presentation.department || '';
    modalEl.querySelector('#editPresentationMentor').value = presentation.mentor || '';
    modalEl.querySelector('#editPresentationKeywords').value = presentation.keywords || '';

    const showOnScheduleCheckbox = modalEl.querySelector('#editPresentationShowOnSchedule');
    if (showOnScheduleCheckbox) {
      showOnScheduleCheckbox.checked = presentation.show_on_schedule !== false;
    }

    const idInput = modalEl.querySelector('#editPresentationId');
    if (idInput) idInput.value = presentation.id || '';
  }

  async function fillAndShowModal(presentation) {
    const modalEl = document.getElementById('editPresentationModal');
    if (!modalEl) return;

    window._currentPresentationData = presentation;
    populateFormFields(presentation);

    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    modal.show();
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