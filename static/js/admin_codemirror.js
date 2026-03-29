/* CodeMirror initialization for Django admin */
document.addEventListener('DOMContentLoaded', function () {
  var el = document.querySelector('.codemirror-field');
  if (!el || typeof CodeMirror === 'undefined') return;

  // Hide the original textarea
  el.style.display = 'none';

  // Create wrapper div
  var wrapper = document.createElement('div');
  wrapper.style.cssText = 'border: 1px solid #ccc; border-radius: 4px; overflow: hidden;';
  el.parentNode.insertBefore(wrapper, el);
  wrapper.appendChild(el);

  // Initialize CodeMirror
  var editor = CodeMirror(wrapper, {
    value: el.value,
    mode: 'markdown',
    theme: 'eclipse',
    lineNumbers: true,
    lineWrapping: true,
    tabSize: 2,
    indentWithTabs: false,
    extraKeys: {
      'Ctrl-S': function(cm) {
        // Save form on Ctrl+S
        var form = cm.getWrapperElement().closest('form');
        if (form) {
          // Update textarea value before submit
          el.value = cm.getValue();
        }
      },
      'Ctrl-B': function(cm) {
        // Bold
        var selection = cm.getSelection();
        cm.replaceSelection('**' + selection + '**');
      },
      'Ctrl-I': function(cm) {
        // Italic
        var selection = cm.getSelection();
        cm.replaceSelection('*' + selection + '*');
      },
      'Ctrl-K': function(cm) {
        // Link
        var selection = cm.getSelection();
        cm.replaceSelection('[' + selection + '](url)');
      },
    },
  });

  // Sync editor content back to textarea before form submit
  var form = wrapper.closest('form');
  if (form) {
    form.addEventListener('submit', function() {
      el.value = editor.getValue();
    });
  }

  // Update textarea on every change
  editor.on('change', function() {
    el.value = editor.getValue();
  });

  // Resize editor to match original textarea
  function resizeEditor() {
    var originalHeight = el.style.height || window.getComputedStyle(el).height;
    if (originalHeight) {
      editor.getWrapperElement().style.height = originalHeight;
    }
  }
  resizeEditor();
});
