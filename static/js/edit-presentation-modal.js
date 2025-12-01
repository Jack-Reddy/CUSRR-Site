(function () {
  function fillAndShowModal(presentation) {
    const modalEl = document.getElementById('editPresentationModal');
    if (!modalEl) return;

    modalEl.querySelector('#editPresentationTitle').value = presentation.title || '';
    modalEl.querySelector('#editPresentationAbstract').value = presentation.abstract || '';
    modalEl.querySelector('#editPresentationSubject').value = presentation.subject || '';
    // populate hidden presentation id so the form includes it explicitly
    const idInput = modalEl.querySelector('#editPresentationId');
    if (idInput) idInput.value = presentation.id || '';

    console.log('Editing presentation:', presentation);

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
