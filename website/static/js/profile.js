// =====================================================
// LOAD ACCOUNT INFO  (TAB 1)
// =====================================================
async function account_info() {
  const div = document.getElementById('account-info-container');
  if (!div) return;

  try {
    const meResponse = await fetch('/me');
    if (!meResponse.ok) {
      throw new Error(`Failed to get user info: ${meResponse.status} ${meResponse.statusText}`);
    }

    const user = await meResponse.json();

    if (!user.authenticated) {
      div.innerHTML = '<p class="text-danger">You must be signed in to view account information.</p>';
      return;
    }

    div.innerHTML = `
      <p><strong>Name:</strong> ${user.name}</p>
      <p><strong>Email:</strong> ${user.email}</p>
      <p><strong>Role:</strong> ${user.auth}</p>
      <p><strong>Class Year:</strong> ${user.student_year || 'N/A'}</p>
      <p><strong>Activity:</strong> ${user.activity || 'N/A'}</p>
      <p><strong>Presentation ID:</strong> ${user.presentation_id || 'N/A'}</p>
    `;

  } catch (error) {
    console.error('Error fetching account info:', error);
    div.innerHTML = '<p class="text-danger">Could not load account information.</p>';
  }
}


// =====================================================
// ROOMMATE PREFERENCES
// =====================================================
async function loadRoommatePreferences() {
  const textarea = document.getElementById('roommate-preferences');
  if (!textarea) return;

  try {
    const response = await fetch('/api/v1/users/roommate-preferences');
    if (!response.ok) return;
    const data = await response.json();
    textarea.value = data.preferences || '';
  } catch (error) {
    console.warn('Could not load roommate preferences:', error);
  }
}

async function saveRoommatePreferences() {
  const textarea = document.getElementById('roommate-preferences');
  const messageDiv = document.getElementById('roommate-preferences-message');
  if (!textarea) return;

  try {
    const response = await fetch('/api/v1/users/roommate-preferences', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ preferences: textarea.value.trim() })
    });

    if (!response.ok) throw new Error('Failed to save roommate preferences');

    if (messageDiv) {
      messageDiv.className = 'small mt-2 text-success';
      messageDiv.textContent = 'Roommate preferences saved.';
    }
  } catch (error) {
    console.error('Error saving roommate preferences:', error);
    if (messageDiv) {
      messageDiv.className = 'small mt-2 text-danger';
      messageDiv.textContent = 'Could not save roommate preferences.';
    }
  }
}


// =====================================================
// GROUP FIELD LOGIC
// =====================================================
function getGroupSize() {
  const selected = document.querySelector('input[name="presentation-group-size"]:checked');
  return parseInt(selected?.value || '1', 10);
}

function getPartnerEmails() {
  const groupSize = getGroupSize();
  const emails = [];
  const first = document.getElementById('partner-email')?.value.trim();
  const second = document.getElementById('partner-email-two')?.value.trim();

  if (groupSize >= 2 && first) emails.push(first);
  if (groupSize >= 3 && second) emails.push(second);
  return emails;
}

function setupPartnerFields() {
  const groupRadios = document.querySelectorAll('input[name="presentation-group-size"]');
  const partnerDetails = document.getElementById('partner-details');
  const partnerTwoWrapper = document.getElementById('partner-two-wrapper');
  const abstractMain = document.getElementById('abstract-main-fields');
  const submitterMe = document.getElementById('submitter-me');
  const submitterPartner = document.getElementById('submitter-partner');

  if (!groupRadios.length || !partnerDetails || !abstractMain) return;

  const updateVisibility = () => {
    const groupSize = getGroupSize();
    const groupHasPartners = groupSize > 1;
    const someoneElseSubmitting = groupHasPartners && submitterPartner && submitterPartner.checked;

    partnerDetails.classList.toggle('d-none', !groupHasPartners);
    if (partnerTwoWrapper) partnerTwoWrapper.classList.toggle('d-none', groupSize < 3);
    abstractMain.classList.toggle('d-none', someoneElseSubmitting);
  };

  groupRadios.forEach((radio) => radio.addEventListener('change', updateVisibility));
  if (submitterMe) submitterMe.addEventListener('change', updateVisibility);
  if (submitterPartner) submitterPartner.addEventListener('change', updateVisibility);

  updateVisibility();
}


