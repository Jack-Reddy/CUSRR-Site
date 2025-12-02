let userTable; // store DataTable instance

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
    allUsers = users; // keep for reference (optional)

    renderTable(users);

  } catch (err) {
    console.error('Failed to load users', err);
    container.innerHTML = '<p class="text-danger">Could not load users.</p>';
  }
}

function renderTable(users) {
  const container = document.getElementById('user-container');
  if (!container) return;

  container.innerHTML = `
    <div class="table-responsive">
      <table id="user-table" class="table table-hover table-bordered align-middle mb-0" style="width:100%">
        <thead class="table table-striped align-middle">
          <tr>
            <th>Name</th>
            <th>Email</th>
            <th>Activity</th>
            <th>Pres. ID</th>
            <th>Status</th>
            <th>Role</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody></tbody>
      </table>
    </div>
  `;

  // Destroy previous DataTable instance if it exists
  if (userTable) {
    userTable.destroy();
  }

  // Initialize DataTable
  userTable = new DataTable('#user-table', {
    data: users,
    columns: [
      { data: 'name', defaultContent: '—' },
      { data: 'email', defaultContent: '—' },
      { data: 'activity', defaultContent: '—' },
      { data: 'presentation_id', defaultContent: '—' },
      { data: 'status', defaultContent: '—' },
      { data: 'auth', defaultContent: '—' },
      {
        data: 'id',
        orderable: false,
        searchable: false,
        render: function (data, type, row) {
          return `
            <div class="dropdown">
              <button class="btn btn-sm btn-outline-secondary dropdown-toggle" type="button" data-bs-toggle="dropdown" aria-expanded="false">
                Options
              </button>
              <ul class="dropdown-menu">
                <li><a class="dropdown-item" href="#" onclick="editUser(${data})">Edit</a></li>
                <li><hr class="dropdown-divider"></li>
                <li><a class="dropdown-item text-danger" href="#" onclick="removeUser(${data})">Delete</a></li>
              </ul>
            </div>
          `;
        }
      }
    ],  
    responsive: true,
    pageLength: 10,
    order: [[1, 'asc']], // default sort by Name
  });
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

    await loadUsers(); // Refresh the user list
  
  } catch (err) {
    console.error('Failed to delete user', err);
    alert('Could not delete user.');
  }
}

//Edit User Function
async function editUser(userId) {
  try {

    const response = await fetch(`/api/v1/users/${userId}`, {
      method: 'GET',
    });
    if (!response.ok) throw new Error(`Network response was not ok: ${response.status}`);
    const user = await response.json();

    // Fill and show modal
    EditModal.fillAndShowModal(user);

    // Handle form submission (set up once)
    EditModal.setupFormSubmit(async (data) => {
      const updateResp = await fetch(`/api/v1/users/${userId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });

      if (!updateResp.ok) throw new Error(`Failed to update user: ${updateResp.status}`);

      await loadUsers(); // refresh after save
    });

  } catch (err) {
    console.error('Failed to edit user', err);
    alert('Could not load user details.');
  }
}

// Initialize after DOM ready
document.addEventListener('DOMContentLoaded', () => {
  loadUsers();
});
