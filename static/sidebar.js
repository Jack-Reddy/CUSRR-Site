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

// --- Auth UI updater: fetch /me and populate the sidebar auth area -------------
(async function(){
  async function updateAuthUI(){
    try {
      const resp = await fetch('/me', { credentials: 'same-origin' });
      const loginBtn = document.getElementById('login-btn');
      const logoutBtn = document.getElementById('logout-btn');
      const userName = document.getElementById('user-name');
      const userPic = document.getElementById('user-pic');

      if (!resp.ok) {
        if (loginBtn) loginBtn.style.display = '';
        if (logoutBtn) logoutBtn.style.display = 'none';
        if (userName) userName.textContent = '';
        if (userPic) { userPic.style.display = 'none'; userPic.src = ''; }
        return;
      }

      const data = await resp.json();
      if (data && data.authenticated) {
        if (loginBtn) loginBtn.style.display = 'none';
        if (logoutBtn) logoutBtn.style.display = '';
        if (userName) userName.textContent = data.name || data.email || '';
        if (userPic) {
          if (data.picture) { userPic.src = data.picture; userPic.style.display = ''; }
          else { userPic.style.display = 'none'; userPic.src = ''; }
        }
      } else {
        if (loginBtn) loginBtn.style.display = '';
        if (logoutBtn) logoutBtn.style.display = 'none';
      }
    } catch (e) {
      console.error('sidebar auth helper error', e);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', updateAuthUI);
  } else {
    updateAuthUI();
  }

})();
//  Auth Stuff

(async function () {
  try {
    const loginBtn  = document.getElementById('login-btn');
    const logoutBtn = document.getElementById('logout-btn');
    const profileBtn = document.querySelector('.btn.btn-outline-secondary.mb-4.nav-link.card');

    const resp = await fetch('/me', { credentials: 'same-origin' });

    // If not authenticated
    if (!resp.ok) {
      loginBtn.style.display = '';
      if (logoutBtn) logoutBtn.style.display = 'none';
      if (profileBtn) profileBtn.remove();  // 👈 remove the entire profile button
      return;
    }

    const data = await resp.json();
    if (data && data.authenticated) {
      // Hide login, show logout
      loginBtn.style.display = 'none';
      if (logoutBtn) logoutBtn.style.display = '';

      // Recreate or fill the profile button
      let btn = profileBtn;
      if (!btn) {
        // If we removed it earlier, rebuild it
        const div = document.createElement('a');
        div.href = '#profile';
        div.className = 'btn btn-outline-secondary mb-4 nav-link card text-center border';
        div.innerHTML = `
          <img id="user-pic" alt="User avatar" width="35" height="35">
          <span id="user-name" class="text-uppercase label"></span>
        `;
        loginBtn.insertAdjacentElement('afterend', div);
        btn = div;
      }

      // Populate data
      const userPic = btn.querySelector('#user-pic');
      const userName = btn.querySelector('#user-name');

      if (data.picture) {
        userPic.src = data.picture;
        userPic.style.display = '';
      } else {
        userPic.style.display = 'none';
        userPic.src = '';
      }

      if (data.name || data.email) {
        userName.textContent = data.name || data.email;
        userName.style.display = '';
      } else {
        userName.remove();
      }
    } else {
      // Not authenticated
      loginBtn.style.display = '';
      if (logoutBtn) logoutBtn.style.display = 'none';
      if (profileBtn) profileBtn.remove(); // 👈 remove when not logged in
    }
  } catch (err) {
    console.error('auth helper error', err);
    const loginBtn  = document.getElementById('login-btn');
    const logoutBtn = document.getElementById('logout-btn');
    const profileBtn = document.querySelector('.btn.btn-outline-secondary.mb-4.nav-link.card');

    loginBtn.style.display = '';
    if (logoutBtn) logoutBtn.style.display = 'none';
    if (profileBtn) profileBtn.remove(); // 👈 remove on error too
  }
})();

