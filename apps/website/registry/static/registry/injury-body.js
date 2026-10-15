const initialiseInjuryBody = () => {
  const root = document.querySelector('[data-injury-body]');
  if (!root) return;
  const data = JSON.parse(document.getElementById('run-injury-body-data').textContent);
  const canvas = root.querySelector('[data-body-canvas]'), ctx = canvas.getContext('2d');
  const stage = root.querySelector('[data-body-stage]');
  const info = root.querySelector('[data-body-info]');
  const cache = {};
  let sex = data.sex || 'male', active = null;
  function dismiss() {
    active = null;
    info.hidden = true;
    canvas.style.cursor = 'default';
    draw();
  }
  function details(id, event) {
    active = id;
    const part = data.parts.find(p => p.id === id);
    const title = document.createElement('strong'); title.textContent = part.name;
    const count = document.createElement('p');
    count.textContent = `${part.total} ${part.total === 1 ? 'injury' : 'injuries'}`;
    const list = document.createElement('ul');
    for (const injury of part.injuries) {
      const li = document.createElement('li'); li.textContent = `${injury.name}: ${injury.count}`; list.append(li);
    }
    if (part.unclassified) {
      const li = document.createElement('li'); li.textContent = `Other injuries: ${part.unclassified}`; list.append(li);
    }
    info.replaceChildren(title, count, list);
    info.hidden = false;
    const bounds = stage.getBoundingClientRect();
    const body = canvas.getBoundingClientRect();
    let x = event ? event.clientX - bounds.left + 18 : body.right - bounds.left + 12;
    let y = event ? event.clientY - bounds.top - 20 : bounds.height / 3;
    if (x + info.offsetWidth > bounds.width - 8) {
      x = event ? event.clientX - bounds.left - info.offsetWidth - 18 : bounds.width - info.offsetWidth - 8;
    }
    info.style.left = `${Math.max(8, x)}px`;
    info.style.top = `${Math.max(8, Math.min(y, bounds.height - info.offsetHeight - 8))}px`;
    draw();
  }
  function draw() {
    const view = cache[sex]; if (!view) return;
    canvas.width = view.body.width; canvas.height = view.body.height;
    ctx.globalAlpha = .65;
    ctx.drawImage(view.body.image, 0, 0);
    for (const part of data.parts) {
      if (part.total <= 0 && part.id !== active) continue;
      ctx.globalAlpha = part.id === active ? 1 : .9;
      ctx.drawImage(part.total > 0 ? view[part.id].tinted : view[part.id].image, 0, 0, view.body.width, view.body.height);
    }
    ctx.globalAlpha = 1;
    if (view.outline) ctx.drawImage(view.outline.image, 0, 0);
  }
  function hit(event) {
    const view = cache[sex]; if (!view) return;
    const box = canvas.getBoundingClientRect();
    const x = Math.floor((event.clientX-box.left)*view.body.width/box.width);
    const y = Math.floor((event.clientY-box.top)*view.body.height/box.height);
    if (x < 0 || y < 0 || x >= view.body.width || y >= view.body.height) return dismiss();
    const part = [...data.parts].reverse().find(p => p.total > 0 && view[p.id].pixels[(y*view[p.id].width+x)*4+3] > 32);
    if (!part) return dismiss();
    canvas.style.cursor = 'pointer';
    details(part.id, event);
  }
  root.querySelector('[data-body-switch]')?.addEventListener('click', () => {
    sex = sex === 'male' ? 'female' : 'male'; dismiss();
  });
  canvas.addEventListener('pointermove', event => {
    if (event.pointerType !== 'touch') hit(event);
  });
  canvas.addEventListener('pointerleave', event => {
    if (event.pointerType !== 'touch') dismiss();
  });
  canvas.addEventListener('click', hit);
  canvas.addEventListener('blur', dismiss);
  canvas.addEventListener('keydown', event => {
    if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); dismiss(); return; }
    if (!['ArrowDown', 'ArrowRight', 'ArrowUp', 'ArrowLeft', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    const parts = data.parts.filter(p => p.total > 0);
    if (!parts.length) return;
    const index = parts.findIndex(p => p.id === active);
    const step = ['ArrowUp', 'ArrowLeft'].includes(event.key) ? -1 : 1;
    const target = event.key === 'Home' ? 0 : event.key === 'End' ? parts.length - 1 : index < 0 ? 0 : (index + step + parts.length) % parts.length;
    details(parts[target].id);
  });
  root.closest('dialog')?.addEventListener('close', dismiss);
  Promise.all(Object.entries(data.views).map(async ([name, urls]) => {
    const view = {};
    await Promise.all(Object.entries(urls).map(async ([id, url]) => {
      const image = new Image(); image.src = url; await image.decode();
      const mask = document.createElement('canvas'); mask.width=image.width; mask.height=image.height;
      const c = mask.getContext('2d'); c.drawImage(image,0,0);
      const pixels = c.getImageData(0,0,image.width,image.height).data;
      c.globalCompositeOperation='source-in'; c.fillStyle='#cc2424'; c.fillRect(0,0,mask.width,mask.height);
      view[id]={image, tinted:mask, pixels, width:image.width, height:image.height};
    }));
    cache[name]=view;
  })).then(draw).catch(() => {
    canvas.hidden = true;
    root.querySelector('.injury-body-hint').hidden = true;
    root.querySelector('[data-body-switch]')?.setAttribute('hidden', '');
    const list = document.createElement('ul');
    for (const part of data.parts.filter(p => p.total > 0)) {
      const li = document.createElement('li');
      const types = part.injuries.map(i => `${i.name}: ${i.count}`);
      if (part.unclassified) types.push(`Other injuries: ${part.unclassified}`);
      li.textContent = `${part.name}: ${part.total} (${types.join(', ')})`;
      list.append(li);
    }
    stage.replaceChildren(list);

  });
};
if (window.RatRacePages) window.RatRacePages.register(initialiseInjuryBody);
else initialiseInjuryBody();
