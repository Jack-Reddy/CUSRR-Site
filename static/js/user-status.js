async function loadUsers() {
  const container = document.getElementById('user-container');
  
  if (!container) {
    console.error('User container not found!');
    return;
  }

  try {
    const response = await fetch('/api/v1/users/');
    if (!response.ok) {
      throw new Error(`Network response was not ok: ${response.status} ${response.statusText}`);
    }

    const users = await response.json();
    allUsers = users; // save all users for filtering

    renderTable(users);

  } catch (err) {
    console.error('Failed to load users', err);
    container.innerHTML = '<p class="text-danger">Could not load users.</p>';
  }
}

function renderTable(users) {
  const container = document.getElementById('user-container');
  if (!container) return;

  if (!users || users.length === 0) {
    container.innerHTML = '<p class="text-secondary">No users.</p>';
    return;
  }

  // Clear container
  container.innerHTML = '';

  // Create table element
  const table = document.createElement('table');
  table.className = 'table table-hover align-middle mb-0';

  // Build table header
  table.innerHTML = `
    <thead class="table-light">
      <tr>
        <th>#</th>
        <th>Name</th>
        <th>Email</th>
        <th>Activity</th>
        <th>Pres. ID</th>
        <th>Status</th>
        <th>Actions</th>
      </tr>
    </thead>
    <tbody></tbody>
  `;

  const tbody = table.querySelector('tbody');

  // Add each user as a table row
  users.forEach((user, index) => {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td>${index + 1}</td>
      <td>${user.name || '—'}</td>
      <td>${user.email || '—'}</td>
      <td>${user.activity || '—'}</td>
      <td>${user.presentation_id || '—'}</td>
      <td>${user.status || '—'}</td>
      <td>
        <div class="dropdown">
          <button class="btn btn-sm btn-outline-secondary dropdown-toggle" type="button" data-bs-toggle="dropdown" aria-expanded="false">
            Options
          </button>
          <ul class="dropdown-menu">
            <li><a class="dropdown-item" onclick="viewPresentation(${user.id})">View Presentation</a></li>
            <li><a class="dropdown-item" onclick="editUser(${user.id})">Edit</a></li>
            <li><hr class="dropdown-divider"></li>
            <li><a class="dropdown-item text-danger" onclick="removeUser(${user.id})">Delete</a></li>
          </ul>
        </div>
      </td>
    `;
    tbody.appendChild(row);
  });

  container.appendChild(table);
}

removeUser = async function(userId) {
  if (!confirm('Are you sure you want to delete this user? This action cannot be undone.')) {
    return;
  }

  try {
    const response = await fetch(`/api/v1/users/${userId}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      throw new Error(`Network response was not ok: ${response.status} ${response.statusText}`);
    }
    loadUsers(); // Refresh the user list
  
  } catch (err) {
    console.error('Failed to delete user', err);
    alert('Could not delete user.');
  }
}

function setupFilter() {
  const filterInput = document.getElementById('user-filter');
  if (!filterInput) return;

  filterInput.addEventListener('input', (e) => {
    const query = e.target.value.toLowerCase().trim();

    const filtered = allUsers.filter(user =>
      (user.name && user.name.toLowerCase().includes(query)) ||
      (user.email && user.email.toLowerCase().includes(query))
    );

    renderTable(filtered);
  });
}
// Run after DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  loadUsers();
  setupFilter();
});