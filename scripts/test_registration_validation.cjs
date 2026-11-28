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
const button = {disabled: false};
const formListeners = {};
let nativeValid = true;
const form = {
  dataset: {validationUrl: '/signup/validate/'},
  checkValidity: () => nativeValid,
  addEventListener: (name, fn) => { formListeners[name] = fn; },
  querySelector(selector) {
    if (selector === 'button[type="submit"]') return button;
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
const reply = async (index, message, valid = true) => {
  requests[index].resolve({ok: true, json: async () => ({valid, message, errors: [message]})});
  await new Promise(resolve => setImmediate(resolve));
};
(async () => {
  assert.equal(button.disabled, true);
  type('Eu'); type('Eury');
  assert.equal(button.disabled, true);
  let prevented = false;
  formListeners.submit({preventDefault() { prevented = true; }});
  assert.equal(prevented, true);
  assert.equal(requests.length, 0);
  assert.equal(timers.size, 1);
  tick();
  assert.equal(requests[0].options.body.get('value'), 'Eury');
  type('NewRacer'); tick();
  await reply(1, 'New nickname available');
  assert.equal(button.disabled, false);
  await reply(0, 'Old result');
  assert.deepEqual(output.messages, ['New nickname available']);
  nativeValid = false; formListeners.change();
  assert.equal(button.disabled, true);
  nativeValid = true; formListeners.change();
  assert.equal(button.disabled, false);
  type('Another'); listeners.blur();
  assert.equal(timers.size, 0);
  assert.equal(requests.length, 3);
  type('Reserved'); tick();
  await reply(3, 'Already reserved', false);
  assert.equal(button.disabled, true);
  type('FreeName');
  assert.equal(button.disabled, true);
  tick(); await reply(4, 'Available');
  assert.equal(button.disabled, false);
  console.log('PASS: submit guard, invalid and pending states, recovery and required controls');
  type(''); await reply(2, 'Obsolete result'); tick();
  assert.deepEqual(output.messages, []);
  assert.equal(requests.length, 5);
  assert.equal(button.disabled, true);
  console.log('PASS: debounce, blur, stale responses and clearing');
})().catch(error => { console.error(error); process.exitCode = 1; });
