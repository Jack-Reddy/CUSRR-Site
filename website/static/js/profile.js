
removeUser = async function() {
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
   
    window.location.href = '/'; // Redirect to homepage after deletion
  
  } catch (err) {
    console.error('Failed to delete user', err);
    alert('Could not delete user.');
  }
}

async function signupAbstract() {
    const div = document.getElementById('abstract-form');
    const messageDivId = 'abstract-message';

    if (!div) {
        console.error('Abstract form not found!');
        return;
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
}



async function account_info() {
    const div = document.getElementById('account-info-container');

    if (!div) {
        console.error('Account info container not found!');
        return;
    }

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

async function setupPresentationField() {
    try {
        // Fetch user info
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

        // Get form containers
        const abstractForm = document.getElementById('abstract-form');
        const presentationForm = document.getElementById('presentation-form');

        if (!abstractForm || !presentationForm) {
            console.error('Form containers not found!');
            return;
        }

        if (user.presentation_id) {
            // User has submitted abstract, show presentation form, hide abstract form
            abstractForm.classList.add('d-none');
            presentationForm.classList.remove('d-none');
            
        } else {
            // User has not submitted abstract, show abstract form, hide presentation form
            abstractForm.classList.remove('d-none');
            presentationForm.classList.add('d-none');
        }

    } catch (err) {
        console.error('Error setting up presentation field:', err);
    }
}
async function uploadPresentation() {
    const fileInput = document.getElementById('presentation-ppt');

    if (!fileInput || !fileInput.files.length) {
        alert("Please select a presentation file first.");
        return;
    }

    // Get the logged-in user (to get their presentation_id)
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
    formData.append("file", fileInput.files[0]);

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
document.getElementById("presentation-submit")
    ?.addEventListener("click", (e) => {
        e.preventDefault();
        uploadPresentation();
    });

window.addEventListener('DOMContentLoaded', () => {
    setupPresentationField();
    account_info();
    document.getElementById('abstract-submit')?.addEventListener('click', signupAbstract);
    document.getElementById('delete-account-btn').addEventListener('click', removeUser);
});