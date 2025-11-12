(function () {
  function fillAndShowModal(user) {
    const modalEl = document.getElementById('editUserModal');
    if (!modalEl) return;

    modalEl.querySelector('#editUserFirstName').value = user.firstname || '';
    modalEl.querySelector('#editUserLastName').value = user.lastname || '';
    modalEl.querySelector('#editUserEmail').value = user.email || '';
    modalEl.querySelector('#editUserRole').value = user.auth || 'presenter';
    //print user role:
    console.log('User role:', user.auth);
    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    modal.show();
  }

  function setupFormSubmit(onSubmit) {
    const form = document.getElementById('editUserForm');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
      e.preventDefault();

      const formData = new FormData(form);
      const data = Object.fromEntries(formData.entries());

      try {
        await onSubmit(data);
        bootstrap.Modal.getInstance(form.closest('.modal')).hide();
      } catch (err) {
        console.error('Failed to submit form:', err);
        alert('Error saving user changes.');
      }
    });
  }

  window.EditModal = {
    fillAndShowModal,
    setupFormSubmit,
  };
})();
