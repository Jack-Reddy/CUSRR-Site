(function () {
  function fillAndShowModal(presentation) {
    const modalEl = document.getElementById('editPresentationModal');
    if (!modalEl) return;

    modalEl.querySelector('#editPresentationTitle').value = presentation.title || '';
    modalEl.querySelector('#editPresentationAbstract').value = presentation.abstract || '';
    modalEl.querySelector('#editPresentationSubject').value = presentation.subject || '';

    console.log('Editing presentation:', presentation);

    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    modal.show();
  }

  function setupFormSubmit(onSubmit) {
    const form = document.getElementById('editPresentationForm');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
      e.preventDefault();

      const formData = new FormData(form);
      const data = Object.fromEntries(formData.entries());

      try {
        await onSubmit(data);
        bootstrap.Modal.getInstance(form.closest('.modal')).hide();
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
