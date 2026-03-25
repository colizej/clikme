/* EasyMDE initialization for Django admin */
document.addEventListener('DOMContentLoaded', function () {
  var el = document.querySelector('.easymde-field');
  if (!el || typeof EasyMDE === 'undefined') return;

  // Remove the old shared autosave key (one-time migration)
  localStorage.removeItem('smde_article-content-md');

  new EasyMDE({
    element: el,
    spellChecker: false,
    autosave: {
      enabled: true,
      uniqueId: 'easymde-' + window.location.pathname,
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
