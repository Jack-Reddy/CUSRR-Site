// Delete account
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

// Load account info into tab 1
async function account_info() {
  const div = document.getElementById('account-info-container');
  if (!div) return;

  try {
    const meResponse = await fetch('/me');
    if (!meResponse.ok) {
      throw new Error(`Failed to get user info: ${meResponse.status} ${meResponse.statusText}`);
    }

    // Create or get a message container
    let msgDiv = document.getElementById(messageDivId);
    if (!msgDiv) {
        msgDiv = document.createElement('div');
        msgDiv.id = messageDivId;
        msgDiv.classList.add('mt-3');
        div.prepend(msgDiv);
    }
    msgDiv.innerHTML = ''; // Clear previous messages

    try {
        // Fetch user info
        const meResponse = await fetch('/me');
        if (!meResponse.ok) throw new Error(`Failed to get user info: ${meResponse.status}`);
        const user = await meResponse.json();
        if (!user.authenticated) {
            msgDiv.innerHTML = '<p class="text-danger">You must be signed in to create a presentation.</p>';
            return;
        }

        // Get form values
        const title = document.getElementById('title').value.trim();
        const abstract = document.getElementById('Abstract').value.trim();
        const subject = document.getElementById('subject').value.trim();
        const typeSelect = document.getElementById('Type');
        const type = typeSelect.value.trim();

        if (!title || !abstract || !subject || !type) {
            msgDiv.innerHTML = '<p class="text-danger">Please fill in all required fields.</p>';
            return;
        }
        
        console.log('Selected type:', type);
        
        // Get Unassigned block for the selected type
        let assignedBlockId = null;
        try {
            const response2 = await fetch('/api/v1/block-schedule/day/Unassigned');
            if (response2.ok) {
                const unassignedBlocks = await response2.json();
                console.log('Unassigned blocks:', unassignedBlocks);
                console.log('Looking for type:', type);
                
                // Match block_type case-insensitively with selected type
                const unassignedBlock = unassignedBlocks.find(b => {
                    console.log('Checking block:', b.id, 'type:', b.type);
                    return (b.type && b.type.toLowerCase() === type.toLowerCase()) ||
                           (b.block_type && b.block_type.toLowerCase() === type.toLowerCase());
                });
                
                if (unassignedBlock) {
                    assignedBlockId = unassignedBlock.id;
                    console.log('Found matching block:', assignedBlockId);
                } else {
                    console.log('No matching block found for type:', type);
                }
            } else {
                console.log('Failed to fetch unassigned blocks:', response2.status);
            }
        } catch (err) {
            console.warn('Could not fetch unassigned blocks:', err);
            // Continue without assigning to a block
        }
        
        console.log('Final assignedBlockId:', assignedBlockId);

        // Submit abstract
        const response = await fetch('/api/v1/presentations/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title,
                abstract,
                subject,
                schedule_id: assignedBlockId
            })
        });

        if (!response.ok) throw new Error(`Failed to submit abstract: ${response.status}`);

        const resultData = await response.json();

        // Update user with presentation_id
        const userUpdate = await fetch(`/api/v1/users/${user.user_id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ presentation_id: resultData.id })
        });

        if (!userUpdate.ok) throw new Error(`Failed to update user: ${userUpdate.status}`);

        // Show success and switch to full presentation form
        msgDiv.innerHTML = `<p class="text-success">Abstract submitted successfully! Title: ${resultData.title}.</p>`;

        // Hide abstract form, show presentation form
        document.getElementById('abstract-form').classList.add('d-none');
        document.getElementById('presentation-form').classList.remove('d-none');

    } catch (error) {
        console.error('Error during signup:', error);
        msgDiv.innerHTML = '<p class="text-danger">Signup failed. Please try again later.</p>';
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

    // Show partner details only if they have a partner
    if (hasPartner) {
      partnerDetails.classList.remove('d-none');
    } else {
      partnerDetails.classList.add('d-none');
    }

    const partnerIsSubmitting = hasPartner && submitterPartner && submitterPartner.checked;

    // If partner is submitting, hide abstract fields (this user isn't submitting anything)
    if (partnerIsSubmitting) {
      abstractMain.classList.add('d-none');
    } else {
      abstractMain.classList.remove('d-none');
    }
  };

  yesRadio.addEventListener('change', updateVisibility);
  noRadio.addEventListener('change', updateVisibility);
  if (submitterMe) submitterMe.addEventListener('change', updateVisibility);
  if (submitterPartner) submitterPartner.addEventListener('change', updateVisibility);

  updateVisibility();
}


// Decide which form to show (abstract vs upload) based on /me
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

    if (!abstractForm || !presentationForm) {
      console.error('Form containers not found!');
      return;
    }

    if (user.presentation_id) {
      // An abstract already exists for this user (or their pair)
      abstractForm.classList.add('d-none');
      presentationForm.classList.remove('d-none');
    } else {
      // No abstract yet -> show abstract form
      abstractForm.classList.remove('d-none');
      presentationForm.classList.add('d-none');
    }
  } catch (err) {
    console.error('Error setting up presentation field:', err);
  }
}
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
    // 1. Get user
    const meResponse = await fetch('/me');
    if (!meResponse.ok) throw new Error(`Failed to get user info: ${meResponse.status}`);
    const user = await meResponse.json();
    if (!user.authenticated) {
      msgDiv.innerHTML = '<p class="text-danger">You must be signed in to create a presentation.</p>';
      return;
    }

    // 2. Partner-related logic
    const hasPartnerRadio = document.querySelector('input[name="has-partner"]:checked');
    const hasPartner = hasPartnerRadio ? hasPartnerRadio.value === 'yes' : false;

    const submitterRoleRadio = document.querySelector('input[name="submitter-role"]:checked');
    const submitterRole = submitterRoleRadio ? submitterRoleRadio.value : 'me';

    const partnerEmailInput = document.getElementById('partner-email');
    const partnerEmail = partnerEmailInput ? partnerEmailInput.value.trim() : '';

    // CASE 1: Have partner, partner is submitting → no abstract, no email required, no request
    if (hasPartner && submitterRole === 'partner') {
      msgDiv.innerHTML = `
        <p class="text-info">
          You indicated that your partner will submit the abstract and presentation 
          for your pair. You do not need to submit anything here.
        </p>
      `;
      return;
    }

    // CASE 2: Have partner, I am submitting → partner email REQUIRED
    if (hasPartner && submitterRole === 'me') {
      if (!partnerEmail) {
        msgDiv.innerHTML = '<p class="text-danger">Please enter your partner\'s email.</p>';
        return;
      }
    }

    // CASE 3: No partner → ignore email completely

    // 3. Abstract fields (for whoever IS submitting)
    const title = document.getElementById('title').value.trim();
    const abstract = document.getElementById('Abstract').value.trim();
    const subject = document.getElementById('subject').value.trim();
    const typeSelect = document.getElementById('Type');
    const type = typeSelect.options[typeSelect.selectedIndex].text;

    if (!title || !abstract || !subject) {
      msgDiv.innerHTML = '<p class="text-danger">Please fill in all required fields.</p>';
      return;
    }

    // 4. Build payload. Only add partner_email in CASE 2.
    const payload = {
      title,
      abstract,
      subject,
      time: '2026-11-04 13:30', // still fine for datetime.fromisoformat
      room: null
      // type is currently not used in backend; add if you add a column
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
      const errData = await response.json().catch(() => ({}));
      console.error('Submit error:', errData);
      throw new Error(`Failed to submit abstract: ${response.status}`);
    }

    const resultData = await response.json();

    // 6. Tie this presentation to the currently logged-in user
    const userUpdate = await fetch(`/api/v1/users/${user.user_id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ presentation_id: resultData.id })
    });

    if (!userUpdate.ok) throw new Error(`Failed to update user: ${userUpdate.status}`);

    msgDiv.innerHTML = `
      <p class="text-success">
        Abstract submitted successfully! Title: ${resultData.title}.
        ${hasPartner && submitterRole === 'me'
          ? '<br>Remember: only one abstract and one presentation per pair.'
          : ''}
      </p>
    `;

    document.getElementById('abstract-form').classList.add('d-none');
    document.getElementById('presentation-form').classList.remove('d-none');
  } catch (error) {
    console.error('Error during signup:', error);
    msgDiv.innerHTML = '<p class="text-danger">Submission failed. Please try again later.</p>';
  }
}


// Upload final PPT/PPTX
async function uploadPresentation() {
  const fileInput = document.getElementById('presentation-ppt');
  if (!fileInput || !fileInput.files.length) {
    alert("Please select a presentation file first.");
    return;
  }

  // Optional: basic size limit check (20MB)
  const file = fileInput.files[0];
  const maxBytes = 20 * 1024 * 1024;
  if (file.size > maxBytes) {
    alert("File is too large. Max size is 20MB.");
    return;
  }

  // Get logged-in user (we need presentation_id)
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

  // Optionally send title/notes if you want to use them
  const finalTitle = document.getElementById('final-title')?.value || '';
  const notes = document.getElementById('presentation-notes')?.value || '';
  formData.append("title", finalTitle);
  formData.append("notes", notes);

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

// Wire everything up
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
