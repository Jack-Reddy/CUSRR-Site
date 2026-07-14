let gradesTable;

async function loadGrades() {
  const container = document.getElementById('grades-container');
  if (!container) return;

  container.innerHTML = `
    <div class="text-center py-3 py-md-5 text-muted">
      <div class="spinner-border text-primary" role="status"></div>
      <p class="mt-3">Loading grades...</p>
    </div>
  `;

  try {
    const response = await fetch('/api/v1/grades/dashboard-summary');

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.error || data.reason || `Failed to load grades: ${response.status}`);
    }

    const summaryRows = await response.json();
    renderGradesTable(summaryRows);

  } catch (err) {
    console.error('Failed to load grades', err);
    container.innerHTML = `<p class="text-danger">Could not load grades: ${err.message}</p>`;
  }
}

function formatScore(value) {
  const score = Number(value);
  return Number.isNaN(score) ? '—' : score.toFixed(2);
}

function formatCount(value) {
  const count = Number(value);
  return Number.isNaN(count) ? '—' : count;
}

function renderGradesTable(rows) {
  const container = document.getElementById('grades-container');
  if (!container) return;

  container.innerHTML = `
    <div class="table-responsive">
      <table id="grades-table" class="table table-hover table-bordered align-middle mb-0">
        <thead class="table-light">
          <tr>
            <th>Presentation</th>
            <th>Presenters</th>
            <th>Average Grade</th>
            <th>Average Abstract Grade</th>
            <th>Number of Grades</th>
            <th>Number of Abstract Grades</th>
          </tr>
        </thead>
        <tbody></tbody>
      </table>
    </div>
  `;

  if (gradesTable) gradesTable.destroy();

  gradesTable = new DataTable('#grades-table', {
    data: rows,
    columns: [
      { data: 'presentation_title', defaultContent: '—' },
      { data: 'presenter_names', defaultContent: '—' },
      {
        data: 'average_score',
        render: formatScore,
      },
      {
        data: 'average_abstract_score',
        render: formatScore,
      },
      {
        data: 'num_grades',
        render: formatCount,
      },
      {
        data: 'num_abstract_grades',
        render: formatCount,
      }
    ],
    responsive: true,
    pageLength: 10,
    order: [[0, 'asc']],
  });
}

document.addEventListener('DOMContentLoaded', () => {
  loadGrades();
});