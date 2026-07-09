function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, (char) => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;',
    }[char]));
}

async function signup(e) {
    e.preventDefault();

    const div = document.getElementById('signup-flash');
    if (!div) {
        console.error('Flash container not found!');
        return;
    }

    const flash = (msg, cls = 'text-danger') => {
        div.innerHTML = `<p class="${cls}">${escapeHtml(msg)}</p>`;
        div.style.opacity = 1;
        setTimeout(() => (div.style.opacity = 0), 3000);
    };

    try {
        const meResponse = await fetch('/me');
        if (!meResponse.ok) throw new Error(`Failed to get user info`);

        const user = await meResponse.json();
        if (!user.authenticated) {
            flash('You must be signed in to Google to register for CUSRR.');
            return;
        }

        const firstName = document.getElementById('first-name')?.value.trim();
        const lastName  = document.getElementById('last-name')?.value.trim();
        const studentYearSelect = document.getElementById('student-year');
        const activitySelect = document.getElementById('activity');

        if (!firstName || !lastName) {
            flash('Please enter both first and last names.');
            return;
        }

        if (!studentYearSelect || !studentYearSelect.value) {
            flash('Please select your class year.');
            return;
        }

        if (!activitySelect || !activitySelect.value) {
            flash('Please select your attending/activity option.');
            return;
        }

        const selectedYear = studentYearSelect.value;
        const selectedActivity = activitySelect.value;

        const response = await fetch('/api/v1/users/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                firstname: firstName,
                lastname: lastName,
                student_year: selectedYear,
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