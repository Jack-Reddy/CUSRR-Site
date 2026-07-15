(function () {
  const DEFAULT_PAGE_LENGTH = 150;
  const TABLE_SELECTORS = ['#user-table', '#presentation-table', '#grades-table'];
  const TABLE_ENDPOINTS = {
    '/api/v1/users/': '/api/v1/users/table',
    '/api/v1/users': '/api/v1/users/table',
    '/api/v1/presentations/': '/api/v1/presentations/table',
    '/api/v1/presentations': '/api/v1/presentations/table',
  };

  function requestMethod(input, init) {
    return String((init && init.method) || (input && input.method) || 'GET').toUpperCase();
  }

  function requestPath(input) {
    const url = typeof input === 'string' ? input : input && input.url;
    if (!url) return '';
    try {
      return new URL(url, window.location.origin).pathname;
    } catch (error) {
      return url;
    }
  }

  function installFetchRewrites() {
    if (window.__cusrrTableFetchRewritesInstalled || !window.fetch) return;

    const originalFetch = window.fetch.bind(window);
    window.fetch = function patchedFetch(input, init) {
      if (requestMethod(input, init) !== 'GET') {
        return originalFetch(input, init);
      }

      const replacementUrl = TABLE_ENDPOINTS[requestPath(input)];
      if (!replacementUrl) {
        return originalFetch(input, init);
      }

      if (typeof input === 'string') {
        return originalFetch(replacementUrl, init);
      }

      return originalFetch(new Request(replacementUrl, input), init);
    };

    window.__cusrrTableFetchRewritesInstalled = true;
  }

  function configureDataTableDefaults() {
    if (!window.DataTable) return;
    window.DataTable.defaults = window.DataTable.defaults || {};
    window.DataTable.defaults.deferRender = true;
  }

  function ensureLengthOption(tableEl) {
    const container = tableEl && tableEl.closest('.dt-container');
    const select = container && container.querySelector('.dt-length select');
    if (!select) return;

    const hasOption = Array.from(select.options).some((option) => Number(option.value) === DEFAULT_PAGE_LENGTH);
    if (!hasOption) {
      select.add(new Option(String(DEFAULT_PAGE_LENGTH), String(DEFAULT_PAGE_LENGTH)));
    }
    select.value = String(DEFAULT_PAGE_LENGTH);
  }

  function setTableLength(selector) {
    if (!window.DataTable || !window.DataTable.isDataTable || !window.DataTable.isDataTable(selector)) {
      return;
    }

    const tableEl = document.querySelector(selector);
    if (!tableEl) return;

    const table = new window.DataTable(selector);
    if (table.page && table.page.len() !== DEFAULT_PAGE_LENGTH) {
      table.page.len(DEFAULT_PAGE_LENGTH).draw(false);
    }

    ensureLengthOption(tableEl);
  }

  function applyDefaultPageLength() {
    TABLE_SELECTORS.forEach(setTableLength);
  }

  installFetchRewrites();
  configureDataTableDefaults();

  document.addEventListener('DOMContentLoaded', () => {
    configureDataTableDefaults();
    applyDefaultPageLength();

    ['user-container', 'presentation-container', 'grades-container']
      .map((id) => document.getElementById(id))
      .filter(Boolean)
      .forEach((container) => {
        const observer = new MutationObserver(applyDefaultPageLength);
        observer.observe(container, { childList: true, subtree: true });
      });

    setTimeout(applyDefaultPageLength, 250);
    setTimeout(applyDefaultPageLength, 1000);
  });
})();
