new Sortable(document.getElementById('sortable-grid'), {
    animation: 150,
    ghostClass: 'sortable-ghost',
    handle: '.card', // draggable element is the card itself
    draggable: '.col-4' // sortable item is the column
  });