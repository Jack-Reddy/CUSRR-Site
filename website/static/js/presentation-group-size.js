(function () {
  const MAX_PRESENTERS_PER_GROUP = 5;
  const partnerFields = [
    { id: 'partner-email', wrapperId: null, label: 'Partner 1 Email' },
    { id: 'partner-email-two', wrapperId: 'partner-two-wrapper', label: 'Partner 2 Email' },
    { id: 'partner-email-three', wrapperId: 'partner-three-wrapper', label: 'Partner 3 Email' },
    { id: 'partner-email-four', wrapperId: 'partner-four-wrapper', label: 'Partner 4 Email' },
  ];

  function ensureGroupSizeOptions() {
    const groupThree = document.getElementById('group-size-three');
    const groupThreeWrapper = groupThree ? groupThree.closest('.form-check') : null;
    if (!groupThreeWrapper) return;

    let insertAfter = groupThreeWrapper;
    for (let size = 4; size <= MAX_PRESENTERS_PER_GROUP; size += 1) {
      if (document.getElementById(`group-size-${size}`)) {
        insertAfter = document.getElementById(`group-size-${size}`).closest('.form-check') || insertAfter;
        continue;
      }

      const wrapper = document.createElement('div');
      wrapper.className = 'form-check form-check-inline';
      wrapper.innerHTML = `
        <input class="form-check-input" type="radio" name="presentation-group-size" id="group-size-${size}" value="${size}">
        <label class="form-check-label" for="group-size-${size}">Group of ${size}</label>
      `;
      insertAfter.after(wrapper);
      insertAfter = wrapper;
    }
  }

  function ensureExtraPartnerFields() {
    const partnerDetails = document.getElementById('partner-details');
    const partnerTwoWrapper = document.getElementById('partner-two-wrapper');
    if (!partnerDetails || !partnerTwoWrapper) return;

    let insertAfter = partnerTwoWrapper;
    partnerFields.slice(2).forEach((field) => {
      let wrapper = document.getElementById(field.wrapperId);
      if (!wrapper) {
        wrapper = document.createElement('div');
        wrapper.id = field.wrapperId;
        wrapper.className = 'mt-3 d-none';
        wrapper.innerHTML = `
          <label for="${field.id}" class="form-label w-100">${field.label}</label>
          <input id="${field.id}" type="email" class="form-control" placeholder="partner@example.com">
        `;
        insertAfter.after(wrapper);
      }
      insertAfter = wrapper;
    });
  }

  function enhancedGetGroupSize() {
    const selected = document.querySelector('input[name="presentation-group-size"]:checked');
    return parseInt(selected?.value || '1', 10);
  }

  function enhancedGetPartnerEmails() {
    const groupSize = enhancedGetGroupSize();
    const emails = [];

    partnerFields.slice(0, Math.max(groupSize - 1, 0)).forEach((field) => {
      const value = document.getElementById(field.id)?.value.trim();
      if (value) emails.push(value);
    });

    return emails;
  }

  function enhancedSetupPartnerFields() {
    ensureGroupSizeOptions();
    ensureExtraPartnerFields();

    const groupRadios = document.querySelectorAll('input[name="presentation-group-size"]');
    const partnerDetails = document.getElementById('partner-details');
    const abstractMain = document.getElementById('abstract-main-fields');
    const submitterMe = document.getElementById('submitter-me');
    const submitterPartner = document.getElementById('submitter-partner');

    if (!groupRadios.length || !partnerDetails || !abstractMain) return;

    const updateVisibility = () => {
      const groupSize = enhancedGetGroupSize();
      const groupHasPartners = groupSize > 1;
      const someoneElseSubmitting = groupHasPartners && submitterPartner && submitterPartner.checked;

      partnerDetails.classList.toggle('d-none', !groupHasPartners);
      partnerFields.forEach((field, index) => {
        if (!field.wrapperId) return;
        const wrapper = document.getElementById(field.wrapperId);
        if (wrapper) wrapper.classList.toggle('d-none', groupSize < index + 2);
      });
      abstractMain.classList.toggle('d-none', someoneElseSubmitting);
    };

    groupRadios.forEach((radio) => radio.addEventListener('change', updateVisibility));
    if (submitterMe) submitterMe.addEventListener('change', updateVisibility);
    if (submitterPartner) submitterPartner.addEventListener('change', updateVisibility);

    updateVisibility();
  }

  window.getGroupSize = enhancedGetGroupSize;
  window.getPartnerEmails = enhancedGetPartnerEmails;
  window.setupPartnerFields = enhancedSetupPartnerFields;

  try {
    getGroupSize = enhancedGetGroupSize;
    getPartnerEmails = enhancedGetPartnerEmails;
    setupPartnerFields = enhancedSetupPartnerFields;
  } catch (error) {
    // Global rebinding can fail in stricter runtimes; window assignments above still work.
  }

  document.addEventListener('DOMContentLoaded', enhancedSetupPartnerFields);
})();
