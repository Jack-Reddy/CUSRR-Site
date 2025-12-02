async function signup(e) {
    e.preventDefault(); // Prevent default form submit behavior

    const div = document.getElementById('signup-flash');
    if (!div) {
        console.error('Flash container not found!');
        return;
    }

    const flash = (msg, cls = 'text-danger') => {
        div.innerHTML = `<p class="${cls}">${msg}</p>`;
        div.style.opacity = 1;
        setTimeout(() => (div.style.opacity = 0), 3000); // Fade-out effect
    };

    try {
        // Fetch authenticated user info
        const meResponse = await fetch('/me');
        if (!meResponse.ok) throw new Error(`Failed to get user info`);

        const user = await meResponse.json();
        if (!user.authenticated) {
            flash('You must be signed in to Google to register for CUSRR.');
            return;
        }

        const firstName = document.getElementById('first-name')?.value.trim();
        const lastName  = document.getElementById('last-name')?.value.trim();
        const activitySelect = document.getElementById('activity');

        // Validate fields
        if (!firstName || !lastName) {
            flash('Please enter both first and last names.');
            return;
        }

        if (!activitySelect || activitySelect.selectedIndex === 0) {
            flash('Please select an activity.');
            return;
        }

        const selectedActivity = activitySelect.options[activitySelect.selectedIndex].text;

        // Send signup request
        const response = await fetch('/api/v1/users/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                firstname: firstName,
                lastname: lastName,
                activity: selectedActivity,
                email: user.email
            })
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            flash(errorData.error || 'Signup failed.');
            return;
        }

        const result = await response.json();
        flash(`Signup successful! Welcome, ${result.name}.`, 'text-success');

        setTimeout(() => {
            window.location.href = `/profile`;
        }, 1500);
    } catch (error) {
        console.error('Error during signup:', error);
        flash('Signup failed. Please try again later.');
    }
}

function setupSignupButton() {
    const btn = document.getElementById('signup-submit');
    console.log('Signup button found:', btn);
    if (btn) btn.addEventListener('click', signup);
}

window.addEventListener('DOMContentLoaded', setupSignupButton);
