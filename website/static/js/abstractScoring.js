// Scores
document.addEventListener('DOMContentLoaded', () => {
  const critInputs = document.querySelectorAll('.crit');
  const totalEl = document.getElementById('scoreTotal');
  const wrapper = document.getElementById('gradeFormWrapper');
  const saveBtn = document.getElementById('saveGradeBtn');
  const commentInput = document.querySelector('#gradeForm textarea');

  const abstractSource = document.getElementById('txt-source');
  const abstractTarget = document.getElementById('txt');
  if (window.AbstractMarkdownEditor && abstractSource && abstractTarget) {
    window.AbstractMarkdownEditor.initRenderedAbstract({
      sourceSelector: '#txt-source',
      targetSelector: '#txt',
    });
  }

  function updateScores() {
    const o = +document.getElementById('scoreOrig').value;
    const c = +document.getElementById('scoreClar').value;
    const s = +document.getElementById('scoreSign').value;
    document.getElementById('scoreOrigVal').textContent = o;
    document.getElementById('scoreClarVal').textContent = c;
    document.getElementById('scoreSignVal').textContent = s;
    totalEl.textContent = o + c + s;
  }

  function setInputValue(id, value) {
    const input = document.getElementById(id);
    if (!input || value === null || typeof value === 'undefined') return;
    input.value = value;
  }

  async function loadExistingGrade() {
    if (!wrapper) return;

    const presentationId = parseInt(wrapper.dataset.presentationId, 10);
    const userId = parseInt(wrapper.dataset.userId, 10);
    if (!presentationId || !userId) return;

    try {
      const response = await fetch(`/api/v1/abstractgrades/completed/${userId}/details`);
      if (!response.ok) return;

      const data = await response.json();
      const existingGrade = (data.grades || []).find((grade) => grade.presentation_id === presentationId);
      if (!existingGrade) return;

      setInputValue('scoreOrig', existingGrade.criteria_1);
      setInputValue('scoreClar', existingGrade.criteria_2);
      setInputValue('scoreSign', existingGrade.criteria_3);
      if (commentInput) {
        commentInput.value = existingGrade.comment || '';
      }
      if (saveBtn) {
        saveBtn.textContent = 'Update Grade';
      }
      updateScores();
    } catch (error) {
      console.warn('Could not load existing abstract grade for review.', error);
    }
  }

  critInputs.forEach((input) => input.addEventListener('input', updateScores));
  updateScores();
  loadExistingGrade();

  // Save grade button
  if (saveBtn) {
    saveBtn.addEventListener('click', async (e) => {
      e.preventDefault();

      const comment = commentInput ? commentInput.value : '';
      const criteria_1 = +document.getElementById('scoreOrig').value;
      const criteria_2 = +document.getElementById('scoreClar').value;
      const criteria_3 = +document.getElementById('scoreSign').value;

      // Get the presentation ID from a data attribute on the page
      const presentationId = parseInt(wrapper.dataset.presentationId, 10);
      const userId = parseInt(wrapper.dataset.userId, 10);

      if (!presentationId) {
        alert('Presentation ID missing!');
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
            comment,
          }),
        });

        if (!res.ok) throw new Error('Failed to save grade');

        // Redirect back to Abstract Grader Dashboard
        window.location.href = '/abstract-grader';
      } catch (err) {
        console.error(err);
        alert('Error saving grade: ' + err.message);
      }
    });
  }
});
