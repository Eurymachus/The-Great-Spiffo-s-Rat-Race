(() => {
  const dialog = document.querySelector('[data-event-review-dialog]');
  if (!dialog || typeof dialog.showModal !== 'function') return;
  const content = dialog.querySelector('[data-event-review-content]');
  const previous = dialog.querySelector('[data-event-review-previous]');
  const next = dialog.querySelector('[data-event-review-next]');
  const position = dialog.querySelector('[data-event-review-position]');
  let sources = [];
  let index = 0;
  let opener;
  const render = () => {
    content.replaceChildren(sources[index].cloneNode(true));
    position.textContent = `${index + 1} of ${sources.length}`;
    previous.disabled = index === 0;
    next.disabled = index === sources.length - 1;
    content.scrollTop = 0;
  };
  document.querySelectorAll('[data-event-review]').forEach(link => {
    link.addEventListener('click', event => {
      sources = link.dataset.eventReview.split(',').map(sequence =>
        document.getElementById(`event-evidence-${sequence}`)?.querySelector('[data-event-evidence-content]')
      ).filter(Boolean);
      if (!sources.length) return;
      event.preventDefault();
      opener = link;
      index = 0;
      render();
      dialog.showModal();
    });
  });
  previous.addEventListener('click', () => { if (index > 0) { index--; render(); } });
  next.addEventListener('click', () => { if (index < sources.length - 1) { index++; render(); } });
  dialog.querySelectorAll('[data-event-review-close]').forEach(button => button.addEventListener('click', () => dialog.close()));
  dialog.addEventListener('click', event => {
    const rect = dialog.getBoundingClientRect();
    if (event.target === dialog && (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom)) dialog.close();
  });
  dialog.addEventListener('close', () => opener?.focus());
})();
