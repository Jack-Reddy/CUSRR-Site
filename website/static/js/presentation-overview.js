/**
 * Presentation Overview Page
 * Handles loading presentations and navigation between them.
 */

(function () {
  let allPresentations = [];
  let currentIndex = 0;

  function setCounter(text) {
    const counter = document.getElementById('presentation-counter');
    if (counter) {
      counter.textContent = text;
    }
  }

  /**
   * Fetch all presentations from the API.
   */
  async function loadPresentations() {
    try {
      const response = await fetch('/overview/all');
      if (!response.ok) {
        console.error('Failed to fetch presentations:', response.statusText);
        setCounter('Load failed');
        showError('Could not load presentations.');
        return;
      }
      allPresentations = await response.json();
      if (allPresentations.length > 0) {
        currentIndex = 0;
        renderPresentation();
      } else {
        setCounter('0 / 0');
        showError('No presentations found.');
      }
    } catch (error) {
      console.error('Error loading presentations:', error);
      setCounter('Load failed');
      showError('Could not load presentations.');
    }
  }

  /**
   * Render the current presentation.
   */
  async function renderPresentation() {
    if (allPresentations.length === 0) {
      return;
    }

    const pres = allPresentations[currentIndex];

    try {
      const response = await fetch(`/overview/${pres.id}`);
      if (!response.ok) {
        console.error('Failed to fetch presentation detail:', response.statusText);
        setCounter('Load failed');
        showError('Could not load this presentation.');
        return;
      }
      const detail = await response.json();

      // Update counter
      setCounter(`${currentIndex + 1} / ${allPresentations.length}`);

      // Update cards
      document.getElementById('session-id').textContent = detail.id;
      document.getElementById('presentation-title').textContent = detail.title || '-';

      // Authors
      if (detail.presenters && detail.presenters.length > 0) {
        document.getElementById('presentation-authors').textContent =
          detail.presenters.map((p) => p.name || p.email).join(', ');
      } else {
        document.getElementById('presentation-authors').textContent = '-';
      }

      // Department (from first presenter)
      if (detail.presenters && detail.presenters.length > 0 && detail.presenters[0].department) {
        document.getElementById('presentation-department').textContent =
          detail.presenters[0].department;
      } else {
        document.getElementById('presentation-department').textContent = '-';
      }

      // Abstract (render markdown if available)
      const abstractElement = document.getElementById('presentation-abstract');
      if (detail.abstract) {
        if (window.AbstractMarkdownEditor && typeof window.AbstractMarkdownEditor.renderToElement === 'function') {
          window.AbstractMarkdownEditor.renderToElement(abstractElement, detail.abstract);
        } else {
          abstractElement.textContent = detail.abstract;
        }
      } else {
        abstractElement.textContent = '-';
      }

      // Update button states
      document.getElementById('prev-btn').disabled = currentIndex === 0;
      document.getElementById('next-btn').disabled = currentIndex === allPresentations.length - 1;
    } catch (error) {
      console.error('Error rendering presentation:', error);
      setCounter('Load failed');
      showError('Could not render presentation.');
    }
  }

  /**
   * Show error message.
   */
  function showError(message) {
    const container = document.getElementById('presentation-container');
    if (container) {
      container.innerHTML = `<div class="alert alert-danger">${message}</div>`;
    }
  }

  /**
   * Navigate to previous presentation.
   */
  function previousPresentation() {
    if (currentIndex > 0) {
      currentIndex--;
      renderPresentation();
    }
  }

  /**
   * Navigate to next presentation.
   */
  function nextPresentation() {
    if (currentIndex < allPresentations.length - 1) {
      currentIndex++;
      renderPresentation();
    }
  }

  /**
   * Initialize the page.
   */
  function init() {
    const prevBtn = document.getElementById('prev-btn');
    const nextBtn = document.getElementById('next-btn');

    if (prevBtn) {
      prevBtn.addEventListener('click', previousPresentation);
    }

    if (nextBtn) {
      nextBtn.addEventListener('click', nextPresentation);
    }

    loadPresentations();
  }

  // Start on DOMContentLoaded
  window.addEventListener('DOMContentLoaded', init);
})();
