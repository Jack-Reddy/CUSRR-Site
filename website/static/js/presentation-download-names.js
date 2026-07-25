(function () {
  function apiErrorMessage(response, fallback) {
    return response.text().then((bodyText) => {
      let bodyDetails = bodyText;
      if (bodyText) {
        try {
          bodyDetails = JSON.stringify(JSON.parse(bodyText), null, 2);
        } catch (error) {
          bodyDetails = bodyText;
        }
      }
      return [
        fallback,
        `Status: ${response.status} ${response.statusText || ''}`.trim(),
        response.url ? `URL: ${response.url}` : '',
        bodyDetails ? `Response body:\n${bodyDetails}` : 'Response body: empty',
      ].filter(Boolean).join('\n\n');
    });
  }

  async function downloadNamedPresentationZip(event) {
    event.preventDefault();
    event.stopPropagation();
    event.stopImmediatePropagation();

    const btn = event.currentTarget;
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Downloading...';

    try {
      const response = await fetch(`/api/v1/presentations/download-all-named?_=${Date.now()}`, {
        credentials: 'same-origin',
        cache: 'no-store',
      });

      if (!response.ok) {
        throw new Error(await apiErrorMessage(response, `Failed to download presentations: ${response.status}`));
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'presentations.zip';
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error(error);
      alert(error.message || 'Could not download presentations.');
    } finally {
      btn.disabled = false;
      btn.innerHTML = originalText || 'Download All Presentations';
    }
  }

  function replaceDownloadButton() {
    const originalBtn = document.getElementById('download-presentations');
    if (!originalBtn || originalBtn.dataset.namedDownloadBound === 'true') return;

    const btn = originalBtn.cloneNode(true);
    btn.dataset.namedDownloadBound = 'true';
    originalBtn.replaceWith(btn);
    btn.addEventListener('click', downloadNamedPresentationZip);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', replaceDownloadButton);
  } else {
    replaceDownloadButton();
  }
})();
