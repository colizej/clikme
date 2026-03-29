/* EasyMDE initialization for Django admin */
document.addEventListener('DOMContentLoaded', function () {
  var el = document.querySelector('.easymde-field');
  if (!el || typeof EasyMDE === 'undefined') return;

  // Remove the old shared autosave key (one-time migration)
  localStorage.removeItem('smde_article-content-md');

  var editor = new EasyMDE({
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

  // Inject CSS into preview iframe
  var css = `
    h1, h2, h3, h4, h5, h6 { font-weight: 700 !important; }
    h1 { font-size: 1rem !important; }
    h2 { font-size: 0.95rem !important; }
    h3 { font-size: 0.9rem !important; }
    h4, h5, h6 { font-size: 0.85rem !important; }
  `;

  function injectCSS() {
    var iframe = document.querySelector('.editor-preview-active iframe');
    if (iframe && iframe.contentDocument) {
      var style = iframe.contentDocument.createElement('style');
      style.textContent = css;
      iframe.contentDocument.head.appendChild(style);
    }
  }

  // Try immediately and on preview toggle
  setTimeout(injectCSS, 500);
  editor.toolbarElements['preview']?.addEventListener('click', function() {
    setTimeout(injectCSS, 100);
  });
});
