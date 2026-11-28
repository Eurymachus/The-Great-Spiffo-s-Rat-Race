const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

// Exercise typing and delayed network responses without a browser dependency.
const classes = () => ({remove() {}, toggle() {}});
const field = {classList: classes(), querySelectorAll: () => []};
const listeners = {};
const input = {
  value: '', addEventListener: (name, fn) => { listeners[name] = fn; },
  closest: () => field, removeAttribute() {}, setAttribute() {},
};
const output = {
  messages: [], classList: classes(),
  replaceChildren() { this.messages = []; },
  appendChild(item) { this.messages.push(item.textContent); },
};
const form = {
  dataset: {validationUrl: '/signup/validate/'},
  querySelector(selector) {
    if (selector === '[name="nickname"]') return input;
    if (selector === '[data-validation-for="nickname"]') return output;
    return null;
  },
};
const timers = new Map();
const requests = [];
let timerId = 0;
vm.runInNewContext(fs.readFileSync(path.join(__dirname,
  '../apps/website/registry/static/registry/registration_validation.js'), 'utf8'), {
  document: {
    addEventListener: (_, fn) => fn(), querySelector: () => form,
    createElement: () => ({}),
  }, URLSearchParams,
  setTimeout(fn, delay) { assert.equal(delay, 500); timers.set(++timerId, fn); return timerId; },
  clearTimeout(id) { timers.delete(id); },
  fetch: (_, options) => new Promise(resolve => requests.push({options, resolve})),
});
const type = value => { input.value = value; listeners.input(); };
const tick = () => { const pending = [...timers.values()]; timers.clear(); pending.forEach(fn => fn()); };
const reply = async (index, message) => {
  requests[index].resolve({ok: true, json: async () => ({valid: true, message})});
  await new Promise(resolve => setImmediate(resolve));
};
(async () => {
  type('Eu'); type('Eury');
  assert.equal(requests.length, 0);
  assert.equal(timers.size, 1);
  tick();
  assert.equal(requests[0].options.body.get('value'), 'Eury');
  type('NewRacer'); tick();
  await reply(1, 'New nickname available');
  await reply(0, 'Old result');
  assert.deepEqual(output.messages, ['New nickname available']);
  type('Another'); listeners.blur();
  assert.equal(timers.size, 0);
  assert.equal(requests.length, 3);
  type(''); await reply(2, 'Obsolete result'); tick();
  assert.deepEqual(output.messages, []);
  assert.equal(requests.length, 3);
  console.log('PASS: debounce, blur, stale responses and clearing');
})().catch(error => { console.error(error); process.exitCode = 1; });