function showLatestPresentationUpload(filename) {
  const latestDiv = document.getElementById('latest-presentation-upload');
  if (!latestDiv) return;

  if (!filename) {
    latestDiv.classList.add('d-none');
    latestDiv.textContent = '';
    return;
  }

  latestDiv.classList.remove('d-none');
  latestDiv.innerHTML = `<strong>Latest uploaded presentation:</strong> ${filename}`;
}

async function loadLatestPresentationUpload(user) {
  if (!user || !user.presentation_id) {
    showLatestPresentationUpload(null);
    return;
  }

  try {
    const response = await fetch(`/api/v1/presentations/${user.presentation_id}/upload/latest`);
    if (response.ok) {
      const data = await response.json();
      if (data.filename) {
        showLatestPresentationUpload(data.filename);
        localStorage.setItem(`latestPresentationUpload:${user.user_id}`, data.filename);
        return;
      }
    }
  } catch (error) {
    console.warn('Could not load latest uploaded presentation from server:', error);
  }

  showLatestPresentationUpload(localStorage.getItem(`latestPresentationUpload:${user.user_id}`));
}


// =====================================================
// SHOW EITHER ABSTRACT FORM OR PRESENTATION UPLOAD
// =====================================================
async function setupPresentationField() {
  try {
    const meResponse = await fetch('/me');
    if (!meResponse.ok) {
      console.error('Failed to get user info for presentation field setup.');
      return;
    }

    const user = await meResponse.json();

    if (!user.authenticated) {
      console.error('User not authenticated for presentation field setup.');
      return;
    }

    const abstractForm = document.getElementById('abstract-form');
    const presentationForm = document.getElementById('presentation-form');

    if (user.presentation_id) {
      abstractForm.classList.add('d-none');
      presentationForm.classList.remove('d-none');
      loadLatestPresentationUpload(user);
    } else {
      abstractForm.classList.remove('d-none');
      presentationForm.classList.add('d-none');
      showLatestPresentationUpload(null);
    }

  } catch (err) {
    console.error('Error setting up presentation field:', err);
  }
}


