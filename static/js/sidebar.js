    const toggle = () => {
      document.body.classList.toggle('sidebar-mini');
      const expanded = !document.body.classList.contains('sidebar-mini');
      document.getElementById('toggleSidebar').setAttribute('aria-expanded', expanded);
    };
    document.getElementById('toggleSidebar').addEventListener('click', toggle);

    // Optional: keyboard shortcut (Ctrl/Cmd + \)
    window.addEventListener('keydown', (e) => {
      const isMac = navigator.platform.toUpperCase().includes('MAC');
      if ((isMac ? e.metaKey : e.ctrlKey) && e.key === '\\') {
        e.preventDefault(); toggle();
      }
    });
