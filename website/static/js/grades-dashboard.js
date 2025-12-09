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
    // Fetch both grades
    const [respGrades, respAbstract] = await Promise.all([
      fetch('/api/v1/grades/averages'),
      fetch('/api/v1/abstractgrades/averages')
    ]);

    if (!respGrades.ok) throw new Error('Failed to load grades');
    if (!respAbstract.ok) throw new Error('Failed to load abstract grades');

    const grades = await respGrades.json();
    const abstractGrades = await respAbstract.json();

    renderGradesTable(grades, abstractGrades);

  } catch (err) {
    console.error('Failed to load grades', err);
    container.innerHTML = `<p class="text-danger">Could not load grades.</p>`;
  }
}

function renderGradesTable(grades, abstractGrades) {
  const container = document.getElementById('grades-container');
  if (!container) return;

  container.innerHTML = `
    <div class="table-responsive">
      <table id="grades-table" class="table table-hover table-bordered align-middle mb-0">
        <thead class="table-light">
          <tr>
            <th>Presentation</th>
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

  // Merge data by presentation_id
  const merged = {};
  grades.forEach(g => {
    merged[g.presentation_id] = { ...g, avgAbstract: '—', numAbstract: 0 };
  });
  abstractGrades.forEach(ag => {
    if (merged[ag.presentation_id]) {
      merged[ag.presentation_id].avgAbstract = isNaN(Number(ag.average_score)) ? '—' : Number(ag.average_score).toFixed(2);
      merged[ag.presentation_id].numAbstract = ag.num_grades || 0;
    } else {
      merged[ag.presentation_id] = { 
        presentation_title: ag.presentation_title || '—',
        average_score: '—',
        num_grades: 0,
        avgAbstract: isNaN(Number(ag.average_score)) ? '—' : Number(ag.average_score).toFixed(2),
        numAbstract: ag.num_grades || 0
      };
    }
  });

  const data = Object.values(merged);

  if (gradesTable) gradesTable.destroy();

  gradesTable = new DataTable('#grades-table', {
    data: data,
    columns: [
      { data: 'presentation_title', defaultContent: '—' },
      { 
        data: 'average_score',
        render: data => {
          const score = Number(data);
          return isNaN(score) ? '—' : score.toFixed(2);
        }
      },
      { data: 'avgAbstract', defaultContent: '—' },
      { 
        data: 'num_grades',
        render: data => isNaN(Number(data)) ? '—' : data
      },
      { 
        data: 'numAbstract',
        render: data => isNaN(Number(data)) ? '—' : data
      }
    ],
    responsive: true,
    pageLength: 10,
    order: [[1, 'desc']], // sort by average grade
  });
}

document.addEventListener('DOMContentLoaded', () => {
  loadGrades();
});
