async function signup() {
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
            div.innerHTML = '<p class="text-danger">You must be signed in to sign up.</p>';
            return;
        }

        const activitySelect = document.getElementById('activity');

        const response = await fetch('/api/v1/users/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                firstname: document.getElementById('first-name').value,
                lastname: document.getElementById('last-name').value,
                activity: activitySelect.options[activitySelect.selectedIndex].text,
                email: user.email
            })
        });

        if (!response.ok) {
            throw new Error(`Network response was not ok: ${response.status} ${response.statusText}`);
        }

        const result = await response.json();
        div.innerHTML = `<p class="text-success">Signup successful! Welcome, ${result.name}.</p>`;

        setTimeout(() => {
            window.location.href = `/profile`; // or `/users/${result.id}` if applicable
        }, 1500);
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
            signup();
        });
    }
}

window.addEventListener('DOMContentLoaded', () => {
    setupSignupButton();
});