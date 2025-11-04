async function loadUsers() {
  const container = document.getElementById('user-container');
  
  if (!container) {
    console.error('User container not found!');
    return;
  }

  try {
    const response = await fetch('/routes/users/');

    if (!response.ok) {
      throw new Error(`Network response was not ok: ${response.status} ${response.statusText}`);
    }

    const users = await response.json();

    if (!users || users.length === 0) {
      console.log('No users found.');
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
              <li><a class="dropdown-item" href="#">View</a></li>
              <li><a class="dropdown-item" href="#">Edit</a></li>
              <li><hr class="dropdown-divider"></li>
              <li><a class="dropdown-item text-danger" href="#">Delete</a></li>
            </ul>
          </div>
        </td>
      `;

      tbody.appendChild(row);
    });

    // Add table to container
    container.appendChild(table);

    console.log(`Loaded ${users.length} total users.`);

  } catch (err) {
    console.error('Failed to load users', err);
    container.innerHTML = '<p class="text-danger">Could not load users.</p>';
  }
}

// Run after DOM is ready
document.addEventListener('DOMContentLoaded', loadUsers);
