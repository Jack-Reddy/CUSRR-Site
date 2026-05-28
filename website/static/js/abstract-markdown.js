(function () {
  let activeTextarea = null;

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

  function getSelectionRange(textarea) {
    const storedStart = Number.parseInt(textarea?.dataset?.mdSelectionStart || '', 10);
    const storedEnd = Number.parseInt(textarea?.dataset?.mdSelectionEnd || '', 10);

    if (Number.isFinite(storedStart) && Number.isFinite(storedEnd)) {
      return { start: storedStart, end: storedEnd };
    }

    return {
      start: textarea?.selectionStart ?? textarea?.value.length ?? 0,
      end: textarea?.selectionEnd ?? textarea?.value.length ?? 0,
    };
  }

  function rememberSelection(textarea) {
    if (!textarea) return;

    const capture = () => {
      textarea.dataset.mdSelectionStart = String(textarea.selectionStart ?? 0);
      textarea.dataset.mdSelectionEnd = String(textarea.selectionEnd ?? 0);
    };

    ['keyup', 'mouseup', 'select', 'focus', 'blur', 'input'].forEach((eventName) => {
      textarea.addEventListener(eventName, capture);
    });

    capture();
  }

  function setActiveTextarea(textarea) {
    activeTextarea = textarea || null;
    if (activeTextarea) {
      rememberSelection(activeTextarea);
    }
  }

  function getActiveTextarea() {
    return activeTextarea;
  }

  function plainText(source) {
    const preview = document.createElement('div');
    preview.innerHTML = renderMarkdown(source);
    return (preview.textContent || preview.innerText || '').trim();
  }

  function insertAtCursor(textarea, before, after = '', placeholder = '') {
    if (!textarea) return;

    const { start, end } = getSelectionRange(textarea);
    const selected = textarea.value.slice(start, end) || placeholder;
    const inserted = `${before}${selected}${after}`;

    textarea.setRangeText(inserted, start, end, 'end');
    textarea.focus();
    textarea.dispatchEvent(new Event('input', { bubbles: true }));
  }

  function insertTextAtCursor(textarea, text) {
    if (!textarea) return;

    const { start, end } = getSelectionRange(textarea);
    textarea.setRangeText(text, start, end, 'end');
    textarea.focus();
    textarea.dispatchEvent(new Event('input', { bubbles: true }));
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

  async function uploadImagesIntoAbstract(textarea, files) {
    const uploaded = await uploadImageFiles(files);
    uploaded.forEach((item) => {
      const imageMarkdown = markdownImage(item.url, item.filename);
      insertTextAtCursor(textarea, `${imageMarkdown}\n\n`);
    });
    return uploaded;
  }

  function openBootstrapModal(modalId) {
    const modalElement = document.getElementById(modalId);
    if (!modalElement || !window.bootstrap || !window.bootstrap.Modal) return null;

    const modal = window.bootstrap.Modal.getOrCreateInstance(modalElement);
    modal.show();
    return modal;
  }

  function setupImageModals(textarea) {
    const linkModal = document.getElementById('image-link-modal');
    const uploadModal = document.getElementById('image-upload-modal');
    const linkForm = document.getElementById('image-link-form');
    const uploadForm = document.getElementById('image-upload-form');
    const linkUrl = document.getElementById('image-link-url');
    const linkAlt = document.getElementById('image-link-alt');
    const uploadFiles = document.getElementById('image-upload-files');
    const uploadStatus = document.getElementById('image-upload-status');
    const uploadButton = document.getElementById('image-upload-submit');

    if (linkForm && !linkForm.dataset.mdBound) {
      linkForm.dataset.mdBound = 'true';
      linkForm.addEventListener('submit', (event) => {
        event.preventDefault();
        const targetTextarea = getActiveTextarea() || textarea;
        const url = linkUrl?.value.trim();
        const alt = linkAlt?.value.trim() || 'image';
        if (!targetTextarea || !url) return;

        insertTextAtCursor(targetTextarea, `${markdownImage(url, alt)}\n\n`);
        if (window.bootstrap && linkModal) {
          window.bootstrap.Modal.getOrCreateInstance(linkModal).hide();
        }
        linkForm.reset();
      });
    }

    if (uploadForm && !uploadForm.dataset.mdBound) {
      uploadForm.dataset.mdBound = 'true';
      uploadForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const targetTextarea = getActiveTextarea() || textarea;
        const files = uploadFiles?.files ? Array.from(uploadFiles.files) : [];

        if (!targetTextarea || !files.length) {
          if (uploadStatus) {
            uploadStatus.textContent = 'Choose one or more image files first.';
          }
          return;
        }

        if (uploadButton) {
          uploadButton.disabled = true;
        }
        if (uploadStatus) {
          uploadStatus.textContent = 'Uploading...';
        }

        try {
          await uploadImagesIntoAbstract(targetTextarea, files);
          if (window.bootstrap && uploadModal) {
            window.bootstrap.Modal.getOrCreateInstance(uploadModal).hide();
          }
          uploadForm.reset();
          if (uploadStatus) {
            uploadStatus.textContent = '';
          }
        } catch (error) {
          console.error('Image upload failed', error);
          if (uploadStatus) {
            uploadStatus.textContent = error.message || 'Could not upload image(s).';
          }
          window.alert(error.message || 'Could not upload image(s).');
        } finally {
          if (uploadButton) {
            uploadButton.disabled = false;
          }
        }
      });
    }
  }

  function insertMathInline(textarea) {
    insertAtCursor(textarea, '$', '$', 'x^2');
  }

  function insertMathBlock(textarea) {
    insertAtCursor(textarea, '\n\n$$\n', '\n$$\n\n', 'E = mc^2');
  }

  function wireToolbar(textarea, toolbar) {
    if (!textarea || !toolbar) return;

    setActiveTextarea(textarea);
    rememberSelection(textarea);

    textarea.addEventListener('focus', () => setActiveTextarea(textarea));
    textarea.addEventListener('click', () => setActiveTextarea(textarea));
    textarea.addEventListener('keyup', () => setActiveTextarea(textarea));
    textarea.addEventListener('mouseup', () => setActiveTextarea(textarea));

    setupImageModals(textarea);

    toolbar.querySelectorAll('[data-md-action]').forEach((button) => {
      button.addEventListener('click', () => {
        const action = button.dataset.mdAction;
        if (action === 'bold') insertAtCursor(textarea, '**', '**', 'bold text');
        if (action === 'italic') insertAtCursor(textarea, '_', '_', 'italic text');
        if (action === 'code') insertAtCursor(textarea, '`', '`', 'code');
        if (action === 'heading') insertAtCursor(textarea, '## ', '', 'Section title');
        if (action === 'list') insertAtCursor(textarea, '- ', '', 'List item');
        if (action === 'link') openBootstrapModal('image-link-modal');
        if (action === 'image-upload') openBootstrapModal('image-upload-modal');
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