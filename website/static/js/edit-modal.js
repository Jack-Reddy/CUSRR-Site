(function () {
  function normalizeRoleForSelect(auth) {
    const roles = String(auth || '')
      .split(',')
      .map((role) => role.trim().toLowerCase())
      .filter(Boolean);

    const knownRoles = ['admin', 'organizer', 'judge', 'abstract-grader', 'presenter', 'attendee', 'banned'];
    return roles.find((role) => knownRoles.includes(role)) || 'presenter';
  }

  async function errorMessageFromResponse(response, fallback) {
    const data = await response.json().catch(() => ({}));
    return data.error || data.reason || fallback;
  }

  function setSelectValue(select, value, fallback = '') {
    if (!select) return;
    const wanted = String(value || '').trim();
    const option = Array.from(select.options).find((item) => item.value.toLowerCase() === wanted.toLowerCase());
    select.value = option ? option.value : fallback;
  }

  function fillAndShowModal(user) {
    const modalEl = document.getElementById('editUserModal');
    if (!modalEl) return;

    modalEl.querySelector('#editUserFirstName').value = user.firstname || '';
    modalEl.querySelector('#editUserLastName').value = user.lastname || '';
    modalEl.querySelector('#editUserEmail').value = user.email || '';
    modalEl.querySelector('#editUserRole').value = normalizeRoleForSelect(user.auth);

    setSelectValue(modalEl.querySelector('#editUserActivity'), user.activity);

    const presentationTypeSelect = modalEl.querySelector('#editUserPresentationType');
    setSelectValue(presentationTypeSelect, user.presentation_type);
    if (presentationTypeSelect) {
      const hasPresentation = Boolean(user.presentation_id);
      presentationTypeSelect.disabled = !hasPresentation;
      presentationTypeSelect.title = hasPresentation ? '' : 'Assign a presentation before setting presentation type.';
    }

    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    modal.show();
  }

  function setupFormSubmit(onSubmit) {
    const form = document.getElementById('editUserForm');
    if (!form) return;

    // Replace any existing submit handler to avoid duplicate bindings
    form.onsubmit = async (e) => {
      e.preventDefault();

      const formData = new FormData(form);
      const data = Object.fromEntries(formData.entries());

      try {
        await onSubmit(data, errorMessageFromResponse);
        bootstrap.Modal.getInstance(form.closest('.modal')).hide();
      } catch (err) {
        console.error('Failed to submit form:', err);
        alert(err.message || 'Error saving user changes.');
      }
    };
  }

  window.EditModal = {
    fillAndShowModal,
    setupFormSubmit,
  };
})();