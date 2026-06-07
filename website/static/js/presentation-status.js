let presentationTable;

async function loadPresentations() {
  const container = document.getElementById('presentation-container');
  if (!container) {
    console.error('Presentation container not found!');
    return;
  }

  try {
    const response = await fetch('/api/v1/presentations/');
    if (!response.ok) {
      throw new Error(`Network response was not ok: ${response.status} ${response.statusText}`);
    }

    const presentations = await response.json();
    window.allPresentations = presentations;

    renderPresentationTable(presentations);

  } catch (err) {
    console.error('Failed to load presentations', err);
    container.innerHTML = '<p class="text-danger">Could not load presentations.</p>';
  }
}

function renderPresentationTable(presentations) {
  const container = document.getElementById('presentation-container');
  if (!container) return;

  container.innerHTML = `
    <div class="table-responsive">
      <table id="presentation-table" class="table table-hover table-bordered align-middle mb-0" style="width:100%">
        <thead class="table table-striped align-middle">
          <tr>
            <th>Program ID</th>
            <th>Title</th>
            <th>Subject</th>
            <th>Type</th>
            <th>Schedule Block</th>
            <th>Time</th>
            <th>Presenters</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody></tbody>
      </table>
    </div>
  `;

  if (presentationTable) {
    presentationTable.destroy();
  }

  presentationTable = new DataTable('#presentation-table', {
    data: presentations,
    columns: [
      { data: 'program_identifier', defaultContent: '—' },
      { data: 'title', defaultContent: '—' },
      { data: 'subject', defaultContent: '—' },
      { data: 'type', defaultContent: '—' },
      { data: 'schedule_title', defaultContent: 'Unassigned' },
      { 
        data: 'time',
        defaultContent: '—',
        render: (data) => data ? new Date(data).toLocaleString() : '—'
      },
      { 
        data: 'presenters',
        defaultContent: '—',
        render: (presenters) => {
          if (!presenters || presenters.length === 0) return '—';
          return presenters.map(p => `${p.firstname} ${p.lastname}`).join(', ');
        }
      },
      {
        data: 'id',
        orderable: false,
        searchable: false,
        render: function (data) {
          return `
            <div class="dropdown">
              <button class="btn btn-sm btn-outline-secondary dropdown-toggle" type="button" data-bs-toggle="dropdown" aria-expanded="false">
                Options
              </button>
              <ul class="dropdown-menu">
                <li><a class="dropdown-item" href="#" onclick="editPresentation(${data})">Edit</a></li>
                <li><hr class="dropdown-divider"></li>
                <li><a class="dropdown-item text-danger" href="#" onclick="removePresentation(${data})">Delete</a></li>
              </ul>
            </div>
          `;
        }
      }
    ],
    responsive: true,
    pageLength: 10,
    order: [[0, 'asc']],
  });
}

removePresentation = async function (presentationId) {
  if (!confirm('Are you sure you want to delete this presentation? This action cannot be undone.')) {
    return;
  }

  try {
    const response = await fetch(`/api/v1/presentations/${presentationId}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      throw new Error(`Network response was not ok: ${response.status} ${response.statusText}`);
    }

    await loadPresentations();

  } catch (err) {
    console.error('Failed to delete presentation', err);
    alert('Could not delete presentation.');
  }
};

async function editPresentation(presentationId) {
  try {
    const response = await fetch(`/api/v1/presentations/${presentationId}`, {
      method: 'GET',
    });

    if (!response.ok) throw new Error(`Network response was not ok: ${response.status}`);

    const presentation = await response.json();

    await EditPresentationModal.fillAndShowModal(presentation);

    EditPresentationModal.setupFormSubmit(async (data) => {
      const updateResp = await fetch(`/api/v1/presentations/${presentationId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });

      if (!updateResp.ok) throw new Error(`Failed to update presentation: ${updateResp.status}`);

      await loadPresentations();
    });

  } catch (err) {
    console.error('Failed to edit presentation', err);
    alert('Could not load presentation details.');
  }
}

document.addEventListener('DOMContentLoaded', () => {
  loadPresentations();
});

document.getElementById("download-presentations")?.addEventListener("click", async () => {
  const btn = document.getElementById("download-presentations");
  let originalText = btn ? btn.innerHTML : '';
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Downloading...';
  }
  try {
    const response = await fetch("/api/v1/presentations/download-all");

    if (!response.ok) {
      throw new Error("Failed to download presentations");
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = "presentations.zip";
    document.body.appendChild(a);
    a.click();
    a.remove();

  } catch (err) {
    console.error(err);
    alert("Could not download presentations.");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = originalText || 'Download Presentations';
    }
  }
});
