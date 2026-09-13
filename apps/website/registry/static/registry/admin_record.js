document.addEventListener('DOMContentLoaded', () => {
  if (!document.querySelector('#changelist, .challenge-run-registry')) return;
  const title = document.querySelector('#content > h1');
  if (!title) return;
  const heading = document.createElement('header');
  heading.className = 'admin-list-heading';
  title.before(heading);
  heading.append(title);
  const tools = document.querySelector('#content-main > .object-tools');
  if (tools) heading.append(tools);
});

document.addEventListener('click', event => {
  document.querySelectorAll('.run-tab-menu[open]').forEach(menu => {
    if (!menu.contains(event.target)) menu.removeAttribute('open');
  });
});
document.addEventListener('keydown', event => {
  if (event.key !== 'Escape') return;
  document.querySelectorAll('.run-tab-menu[open]').forEach(menu => {
    menu.removeAttribute('open');
    menu.querySelector('summary').focus();
  });
});

document.addEventListener('click', event => {
  const dialog = event.target;
  if (!(dialog instanceof HTMLDialogElement) || !dialog.matches('.run-workspace-panel[open]')) return;
  const bounds = dialog.getBoundingClientRect();
  if (event.clientX < bounds.left || event.clientX > bounds.right ||
      event.clientY < bounds.top || event.clientY > bounds.bottom) {
    dialog.close();
  }
});

document.addEventListener('DOMContentLoaded', () => {
  const tabs = document.querySelector('.run-saved-tabs');
  if (!tabs) return;
  let dragged;
  let busy = false;
  const send = async (action, view, order) => {
    const body = new URLSearchParams();
    body.set('csrfmiddlewaretoken', document.querySelector('[name=csrfmiddlewaretoken]').value);
    body.set('action', action);
    body.set('saved_view_action', action);
    if (view) body.set('view', view);
    order?.forEach(id => body.append('order', id));
    const response = await fetch(location.pathname, {method:'POST', body});
    if (!response.ok) throw new Error('Unable to save tab changes. Please refresh and try again.');
    return response;
  };
  tabs.addEventListener('contextmenu', event => {
    const tab = event.target.closest('[data-tab-id]');
    if (!tab) return;
    event.preventDefault();
    let menu = document.querySelector('.live-tab-context');
    if (menu) menu.remove();
    menu = document.createElement('div');
    menu.className = 'run-tab-menu-options live-tab-context';
    menu.style.position = 'fixed';
    menu.style.left = Math.min(event.clientX, innerWidth - 180) + 'px';
    menu.style.top = Math.min(event.clientY, innerHeight - 150) + 'px';
    for (const [action, label] of [['hide', 'Hide Tab'], ['up', 'Move Left'], ['down', 'Move Right']]) {
      const button = document.createElement('button');
      button.type = 'button'; button.textContent = label;
      button.addEventListener('click', async () => {
        menu.remove();
        try { const response = await send(action, tab.dataset.tabId); location.assign(response.url); }
        catch (error) { alert(error.message); }
      });
      menu.append(button);
    }
    document.body.append(menu);
    menu.querySelector('button').focus();
    const dismiss = e => { if (e.type === 'keydown' && e.key !== 'Escape') return; if (!menu.contains(e.target) || e.key === 'Escape') { menu.remove(); document.removeEventListener('click', dismiss); document.removeEventListener('keydown', dismiss); } };
    document.addEventListener('click', dismiss);
    document.addEventListener('keydown', dismiss);
  });
  let originalOrder = [];
  let dropped = false;
  const moveTab = before => {
    if (before === dragged || dragged.nextSibling === before) return;
    const positions = new Map([...tabs.children].map(tab => [tab, tab.getBoundingClientRect().left]));
    tabs.insertBefore(dragged, before);
    if (!matchMedia('(prefers-reduced-motion: reduce)').matches) {
      [...tabs.children].forEach(tab => {
        if (tab === dragged) return;
        const offset = positions.get(tab) - tab.getBoundingClientRect().left;
        tab.getAnimations().forEach(animation => animation.cancel());
        if (offset) tab.animate([{transform:`translateX(${offset}px)`}, {transform:'translateX(0)'}], {duration:160, easing:'ease-out'});
      });
    }
  };
  tabs.addEventListener('dragstart', event => {
    dragged = event.target.closest('[data-tab-id]');
    if (!dragged || busy) { event.preventDefault(); return; }
    originalOrder = [...tabs.children];
    dropped = false;
    event.dataTransfer.setData('text/plain', dragged.dataset.tabId);
    event.dataTransfer.effectAllowed = 'move';
    requestAnimationFrame(() => dragged?.classList.add('is-dragging'));
  });
  const dropZone = tabs.closest('.run-table-tabs');
  dropZone.addEventListener('dragenter', event => {
    if (dragged && !busy) { event.preventDefault(); event.dataTransfer.dropEffect = 'move'; }
  });
  dropZone.addEventListener('dragover', event => {
    if (!dragged || busy) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
    const candidates = [...tabs.querySelectorAll('[data-tab-id]')].filter(tab => tab !== dragged);
    const before = candidates.find(tab => event.clientX < tab.offsetLeft - tabs.scrollLeft + tabs.getBoundingClientRect().left - tabs.offsetLeft + tab.offsetWidth / 2);
    moveTab(before || null);
    const bounds = tabs.getBoundingClientRect();
    if (event.clientX < bounds.left + 30) tabs.scrollLeft -= 12;
    if (event.clientX > bounds.right - 30) tabs.scrollLeft += 12;
  });
  dropZone.addEventListener('drop', async event => {
    if (!dragged || busy) return;
    event.preventDefault();
    dropped = true;
    dragged.classList.remove('is-dragging');
    const snapshot = originalOrder;
    busy = true;
    try { await send('reorder', null, [...tabs.querySelectorAll('[data-tab-id]')].map(tab => tab.dataset.tabId)); }
    catch (error) { snapshot.forEach(tab => tabs.append(tab)); alert(error.message); }
    finally { busy = false; dragged = null; }
  });
  tabs.addEventListener('dragend', () => {
    dragged?.classList.remove('is-dragging');
    if (!dropped) originalOrder.forEach(tab => tabs.append(tab));
    dragged = null;
  });
  document.querySelectorAll('[data-tab-action]').forEach(button => button.addEventListener('click', async () => {
    if (busy) return;
    busy = true;
    try { const response = await send(button.dataset.tabAction, button.dataset.view); location.assign(response.url); }
    catch (error) { alert(error.message); busy = false; }
  }));
});
