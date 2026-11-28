const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const source = fs.readFileSync('apps/website/operations/static/operations/catalogue_review.js', 'utf8');
for (const action of ['approve', 'reject']) {
  test(`${action} keeps POST destination, blocks duplicate submits and resets on back`, () => {
    const handlers = {};
    const form = {action: '/change/', addEventListener: (name, fn) => handlers[name] = fn,
      setAttribute() {}, removeAttribute() {}};
    const buttons = ['approve', 'reject'].map(value => ({form, formAction: `/${value}/`,
      dataset: {catalogueAction: value}, textContent: value, disabled: false}));
    const status = {textContent: ''};
    vm.runInNewContext(source, {document: {querySelectorAll: () => buttons, getElementById: () => status},
      window: {addEventListener: (name, fn) => handlers[name] = fn}});
    let prevented = false;
    const event = {submitter: buttons.find(b => b.dataset.catalogueAction === action),
      preventDefault: () => { prevented = true; }};
    handlers.submit(event);
    assert.equal(prevented, false);
    assert.equal(form.action, `/${action}/`);
    assert.ok(buttons.every(button => button.disabled));
    assert.match(event.submitter.textContent, /Applying|Rejecting/);
    assert.match(status.textContent, /Please wait/);
    handlers.submit(event);
    assert.equal(prevented, true);
    handlers.pageshow();
    assert.equal(form.action, '/change/');
    assert.ok(buttons.every(button => !button.disabled));
    assert.equal(status.textContent, '');
  });
}
