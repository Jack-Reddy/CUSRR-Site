
removeUser = async function() {
  if (!confirm('Are you sure you want to delete this user? This action cannot be undone.')) {
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
    loadUsers(); // Refresh the user list
  
  } catch (err) {
    console.error('Failed to delete user', err);
    alert('Could not delete user.');
  } 
}

async function signupPresentation() {
    const div = document.getElementById('signup-container');



    if (!div) {
        console.error('Signup container not found!');
        return;
    }

    

    try {
        const meResponse = await fetch('/me');
        if (!meResponse.ok) {
            throw new Error(`Failed to get user info: ${meResponse.status} ${meResponse.statusText}`);
        }

        const user = await meResponse.json();
        if (!user.authenticated) {
            div.innerHTML = '<p class="text-danger">You must be signed in to create presentation.</p>';
            return;
        }

        const activitySelect = document.getElementById('Type');

        const response = await fetch('/api/v1/presentations/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                title: document.getElementById('title').value,
                abstract: document.getElementById('Abstract').value,
                subject: null,
                time: "2026-11-04 13:30", // Placeholder time for presentation
                room: null,
                type: activitySelect.options[activitySelect.selectedIndex].text
            })
        });

        if (!response.ok) {
            throw new Error(`Network response was not ok: ${response.status} ${response.statusText}`);
        }

        const resultData = await response.json();

        const result = await fetch(`api/v1/users/${user.user_id}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                presentation_id: resultData.id
            })
        });

        div.innerHTML = `<p class="text-success">Presentation signup successful! Title: ${resultData.title}.</p>`;
    } catch (error) {
        console.error('Error during signup:', error);
        div.innerHTML = '<p class="text-danger">Signup failed. Please try again later.</p>';
    }
}

setupSignupButton = () => {
    const btn = document.getElementById('signup-submit');
    //print 
    console.log('Signup button found:', btn);
    if (btn) {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            signupPresentation();
        });
    }
}

window.addEventListener('DOMContentLoaded', () => {
    setupSignupButton();
    document.getElementById('delete-account-btn').addEventListener('click', removeUser);
});