// =====================================================
// SUBMIT ABSTRACT
// =====================================================
async function signupAbstract() {
  const div = document.getElementById('abstract-form');
  const messageDivId = 'abstract-message';

  if (!div) {
    console.error('Abstract form not found!');
    return;
  }

  let msgDiv = document.getElementById(messageDivId);
  if (!msgDiv) {
    msgDiv = document.createElement('div');
    msgDiv.id = messageDivId;
    msgDiv.classList.add('mt-3');
    div.prepend(msgDiv);
  }
  msgDiv.innerHTML = '';

  try {
    // 1. User
    const meResponse = await fetch('/me');
    if (!meResponse.ok) throw new Error(`Failed to get user info`);
    const user = await meResponse.json();

    if (!user.authenticated) {
      msgDiv.innerHTML = '<p class="text-danger">You must be signed in to create a presentation.</p>';
      return;
    }

    // 2. Group logic
    const groupSize = getGroupSize();
    const submitterRole = document.querySelector('input[name="submitter-role"]:checked')?.value || 'me';
    const partnerEmails = getPartnerEmails();

    if (groupSize > 1 && submitterRole === 'partner') {
      msgDiv.innerHTML = `
        <p class="text-info">
          Someone else in your group will submit the abstract. You do not need to submit anything.
        </p>`;
      return;
    }

    if (groupSize > 1 && partnerEmails.length !== groupSize - 1) {
      msgDiv.innerHTML = '<p class="text-danger">Please enter the email for each partner in your group.</p>';
      return;
    }

    const uniqueEmails = new Set(partnerEmails.map((email) => email.toLowerCase()));
    if (uniqueEmails.size !== partnerEmails.length) {
      msgDiv.innerHTML = '<p class="text-danger">Please enter different emails for each partner.</p>';
      return;
    }

    // 3. Abstract fields
    const title = document.getElementById('title').value.trim();
    const abstract = document.getElementById('Abstract').value.trim();
    const department = document.getElementById('department')?.value.trim() || '';
    const mentor = document.getElementById('mentor')?.value.trim() || '';
    const keywords = document.getElementById('keywords')?.value.trim() || '';
    const typeSelect = document.getElementById('Type');
    const type = typeSelect.options[typeSelect.selectedIndex].value;

    if (!title || !abstract || !type || typeSelect.selectedIndex === 0) {
      msgDiv.innerHTML = '<p class="text-danger">Please fill in all required fields.</p>';
      return;
    }

    // 4. Build payload
    const payload = {
      title,
      abstract,
      department,
      mentor,
      keywords,
      type,
      partner_emails: partnerEmails,
      time: '2026-11-04 13:30',
      room: null
    };

    // 5. Create presentation
    const response = await fetch('/api/v1/presentations/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({ error: 'Failed to submit abstract' }));
      throw new Error(err.error || 'Failed to submit abstract');
    }

    const resultData = await response.json();

    // 6. Assign to user
    const userUpdate = await fetch(`/api/v1/users/${user.user_id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ presentation_id: resultData.id })
    });

    if (!userUpdate.ok) throw new Error('Failed to update user');

    msgDiv.innerHTML = `
      <p class="text-success">
        Abstract submitted successfully! Title: ${resultData.title}.
      </p>
    `;

    // Switch to presentation form
    document.getElementById('abstract-form').classList.add('d-none');
    document.getElementById('presentation-form').classList.remove('d-none');
    loadLatestPresentationUpload({ ...user, presentation_id: resultData.id });

  } catch (error) {
    console.error('Error during signup:', error);
    msgDiv.innerHTML = `<p class="text-danger">Submission failed: ${error.message}</p>`;
  }
}


// =====================================================
// UPLOAD FINAL PRESENTATION FILE
// =====================================================
async function uploadPresentation() {
  const fileInput = document.getElementById('presentation-ppt');
  if (!fileInput || !fileInput.files.length) {
    alert("Please select a presentation file first.");
    return;
  }

  const file = fileInput.files[0];
  const maxBytes = 20 * 1024 * 1024;
  const allowedExtensions = ['ppt', 'pptx', 'pdf'];
  const extension = file.name.split('.').pop().toLowerCase();

  if (!allowedExtensions.includes(extension)) {
    alert("Invalid file type. Please upload a PPT, PPTX, or PDF file.");
    return;
  }

  if (file.size > maxBytes) {
    alert("File is too large. Max size is 20MB.");
    return;
  }

  const meResponse = await fetch('/me');
  if (!meResponse.ok) {
    alert("Unable to verify user.");
    return;
  }

  const user = await meResponse.json();
  if (!user.presentation_id) {
    alert("You must submit an abstract before uploading your final presentation.");
    return;
  }

  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`/api/v1/presentations/${user.presentation_id}/upload`, {
    method: "POST",
    body: formData
  });

  if (response.ok) {
    const data = await response.json().catch(() => ({}));
    const filename = data.filename || file.name;
    localStorage.setItem(`latestPresentationUpload:${user.user_id}`, filename);
    showLatestPresentationUpload(filename);
    alert("Presentation uploaded successfully!");
    fileInput.value = "";
  } else {
    const err = await response.json().catch(() => ({ error: "Upload failed" }));
    alert("Error: " + err.error);
  }
}


// =====================================================
// EVENT WIRING
// =====================================================
window.addEventListener('DOMContentLoaded', () => {
  console.log('DOMContentLoaded fired');

  if (window.AbstractMarkdownEditor) {
    window.AbstractMarkdownEditor.initEditor({
      textareaId: 'Abstract',
      toolbarId: 'abstract-toolbar',
      previewId: 'abstract-preview',
    });
  }

  setupPresentationField();
  account_info();
  setupPartnerFields();
  loadRoommatePreferences();

  const abstractBtn = document.getElementById('abstract-submit');
  if (abstractBtn) {
    abstractBtn.addEventListener('click', (e) => {
      e.preventDefault();
      signupAbstract();
    });
  }

  const roommateBtn = document.getElementById('roommate-preferences-submit');
  if (roommateBtn) {
    roommateBtn.addEventListener('click', (e) => {
      e.preventDefault();
      saveRoommatePreferences();
    });
  }

  const presentationBtn = document.getElementById('presentation-submit');
  if (presentationBtn) {
    presentationBtn.addEventListener('click', (e) => {
      e.preventDefault();
      uploadPresentation();
    });
  }
});