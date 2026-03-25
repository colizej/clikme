/* EasyMDE initialization for Django admin */
document.addEventListener('DOMContentLoaded', function () {
  var el = document.querySelector('.easymde-field');
  if (!el || typeof EasyMDE === 'undefined') return;

  new EasyMDE({
    element: el,
    spellChecker: false,
    autosave: {
      enabled: true,
      uniqueId: 'article-content-md',
      delay: 3000,
    },
    toolbar: [
      'bold', 'italic', 'heading', '|',
      'quote', 'unordered-list', 'ordered-list', '|',
      'link', 'image', 'table', '|',
      'preview', 'side-by-side', 'fullscreen', '|',
      'guide',
    ],
    minHeight: '500px',
    renderingConfig: {
      singleLineBreaks: false,
    },
    status: ['autosave', 'lines', 'words'],
  });
});
