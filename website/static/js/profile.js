// =====================================================
// DELETE ACCOUNT
// =====================================================
removeUser = async function () {
  if (!confirm('Are you sure you want to delete your account? This action cannot be undone.')) {
    return;
  }

  try {
    const meResponse = await fetch('/me');
    if (!meResponse.ok) {
      throw new Error(`Failed to get user info: ${meResponse.status} ${meResponse.statusText}`);
    }

    const user = await meResponse.json();
    if (!user.authenticated) {
      alert('You must be signed in to delete your account.');
      return;
    }

    const userId = user.user_id;

    const response = await fetch(`/api/v1/users/${userId}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      throw new Error(`Network response was not ok: ${response.status} ${response.statusText}`);
    }

    window.location.href = '/';
  } catch (err) {
    console.error('Failed to delete user', err);
    alert('Could not delete user.');
  }
};



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
      <p><strong>Activity:</strong> ${user.activity || 'N/A'}</p>
      <p><strong>Presentation ID:</strong> ${user.presentation_id || 'N/A'}</p>
    `;

  } catch (error) {
    console.error('Error fetching account info:', error);
    div.innerHTML = '<p class="text-danger">Could not load account information.</p>';
  }
}




// =====================================================
// PARTNER FIELD LOGIC
// =====================================================
function setupPartnerFields() {
  const yesRadio = document.getElementById('has-partner-yes');
  const noRadio = document.getElementById('has-partner-no');
  const partnerDetails = document.getElementById('partner-details');
  const abstractMain = document.getElementById('abstract-main-fields');
  const submitterMe = document.getElementById('submitter-me');
  const submitterPartner = document.getElementById('submitter-partner');

  if (!yesRadio || !noRadio || !partnerDetails || !abstractMain) return;

  const updateVisibility = () => {
    const hasPartner = yesRadio.checked;
    const partnerIsSubmitting = hasPartner && submitterPartner && submitterPartner.checked;

    partnerDetails.classList.toggle('d-none', !hasPartner);
    abstractMain.classList.toggle('d-none', partnerIsSubmitting);
  };

  yesRadio.addEventListener('change', updateVisibility);
  noRadio.addEventListener('change', updateVisibility);
  if (submitterMe) submitterMe.addEventListener('change', updateVisibility);
  if (submitterPartner) submitterPartner.addEventListener('change', updateVisibility);

  updateVisibility();
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
    } else {
      abstractForm.classList.remove('d-none');
      presentationForm.classList.add('d-none');
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

    // 2. Partner logic
    const hasPartner = document.querySelector('input[name="has-partner"]:checked')?.value === 'yes';
    const submitterRole = document.querySelector('input[name="submitter-role"]:checked')?.value || 'me';
    const partnerEmail = document.getElementById('partner-email')?.value.trim() || '';

    if (hasPartner && submitterRole === 'partner') {
      msgDiv.innerHTML = `
        <p class="text-info">
          Your partner will submit the abstract. You do not need to submit anything.
        </p>`;
      return;
    }

    if (hasPartner && submitterRole === 'me' && !partnerEmail) {
      msgDiv.innerHTML = '<p class="text-danger">Please enter your partner\'s email.</p>';
      return;
    }

    // 3. Abstract fields
    const title = document.getElementById('title').value.trim();
    const abstract = document.getElementById('Abstract').value.trim();
    const subject = document.getElementById('subject').value.trim();
    const type = document.getElementById('Type').options[document.getElementById('Type').selectedIndex].text;

    if (!title || !abstract || !subject) {
      msgDiv.innerHTML = '<p class="text-danger">Please fill in all required fields.</p>';
      return;
    }

    // 4. Build payload
    const payload = {
      title,
      abstract,
      subject,
      time: '2026-11-04 13:30',
      room: null
    };

    if (hasPartner && submitterRole === 'me') {
      payload.partner_email = partnerEmail;
    }

    // 5. Create presentation
    const response = await fetch('/api/v1/presentations/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      throw new Error('Failed to submit abstract');
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

  } catch (error) {
    console.error('Error during signup:', error);
    msgDiv.innerHTML = '<p class="text-danger">Submission failed. Please try again later.</p>';
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
  formData.append("title", document.getElementById('final-title')?.value || '');
  formData.append("notes", document.getElementById('presentation-notes')?.value || '');

  const response = await fetch(`/api/v1/presentations/${user.presentation_id}/upload`, {
    method: "POST",
    body: formData
  });

  if (response.ok) {
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

  setupPresentationField();
  account_info();
  setupPartnerFields();

  const abstractBtn = document.getElementById('abstract-submit');
  if (abstractBtn) {
    abstractBtn.addEventListener('click', (e) => {
      e.preventDefault();
      signupAbstract();
    });
  }

  const deleteBtn = document.getElementById('delete-account-btn');
  if (deleteBtn) {
    deleteBtn.addEventListener('click', removeUser);
  }

  const presentationBtn = document.getElementById('presentation-submit');
  if (presentationBtn) {
    presentationBtn.addEventListener('click', (e) => {
      e.preventDefault();
      uploadPresentation();
    });
  }
});
