(function () {
  const DEFAULT_PAGE_LENGTH = 150;
  const TABLE_SELECTORS = ['#user-table', '#presentation-table', '#grades-table'];

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

  document.addEventListener('DOMContentLoaded', () => {
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
