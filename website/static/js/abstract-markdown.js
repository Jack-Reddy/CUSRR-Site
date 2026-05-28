(function () {
  function ensureMarkedOptions() {
    if (window.marked && typeof window.marked.setOptions === 'function') {
      window.marked.setOptions({
        breaks: true,
        gfm: true,
        headerIds: false,
        mangle: false,
      });
    }
  }

  function renderMarkdown(source) {
    const text = String(source || '');
    if (!text) return '';

    ensureMarkedOptions();

    if (!window.marked || typeof window.marked.parse !== 'function') {
      return text;
    }

    const html = window.marked.parse(text);
    if (window.DOMPurify && typeof window.DOMPurify.sanitize === 'function') {
      return window.DOMPurify.sanitize(html, {
        USE_PROFILES: { html: true },
      });
    }

    return html;
  }

  function typesetMath(element) {
    if (!element) return;
    if (window.MathJax && typeof window.MathJax.typesetPromise === 'function') {
      if (typeof window.MathJax.typesetClear === 'function') {
        window.MathJax.typesetClear([element]);
      }
      window.MathJax.typesetPromise([element]).catch((error) => {
        console.error('MathJax typeset failed', error);
      });
    }
  }

  function renderToElement(element, source) {
    if (!element) return;
    element.innerHTML = renderMarkdown(source);
    typesetMath(element);
  }

  function plainText(source) {
    const preview = document.createElement('div');
    preview.innerHTML = renderMarkdown(source);
    return (preview.textContent || preview.innerText || '').trim();
  }

  function insertAtCursor(textarea, before, after = '', placeholder = '') {
    if (!textarea) return;

    const start = textarea.selectionStart ?? textarea.value.length;
    const end = textarea.selectionEnd ?? textarea.value.length;
    const selected = textarea.value.slice(start, end) || placeholder;
    const inserted = `${before}${selected}${after}`;

    textarea.setRangeText(inserted, start, end, 'end');
    textarea.focus();
    textarea.dispatchEvent(new Event('input', { bubbles: true }));
  }

  function insertTextAtCursor(textarea, text) {
    if (!textarea) return;

    const start = textarea.selectionStart ?? textarea.value.length;
    const end = textarea.selectionEnd ?? textarea.value.length;
    textarea.setRangeText(text, start, end, 'end');
    textarea.focus();
    textarea.dispatchEvent(new Event('input', { bubbles: true }));
  }

  function insertLink(textarea) {
    const url = window.prompt('Enter the link URL:');
    if (!url) return;
    const label = window.prompt('Enter the link text:', 'link text') || 'link text';
    insertAtCursor(textarea, '[', `](${url})`, label);
  }

  function markdownImage(url, altText) {
    const safeAlt = String(altText || 'image').trim() || 'image';
    return `![${safeAlt}](${url})`;
  }

  function uploadImageFiles(files) {
    const formData = new FormData();
    Array.from(files).forEach((file) => formData.append('files', file));

    return fetch('/api/v1/presentations/abstract-images', {
      method: 'POST',
      body: formData,
      credentials: 'same-origin',
    }).then(async (response) => {
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.error || 'Image upload failed');
      }
      return data.uploaded || [];
    });
  }

  function uploadImagesIntoAbstract(textarea) {
    return new Promise((resolve, reject) => {
      const fileInput = document.createElement('input');
      fileInput.type = 'file';
      fileInput.accept = 'image/*';
      fileInput.multiple = true;
      fileInput.style.display = 'none';

      fileInput.addEventListener('change', async () => {
        try {
          const files = fileInput.files ? Array.from(fileInput.files) : [];
          if (!files.length) {
            resolve([]);
            return;
          }

          const uploaded = await uploadImageFiles(files);
          uploaded.forEach((item) => {
            const imageMarkdown = markdownImage(item.url, item.filename);
            insertTextAtCursor(textarea, `${imageMarkdown}\n\n`);
          });
          resolve(uploaded);
        } catch (error) {
          reject(error);
        } finally {
          fileInput.remove();
        }
      });

      document.body.appendChild(fileInput);
      fileInput.click();
    });
  }

  async function insertImage(textarea) {
    const choice = window.prompt('Type an image URL or enter upload to add files:', 'upload');
    if (!choice) return;

    if (choice.trim().toLowerCase() === 'upload') {
      try {
        await uploadImagesIntoAbstract(textarea);
      } catch (error) {
        console.error('Image upload failed', error);
        window.alert(error.message || 'Could not upload image(s).');
      }
      return;
    }

    const url = choice.trim();
    const alt = window.prompt('Enter alt text for the image:', 'image description') || 'image description';
    insertTextAtCursor(textarea, markdownImage(url, alt));
  }

  function insertMathInline(textarea) {
    insertAtCursor(textarea, '$', '$', 'x^2');
  }

  function insertMathBlock(textarea) {
    insertAtCursor(textarea, '\n\n$$\n', '\n$$\n\n', 'E = mc^2');
  }

  function wireToolbar(textarea, toolbar) {
    if (!textarea || !toolbar) return;

    toolbar.querySelectorAll('[data-md-action]').forEach((button) => {
      button.addEventListener('click', () => {
        const action = button.dataset.mdAction;
        if (action === 'bold') insertAtCursor(textarea, '**', '**', 'bold text');
        if (action === 'italic') insertAtCursor(textarea, '_', '_', 'italic text');
        if (action === 'code') insertAtCursor(textarea, '`', '`', 'code');
        if (action === 'heading') insertAtCursor(textarea, '## ', '', 'Section title');
        if (action === 'list') insertAtCursor(textarea, '- ', '', 'List item');
        if (action === 'link') insertLink(textarea);
        if (action === 'image') insertImage(textarea);
        if (action === 'math-inline') insertMathInline(textarea);
        if (action === 'math-block') insertMathBlock(textarea);
      });
    });
  }

  function wirePreview(textarea, preview) {
    if (!textarea || !preview) return;

    const update = () => renderToElement(preview, textarea.value);
    textarea.addEventListener('input', update);
    update();
  }

  function initEditor({ textareaId, toolbarId, previewId }) {
    const textarea = document.getElementById(textareaId);
    const toolbar = document.getElementById(toolbarId);
    const preview = document.getElementById(previewId);

    wireToolbar(textarea, toolbar);
    wirePreview(textarea, preview);
  }

  function initRenderedAbstract({ sourceSelector, targetSelector }) {
    const source = document.querySelector(sourceSelector);
    const target = document.querySelector(targetSelector);
    if (!source || !target) return;

    const sourceText = typeof source.value === 'string'
      ? source.value
      : (source.dataset.abstract || source.textContent || '');

    renderToElement(target, sourceText);
  }

  window.AbstractMarkdownEditor = {
    initEditor,
    initRenderedAbstract,
    renderToElement,
    renderMarkdown,
    plainText,
  };
})();