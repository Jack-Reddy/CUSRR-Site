// Scores
const critInputs = document.querySelectorAll('.crit');
const totalEl = document.getElementById('scoreTotal');

function updateScores() {
  const o = +document.getElementById('scoreOrig').value;
  const c = +document.getElementById('scoreClar').value;
  const s = +document.getElementById('scoreSign').value;
  document.getElementById('scoreOrigVal').textContent = o;
  document.getElementById('scoreClarVal').textContent = c;
  document.getElementById('scoreSignVal').textContent = s;
  totalEl.textContent = o + c + s;
}

critInputs.forEach(i => i.addEventListener('input', updateScores));
updateScores();

// Save grade button
const saveBtn = document.getElementById('saveGradeBtn');
if (saveBtn) {
  saveBtn.addEventListener('click', async (e) => {
    e.preventDefault();

    const comment = document.querySelector('#gradeForm textarea').value;
    const criteria_1 = +document.getElementById('scoreOrig').value;
    const criteria_2 = +document.getElementById('scoreClar').value;
    const criteria_3 = +document.getElementById('scoreSign').value;

    // Get the presentation ID from a data attribute on the page
    const wrapper = document.getElementById('gradeFormWrapper');
    const presentationId = parseInt(wrapper.dataset.presentationId);
    const userId = parseInt(wrapper.dataset.userId);

    if (!presentationId) {
      alert("Presentation ID missing!");
      return;
    }

    try {
      const res = await fetch('/api/v1/abstractgrades', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
        presentation_id: presentationId,
        user_id: userId, 
        criteria_1,
        criteria_2,
        criteria_3,
        comment
      })
    });

      if (!res.ok) throw new Error('Failed to save grade');

      // Redirect back to Abstract Grader Dashboard
      window.location.href = '/abstract_grader';
    } catch (err) {
      console.error(err);
      alert("Error saving grade: " + err.message);
    }
  });
}
