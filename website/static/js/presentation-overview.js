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

  function setText(id, value) {
    const element = document.getElementById(id);
    if (element) element.textContent = value || '-';
  }

  async function fetchJson(url) {
    const response = await fetch(url, { credentials: 'same-origin' });
    if (!response.ok) {
      const text = await response.text().catch(() => '');
      throw new Error(`${url} failed with ${response.status}: ${text || response.statusText}`);
    }
    return response.json();
  }

  async function loadPresentationList() {
    try {
      const rows = await fetchJson('/api/v1/presentations/table');
      return (rows || [])
        .filter((item) => item && item.id && item.show_on_schedule !== false)
        .sort((a, b) => {
          const aTime = a.time || '';
          const bTime = b.time || '';
          if (aTime !== bTime) return aTime.localeCompare(bTime);
          const aId = a.program_identifier || String(a.id);
          const bId = b.program_identifier || String(b.id);
          return aId.localeCompare(bId);
        });
    } catch (tableError) {
      console.warn('Lightweight program list failed; falling back to overview list.', tableError);
      return await fetchJson('/overview/all');
    }
  }

  async function loadPresentations() {
    try {
      allPresentations = await loadPresentationList();
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
      const response = await fetch(`/overview/${pres.id}`, { credentials: 'same-origin' });
      if (!response.ok) {
        const text = await response.text().catch(() => '');
        console.error('Failed to fetch presentation detail:', response.status, text || response.statusText);
        setCounter('Load failed');
        showError('Could not load this presentation.');
        return;
      }
      const detail = await response.json();

      setCounter(`${currentIndex + 1} / ${allPresentations.length}`);

      setText('session-id', detail.program_identifier || pres.program_identifier || detail.id || pres.id);
      setText('presentation-title', detail.title || pres.title);
      setText('presentation-department', detail.department || pres.department);
      setText('presentation-mentor', detail.mentor || pres.mentor);
      setText('presentation-keywords', detail.keywords || pres.keywords);

      const presenters = detail.presenters || pres.presenters || [];
      if (presenters.length > 0) {
        setText('presentation-authors', presenters.map((p) => p.name || p.email).join(', '));
      } else {
        setText('presentation-authors', '-');
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