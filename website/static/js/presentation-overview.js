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

      setCounter(`${currentIndex + 1} / ${allPresentations.length}`);

      document.getElementById('session-id').textContent = detail.program_identifier || detail.id;
      document.getElementById('presentation-title').textContent = detail.title || '-';

      if (detail.presenters && detail.presenters.length > 0) {
        document.getElementById('presentation-authors').textContent =
          detail.presenters.map((p) => p.name || p.email).join(', ');
      } else {
        document.getElementById('presentation-authors').textContent = '-';
      }

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

      document.getElementById('prev-btn').disabled = currentIndex === 0;
      document.getElementById('next-btn').disabled = currentIndex === allPresentations.length - 1;
    } catch (error) {
      console.error('Error rendering presentation:', error);
      setCounter('Load failed');
      showError('Could not render presentation.');
    }
  }

  function showError(message) {
    const container = document.getElementById('presentation-container');
    if (container) {
      container.innerHTML = `<div class="alert alert-danger">${message}</div>`;
    }
  }

  function previousPresentation() {
    if (currentIndex > 0) {
      currentIndex--;
      renderPresentation();
    }
  }

  function nextPresentation() {
    if (currentIndex < allPresentations.length - 1) {
      currentIndex++;
      renderPresentation();
    }
  }

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

  window.addEventListener('DOMContentLoaded', init);
})();