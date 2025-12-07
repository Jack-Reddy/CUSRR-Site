// static/js/sidebar.js

document.addEventListener('DOMContentLoaded', () => {
  const STORAGE_KEY = 'cusrr_sidebar_mini';
  const root = document.documentElement;        // <html>
  const sidebar = document.getElementById('sidenav-main');
  const toggleBtns = document.querySelectorAll('[data-sidebar-toggle]');
  const backdrop = document.getElementById('sidebar-backdrop');

  if (!sidebar || !toggleBtns.length) return;

  const isMobile = () => window.matchMedia('(max-width: 768px)').matches;

  // ----- DESKTOP (mini vs full) -----
  const applyDesktopMini = (isMini) => {
    root.classList.toggle('sidebar-mini', isMini);
    toggleBtns.forEach(btn => {
      btn.setAttribute('aria-expanded', String(!isMini));
    });
  };

  // ----- MOBILE (drawer open vs closed) -----
  const openMobile = () => {
    sidebar.classList.add('open');
    backdrop && backdrop.classList.add('show');
  };
  
  const closeMobile = () => {
    sidebar.classList.remove('open');
    backdrop && backdrop.classList.remove('show');
  };
  

  const toggle = () => {
    if (isMobile()) {
      // Mobile: open/close drawer
      if (sidebar.classList.contains('open')) {
        closeMobile();
      } else {
        openMobile();
      }
    } else {
      // Desktop: mini/full
      const willBeMini = !root.classList.contains('sidebar-mini');
      applyDesktopMini(willBeMini);
      try {
        localStorage.setItem(STORAGE_KEY, String(willBeMini));
      } catch (e) {
        // ignore storage errors
      }
    }
  };

  // Attach to all toggle buttons (sidebar toggle + optional navbar toggle)
  toggleBtns.forEach(btn => btn.addEventListener('click', (e) => {
    e.preventDefault();
    toggle();
  }));

  // Close when backdrop is clicked
  if (backdrop) {
    backdrop.addEventListener('click', closeMobile);
  }

  // ----- INITIAL STATE -----
  const savedMini = (() => {
    try {
      return localStorage.getItem(STORAGE_KEY) === 'true';
    } catch (e) {
      return false;
    }
  })();

  if (isMobile()) {
    // Sidebar should start closed on mobile
    closeMobile();
    root.classList.remove('sidebar-mini');
  } else {
    const initialIsMini =
      root.classList.contains('sidebar-mini') || savedMini;
    applyDesktopMini(initialIsMini);
  }
  
  
  // ----- HANDLE RESIZE -----
  window.addEventListener('resize', () => {
    if (isMobile()) {
      // moving into mobile mode
      root.classList.remove('sidebar-mini');
      applyDesktopMini(false);
      closeMobile();
    } else {
      // moving into desktop mode
      sidebar.classList.remove('open');
      backdrop && backdrop.classList.remove('show');
      const mini = (() => {
        try {
          return localStorage.getItem(STORAGE_KEY) === 'true';
        } catch (e) {
          return false;
        }
      })();
      applyDesktopMini(mini);
    }
  });

  // Optional: keep your keyboard shortcut for desktop mini toggle
  window.addEventListener('keydown', (e) => {
    const isMac = navigator.platform.toUpperCase().includes('MAC');
    if ((isMac ? e.metaKey : e.ctrlKey) && e.key === '\\') {
      e.preventDefault();
      if (!isMobile()) {
        const willBeMini = !root.classList.contains('sidebar-mini');
        applyDesktopMini(willBeMini);
        try {
          localStorage.setItem(STORAGE_KEY, String(willBeMini));
        } catch (err) {}
      } else {
        // On mobile, same shortcut just opens/closes the drawer
        toggle();
      }
    }
  });
});
