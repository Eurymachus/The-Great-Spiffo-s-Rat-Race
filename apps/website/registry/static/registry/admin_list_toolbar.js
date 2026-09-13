
document.addEventListener('DOMContentLoaded', () => {
  const list = document.querySelector('#changelist');
  const source = document.querySelector('#changelist-filter');
  if (!list || !source || document.querySelector('.run-filter-toolbar')) return;
  const params = new URLSearchParams(location.search);
  const bar = document.createElement('div');
  bar.className = 'shared-list-toolbar';
  const search = document.querySelector('#toolbar');
  if (search) bar.append(search);
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'shared-filter-toggle';
  button.innerHTML = '<span>Filters</span><span class="shared-filter-arrow" aria-hidden="true">▾</span>';
  button.setAttribute('popovertarget', 'shared-filter-picker');
  button.setAttribute('aria-expanded', 'false');
  const picker = document.createElement('div');
  picker.id = 'shared-filter-picker';
  picker.setAttribute('popover', 'auto');
  const title = document.createElement('strong');
  title.textContent = 'Filters';
  picker.append(title);
  const chips = document.createElement('div');
  chips.className = 'shared-filter-chips';
  const groups = [];
  let timer;
  const pickerStateKey = 'admin-filter-picker:' + location.pathname;
  const schedule = () => {
    render();
    clearTimeout(timer);
    timer = setTimeout(() => {
      if (picker.matches(':popover-open')) sessionStorage.setItem(pickerStateKey, String(picker.scrollTop));
      else sessionStorage.removeItem(pickerStateKey);
      if (document.querySelector('.run-saved-tabs')) params.set('_filters', '1');
      location.search = params.toString();
    }, 800);
  };
  source.querySelectorAll('details').forEach(details => {
    const links = [...details.querySelectorAll('li a')];
    if (links.length < 2) return;
    const base = new URL(links[0].href).searchParams;
    const options = links.slice(1).map(link => {
      const target = new URL(link.href).searchParams;
      const changes = [...target].filter(([key, value]) => base.get(key) !== value);
      return {text: link.textContent.trim(), changes, initial: link.closest('li').classList.contains('selected')};
    });
    const keys = new Set(options.flatMap(option => option.changes.map(([key]) => key)));
    // Exact field lookups support Django's native OR lookup. Date ranges and
    // custom filters keep their mutually exclusive choice semantics.
    const exact = keys.size === 1 && [...keys][0].endsWith('__exact') && options.every(option => option.changes.length === 1);
    const key = [...keys][0];
    const inKey = exact ? key.slice(0, -7) + '__in' : null;
    if (![...keys].some(key => params.has(key)) && !(inKey && params.has(inKey))) {
      options.filter(option => option.initial).forEach(option => option.changes.forEach(([key,value]) => params.set(key,value)));
    }
    const fieldset = document.createElement('fieldset');
    const legend = document.createElement('legend');
    const groupTitle = details.dataset.filterTitle || '';
    legend.textContent = groupTitle.charAt(0).toUpperCase() + groupTitle.slice(1);
    fieldset.append(legend);
    const clear = () => { keys.forEach(key => params.delete(key)); if (inKey) params.delete(inKey); };
    const selected = option => exact
      ? (params.get(inKey) || params.get(key) || '').split(',').includes(option.changes[0][1])
      : option.changes.length > 0 && option.changes.every(([key,value]) => params.get(key) === value);
    options.forEach(option => {
      const label = document.createElement('label');
      const input = document.createElement('input');
      input.type = 'checkbox';
      option.input = input;
      label.append(input, document.createTextNode(option.text));
      fieldset.append(label);
      option.toggle = () => {
        const wasSelected = selected(option);
        if (exact) {
          const values = new Set((params.get(inKey) || params.get(key) || '').split(',').filter(Boolean));
          const value = option.changes[0][1];
          wasSelected ? values.delete(value) : values.add(value);
          clear();
          if (values.size) params.set(inKey, [...values].join(','));
        } else {
          clear();
          if (!wasSelected) option.changes.forEach(([key,value]) => params.set(key,value));
        }
        params.delete('p');
        schedule();
      };
      input.addEventListener('change', option.toggle);
    });
    groups.push({title: legend.textContent, options, selected, clear});
    picker.append(fieldset);
  });
  function render() {
    chips.replaceChildren();
    groups.forEach(group => group.options.forEach(option => {
      option.input.checked = group.selected(option);
      if (!option.input.checked) return;
      const chip = document.createElement('button');
      chip.type = 'button';
      chip.textContent = group.title + ': ' + option.text + ' ×';
      chip.setAttribute('aria-label', 'Remove ' + group.title + ': ' + option.text);
      chip.addEventListener('click', option.toggle);
      chips.append(chip);
    }));
  }
  const reset = document.createElement('button');
  reset.type = 'button'; reset.className = 'shared-filter-reset'; reset.textContent = 'Reset filters';
  reset.addEventListener('click', () => { groups.forEach(group => group.clear()); params.delete('p'); schedule(); });
  bar.append(button, reset, picker, chips);
  source.remove();
  list.prepend(bar);
  list.classList.add('shared-list-filters');
  const position = () => {
    const rect = button.getBoundingClientRect();
    picker.style.left = Math.max(8, Math.min(rect.left, innerWidth - 328)) + 'px';
    picker.style.top = rect.bottom + 6 + 'px';
    picker.style.maxHeight = Math.max(120, innerHeight - rect.bottom - 20) + 'px';
  };
  picker.addEventListener('beforetoggle', position);
  picker.addEventListener('toggle', () => {
    const open = picker.matches(':popover-open');
    button.setAttribute('aria-expanded', String(open));
    button.lastElementChild.textContent = open ? '▴' : '▾';
  });
  window.addEventListener('resize', position);
  render();
  const previousScroll = sessionStorage.getItem(pickerStateKey);
  sessionStorage.removeItem(pickerStateKey);
  if (previousScroll !== null) {
    picker.showPopover();
    picker.scrollTop = Number(previousScroll);
  }
});

// Selected filters overlay the results instead of moving them down the page.
document.addEventListener('DOMContentLoaded', () => {
  const chips = document.querySelector('#run-filter-chips, .shared-filter-chips');
  if (!chips) return;
  const panel = document.createElement('details');
  panel.className = 'selected-filter-panel';
  const summary = document.createElement('summary');
  panel.append(summary);
  chips.before(panel);
  panel.append(chips);
  const update = () => {
    const count = chips.querySelectorAll('button').length;
    summary.textContent = 'Selected filters (' + count + ')';
  };
  new MutationObserver(update).observe(chips, {childList:true});
  update();
  document.addEventListener('click', event => {
    if (!panel.contains(event.target)) panel.open = false;
  });
  panel.addEventListener('keydown', event => {
    if (event.key === 'Escape') { panel.open = false; summary.focus(); }
  });
});
