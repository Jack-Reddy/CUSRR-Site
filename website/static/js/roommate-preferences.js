async function roommatePreferenceErrorMessage(response) {
  const data = await response.json().catch(() => ({}));
  return data.error || data.reason || `Save failed with status ${response.status}`;
}

function roommatePreferenceMatchSummary(entries) {
  const unmatched = (entries || []).filter((entry) => entry && entry.matched === false);
  if (!unmatched.length) {
    return 'Roommate preferences saved.';
  }

  const names = unmatched
    .map((entry) => entry.preferred_email)
    .filter(Boolean)
    .join(', ');

  return names
    ? `Roommate preferences saved, but no matching user was found for: ${names}`
    : 'Roommate preferences saved, but one or more entries did not match an existing user.';
}

async function saveRoommatePreferencesWithPopup(event) {
  if (event) {
    event.preventDefault();
    event.stopImmediatePropagation();
  }

  const textarea = document.getElementById('roommate-preferences');
  const messageDiv = document.getElementById('roommate-preferences-message');
  if (!textarea) return;

  try {
    const response = await fetch('/api/v1/users/roommate-preferences', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ preferences: textarea.value.trim() })
    });

    if (!response.ok) {
      throw new Error(await roommatePreferenceErrorMessage(response));
    }

    const data = await response.json().catch(() => ({}));
    const message = roommatePreferenceMatchSummary(data.preference_entries);

    if (messageDiv) {
      messageDiv.className = message.includes('no matching user')
        ? 'small mt-2 text-warning'
        : 'small mt-2 text-success';
      messageDiv.textContent = message;
    }

    alert(message);
  } catch (error) {
    console.error('Error saving roommate preferences:', error);
    const message = error.message || 'Could not save roommate preferences.';

    if (messageDiv) {
      messageDiv.className = 'small mt-2 text-danger';
      messageDiv.textContent = message;
    }

    alert(message);
  }
}

window.addEventListener('DOMContentLoaded', () => {
  const roommateBtn = document.getElementById('roommate-preferences-submit');
  if (roommateBtn) {
    roommateBtn.addEventListener('click', saveRoommatePreferencesWithPopup, true);
  }
});
