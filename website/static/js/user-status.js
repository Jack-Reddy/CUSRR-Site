let userTable; // store DataTable instance
let allUsers = []; // keep raw data for clipboard actions

async function apiErrorMessage(response, fallback) {
  const data = await response.json().catch(() => ({}));
  return data.error || data.reason || fallback;
}

function yesNoBadge(isSubmitted) {
  return isSubmitted
    ? '<span class="badge bg-success">Yes</span>'
    : '<span class="badge bg-warning text-dark">No</span>';
}

function isPresenterLike(user) {
  return Boolean(user && user.presentation_id);
}

function userRoles(user) {
  return String(user && user.auth ? user.auth : '')
    .split(',')
    .map((role) => role.trim().toLowerCase())
    .filter(Boolean);
}

function isEmailFilterCandidate(user) {
  return Boolean(user && user.email && (user.presentation_id || userRoles(user).includes('presenter')));
}

function normalizedValue(value) {
  return String(value || '').trim().toLowerCase();
}

function selectedValue(id, fallback = 'all') {
  const element = document.getElementById(id);
  return element ? element.value : fallback;
}

function matchesPresentationTypeFilter(user, selectedType) {
  if (selectedType === 'all') return true;
  return normalizedValue(user.presentation_type) === normalizedValue(selectedType);
}

function matchesActivityFilter(user, selectedActivity) {
  if (selectedActivity === 'all') return true;
  return normalizedValue(user.activity) === normalizedValue(selectedActivity);
}

function matchesCompletionStatusFilter(user, selectedStatus) {
  const abstractSubmitted = Boolean(user.abstract_submitted);
  const presentationUploaded = Boolean(user.presentation_uploaded);

  if (selectedStatus === 'abstract_only') {
    return abstractSubmitted && !presentationUploaded;
  }
  if (selectedStatus === 'presentation_only') {
    return presentationUploaded && !abstractSubmitted;
  }
  if (selectedStatus === 'both') {
    return abstractSubmitted && presentationUploaded;
  }
  if (selectedStatus === 'neither') {
    return !abstractSubmitted && !presentationUploaded;
  }
  return false;
}

function filteredEmailRows() {
  const rows = userTable ? userTable.data().toArray() : allUsers;
  const selectedType = selectedValue('copyEmailPresentationType');
  const selectedStatus = selectedValue('copyEmailCompletionStatus', 'neither');
  const selectedActivity = selectedValue('copyEmailActivity');

  return rows.filter((user) => (
    isEmailFilterCandidate(user)
    && matchesPresentationTypeFilter(user, selectedType)
    && matchesCompletionStatusFilter(user, selectedStatus)
    && matchesActivityFilter(user, selectedActivity)
  ));
}

async function writeToClipboard(text) {
  if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(text);
    return;
  }

  const temp = document.createElement('textarea');
  temp.value = text;
  temp.style.position = 'fixed';
  temp.style.left = '-9999px';
  document.body.appendChild(temp);
  temp.select();
  document.execCommand('copy');
  document.body.removeChild(temp);
}

async function copyFilteredEmails() {
  const matchingRows = filteredEmailRows();
  const emails = [...new Set(matchingRows.map((user) => user.email).filter(Boolean))];

  if (!emails.length) {
    alert('No matching emails to copy.');
    return;
  }

  try {
    await writeToClipboard(emails.join(', '));
    alert(`Copied ${emails.length} email${emails.length === 1 ? '' : 's'}. Paste into Gmail To/CC/BCC.`);
  } catch (err) {
    console.error('Copy failed', err);
    alert('Could not copy emails.');
  }
}

async function loadUsers() {
  const container = document.getElementById('user-container');
  if (!container) {
    console.error('User container not found!');
    return;
  }

  try {
    const response = await fetch('/api/v1/users/');
    if (!response.ok) {
      throw new Error(await apiErrorMessage(response, `Network response was not ok: ${response.status} ${response.statusText}`));
    }

    const users = await response.json();
    allUsers = users;

    renderTable(users);

  } catch (err) {
    console.error('Failed to load users', err);
    container.innerHTML = `<p class="text-danger">Could not load users: ${err.message}</p>`;
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
            <th>Presentation Type</th>
            <th>Abstract Submitted</th>
            <th>Presentation Uploaded</th>
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
      {
        data: 'presentation_type',
        render: function (data, type, row) {
          if (!isPresenterLike(row)) return '—';
          return data || '—';
        }
      },
      {
        data: 'abstract_submitted',
        render: function (data, type, row) {
          if (type !== 'display') return data ? 'Yes' : 'No';
          if (!isPresenterLike(row)) return '—';
          return yesNoBadge(Boolean(data));
        }
      },
      {
        data: 'presentation_uploaded',
        render: function (data, type, row) {
          if (type !== 'display') return data ? 'Yes' : 'No';
          if (!isPresenterLike(row)) return '—';
          return yesNoBadge(Boolean(data));
        }
      },
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
    order: [[1, 'asc']], // default sort by Email
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
      throw new Error(await apiErrorMessage(response, `Could not delete user: ${response.status}`));
    }

    await loadUsers(); // Refresh the user list
  } catch (err) {
    console.error('Failed to delete user', err);
    alert(err.message || 'Could not delete user.');
  }
}

//Edit User Function
async function editUser(userId) {
  try {

    const response = await fetch(`/api/v1/users/${userId}`, {
      method: 'GET',
    });
    if (!response.ok) throw new Error(await apiErrorMessage(response, `Could not load user details: ${response.status}`));
    const user = await response.json();

    // Fill and show modal
    EditModal.fillAndShowModal(user);

    // Handle form submission (set up once)
    EditModal.setupFormSubmit(async (data) => {
      const presentationType = data.presentation_type;
      delete data.presentation_type;

      const updateResp = await fetch(`/api/v1/users/${userId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });

      if (!updateResp.ok) {
        throw new Error(await apiErrorMessage(updateResp, `Failed to update user: ${updateResp.status}`));
      }

      if (user.presentation_id && typeof presentationType !== 'undefined') {
        const presentationResp = await fetch(`/api/v1/presentations/${user.presentation_id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ type: presentationType }),
        });

        if (!presentationResp.ok) {
          throw new Error(await apiErrorMessage(presentationResp, `Failed to update presentation type: ${presentationResp.status}`));
        }
      }

      await loadUsers(); // refresh after save
    });

  } catch (err) {
    console.error('Failed to edit user', err);
    alert(err.message || 'Could not load user details.');
  }
}

// Initialize after DOM ready
document.addEventListener('DOMContentLoaded', () => {
  loadUsers();

  const copyFilteredBtn = document.getElementById('copy-filtered-emails-btn');
  if (copyFilteredBtn) {
    copyFilteredBtn.addEventListener('click', copyFilteredEmails);
  }
});