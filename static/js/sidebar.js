// static/js/sidebar.js

document.addEventListener('DOMContentLoaded', () => {
  const STORAGE_KEY = 'cusrr_sidebar_mini';
  const root = document.documentElement; // <html>
  const toggleBtn = document.getElementById('toggleSidebar');
  if (!toggleBtn) return;

  // Apply a given mini/expanded state
  const applyState = (isMini) => {
    root.classList.toggle('sidebar-mini', isMini);
    toggleBtn.setAttribute('aria-expanded', String(!isMini));
  };

  // Initial state comes from the class already on <html>
  const initialIsMini = root.classList.contains('sidebar-mini');
  applyState(initialIsMini);

  const toggle = () => {
    const willBeMini = !root.classList.contains('sidebar-mini');
    applyState(willBeMini);
    try {
      localStorage.setItem(STORAGE_KEY, String(willBeMini));
    } catch (e) {
      // ignore storage errors
    }
  };

  toggleBtn.addEventListener('click', toggle);

  // Optional: keyboard shortcut (Ctrl/Cmd + \)
  window.addEventListener('keydown', (e) => {
    const isMac = navigator.platform.toUpperCase().includes('MAC');
    if ((isMac ? e.metaKey : e.ctrlKey) && e.key === '\\') {
      e.preventDefault();
      toggle();
    }
  });
});
