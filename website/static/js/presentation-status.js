let presentationTable;
let scheduleBlocks = [];
let subjectOptions = [];

const PRESENTATION_TYPES = ['Presentation', 'Blitz', 'Poster'];

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (char) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  }[char]));
}

function blockTimeLabel(block) {
  const start = block.start_time ? new Date(block.start_time) : null;
  if (!start || Number.isNaN(start.getTime())) return '';
  return start.toLocaleString([], { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
}

function blockLabel(block) {
  const parts = [block.day, block.title || 'Untitled'];
  if (block.type) parts.push(block.type);
  const time = blockTimeLabel(block);
  return `${parts.filter(Boolean).join(' - ')}${time ? ` (${time})` : ''}`;
}

function buildSubjectOptions(presentations) {
  const values = new Set(['']);
  presentations.forEach((presentation) => {
    const subject = (presentation.subject || '').trim();
    if (subject) values.add(subject);
  });
  return Array.from(values).sort((a, b) => {
    if (!a) return -1;
    if (!b) return 1;
    return a.localeCompare(b);
  });
}

function renderSelect(options, selectedValue, attrs = {}) {
  const selected = String(selectedValue ?? '');
  const attrString = Object.entries(attrs)
    .map(([key, value]) => `${key}="${escapeHtml(value)}"`)
    .join(' ');

  const htmlOptions = options.map((option) => {
    const value = String(option.value ?? '');
    const label = option.label ?? (value || 'Unassigned');
    return `<option value="${escapeHtml(value)}"${value === selected ? ' selected' : ''}>${escapeHtml(label)}</option>`;
  }).join('');

  return `<select class="form-select form-select-sm" ${attrString} data-original-value="${escapeHtml(selected)}">${htmlOptions}</select>`;
}

function subjectDropdown(row) {
  const options = subjectOptions.map((subject) => ({ value: subject, label: subject || 'Unassigned' }));
  return renderSelect(options, row.subject || '', {
    onchange: `updatePresentationInline(${row.id}, 'subject', this.value, this)`,
    'aria-label': 'Update subject',
  });
}

function typeDropdown(row) {
  const currentType = row.type || 'Presentation';
  const options = PRESENTATION_TYPES.map((type) => ({ value: type, label: type }));
  return renderSelect(options, currentType, {
    onchange: `updatePresentationInline(${row.id}, 'type', this.value, this)`,
    'aria-label': 'Update presentation type',
  });
}

function scheduleDropdown(row) {
  const options = [{ value: '', label: 'Unassigned' }].concat(
    scheduleBlocks.map((block) => ({ value: String(block.id), label: blockLabel(block) }))
  );
  return renderSelect(options, row.schedule_id || '', {
    onchange: `updatePresentationInline(${row.id}, 'schedule_id', this.value, this)`,
    'aria-label': 'Update schedule block',
  });
}

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Network response was not ok: ${response.status} ${response.statusText}`);
  }
  return response.json();
}

async function loadPresentations() {
  const container = document.getElementById('presentation-container');
  if (!container) {
    console.error('Presentation container not found!');
    return;
  }

  try {
    const [presentations, blocks] = await Promise.all([
      fetchJson('/api/v1/presentations/'),
      fetchJson('/api/v1/block-schedule/'),
    ]);

    scheduleBlocks = blocks.slice().sort((a, b) => {
      if (a.day !== b.day) return a.day.localeCompare(b.day);
      return new Date(a.start_time) - new Date(b.start_time);
    });
    subjectOptions = buildSubjectOptions(presentations);
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
            <th>Department</th>
            <th>Mentor</th>
            <th>Keywords</th>
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
      { data: 'program_identifier', defaultContent: '-' },
      { data: 'title', defaultContent: '-' },
      {
        data: 'subject',
        defaultContent: '-',
        render: (data, type, row) => type === 'display' ? subjectDropdown(row) : (data || '')
      },
      { data: 'department', defaultContent: '-' },
      { data: 'mentor', defaultContent: '-' },
      { data: 'keywords', defaultContent: '-' },
      {
        data: 'type',
        defaultContent: '-',
        render: (data, type, row) => type === 'display' ? typeDropdown(row) : (data || '')
      },
      {
        data: 'schedule_title',
        defaultContent: 'Unassigned',
        render: (data, type, row) => type === 'display' ? scheduleDropdown(row) : (data || 'Unassigned')
      },
      {
        data: 'time',
        defaultContent: '-',
        render: (data) => data ? new Date(data).toLocaleString() : '-'
      },
      {
        data: 'presenters',
        defaultContent: '-',
        render: (presenters) => {
          if (!presenters || presenters.length === 0) return '-';
          return presenters.map(p => `${escapeHtml(p.firstname)} ${escapeHtml(p.lastname)}`).join(', ');
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
                <li><a class="dropdown-item" href="#" onclick="editPresentation(${data})">Edit title/abstract</a></li>
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

window.updatePresentationInline = async function (presentationId, field, value, selectEl) {
  const originalValue = selectEl?.dataset?.originalValue ?? '';
  if (selectEl) selectEl.disabled = true;

  try {
    const response = await fetch(`/api/v1/presentations/${presentationId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ [field]: value }),
    });

    if (!response.ok) {
      throw new Error(`Failed to update presentation: ${response.status}`);
    }

    await loadPresentations();
  } catch (err) {
    console.error('Failed to update presentation field', err);
    if (selectEl) {
      selectEl.value = originalValue;
      selectEl.disabled = false;
    }
    alert('Could not save that presentation change.');
  }
};

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