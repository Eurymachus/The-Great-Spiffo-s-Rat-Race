(() => {
  const buttons = [...document.querySelectorAll('[data-catalogue-action]')];
  const form = buttons[0]?.form;
  if (!form) return;
  const status = document.getElementById('catalogue-action-status');
  const labels = buttons.map(button => button.textContent);
  const originalAction = form.action;
  let submitting = false;
  form.addEventListener('submit', event => {
    if (submitting) {
      event.preventDefault();
      return;
    }
    if (event.defaultPrevented || !buttons.includes(event.submitter)) return;
    submitting = true;
    const button = event.submitter;
    // Preserve the chosen endpoint when disabling the native submitter.
    form.action = button.formAction;
    button.textContent = button.dataset.catalogueAction === 'approve'
      ? 'Applying catalogue…' : 'Rejecting review…';
    status.textContent = 'Please wait for confirmation. This may take a little while.';
    form.setAttribute('aria-busy', 'true');
    buttons.forEach(control => { control.disabled = true; });
  });
  window.addEventListener('pageshow', () => {
    submitting = false;
    form.action = originalAction;
    form.removeAttribute('aria-busy');
    status.textContent = '';
    buttons.forEach((button, index) => {
      button.disabled = false;
      button.textContent = labels[index];
    });
  });
})();
