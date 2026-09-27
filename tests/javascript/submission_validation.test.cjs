const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('apps/website/registry/static/registry/submit_run.js', 'utf8');

function harness({serverError = false} = {}) {
    const timers = new Map();
    let timerId = 0;
    const element = () => ({
        attrs: {}, dataset: {}, listeners: {}, children: [], hidden: false, textContent: '',
        setAttribute(k, v) { this.attrs[k] = v; }, getAttribute(k) { return this.attrs[k]; },
        addEventListener(k, fn) { this.listeners[k] = fn; },
        append(...children) { this.children.push(...children); },
        replaceChildren() { this.children = []; this.textContent = ''; }, remove() {},
        querySelector() { return null; }, querySelectorAll() { return []; }, closest() { return null; },
        matches() { return true; }, removeAttribute(k) {delete this.attrs[k];},
        focus() { this.focused = true; }, scrollIntoView() { this.scrolled = true; },
    });
    const errors = element();
    errors.textContent = serverError ? 'Evidence required' : '';
    const helper = element();
    helper.querySelector = () => errors;
    const input = element();
    input.value = ''; input.willValidate = true; input.validity = {valid: true};
    input.setCustomValidity = message => { input.validity.valid = !message; };
    const form = element(); form.elements = [input];
    form.querySelector = selector => ({'#id_manual_evidence_url': input, '[data-vod-helper]': helper, '.errorlist': serverError ? errors : null}[selector] || null);
    errors.closest = () => ({querySelector: () => input});
    const signal = element();
    const document = {
        querySelector: selector => selector === '[data-run-submission-form]' ? form : null,
        querySelectorAll: () => [], addEventListener() {}, createElement: element,
    };
    const popups = [];
    const toasts = [];
    vm.runInNewContext(source, {document, URL, window: {
        RatRaceToast: {show: toast => toasts.push(toast)},
        RatRaceHint: {create: ({element, anchor}) => {popups.push({element, anchor}); return {show() {element.hidden = false;}, hide() {element.hidden = true;}};}},
        RatRacePages: {register: fn => fn(signal)}},
        setTimeout: fn => {timers.set(++timerId, fn); return timerId;}, clearTimeout: id => timers.delete(id)});
    return {input, helper, form, signal, popups, element, toasts,
        type(value) { input.value = value; input.listeners.input(); },
        pause() { const pending = [...timers.values()]; timers.clear(); pending.forEach(fn => fn()); },
        submit() { let prevented = false; form.listeners.submit({preventDefault() {prevented = true;}}); return prevented; },
    };
}

test('accepts supported recorded video URLs', () => {
    for (const url of ['https://www.twitch.tv/videos/123', 'https://m.twitch.tv:443/videos/123/',
        'https://youtube.com/watch?v=abcdefghijk&t=10', 'https://www.youtube.com/live/abcdefghijk/', 'https://youtu.be/abcdefghijk']) {
        const h = harness(); h.type(url); h.pause();
        assert.equal(h.helper.hidden, true, url);
        assert.equal(h.submit(), false, url);
    }
});
test('rejects channels, clips, unsafe hosts and malformed links', () => {
    for (const url of ['https://www.twitch.tv/walkoll', 'https://clips.twitch.tv/clip', 'http://twitch.tv/videos/123',
        'https://twitch.tv.evil.test/videos/123', 'https://user@twitch.tv/videos/123', 'https://twitch.tv:444/videos/123',
        'https://youtube.com/watch?v=short', 'https://youtube.com/watch?v=abcdefghijk&v=lmnopqrstuv', 'not a URL']) {
        const h = harness(); h.type(url); h.pause();
        assert.equal(h.helper.hidden, false, url);
        assert.equal(h.submit(), true, url);
        assert.equal(h.input.focused, true);
        assert.equal(h.input.scrolled, true);
        assert.match(h.toasts[0].message, /correct the highlighted errors/);
    }
});
test('submit validates immediately even before the typing timer fires', () => {
    const h = harness(); h.type('https://twitch.tv/walkoll');
    assert.equal(h.submit(), true);
});
test('correction clears feedback and empty evidence remains a server policy decision', () => {
    const h = harness(); h.type('https://twitch.tv/walkoll'); h.pause();
    h.type('https://twitch.tv/videos/123'); h.input.listeners.blur();
    assert.equal(h.helper.hidden, true);
    assert.equal(h.input.attrs['aria-invalid'], 'false');
    h.type(''); assert.equal(h.submit(), false);
});
test('server evidence errors receive focus and a toast on arrival', () => {
    const h = harness({serverError: true});
    assert.equal(h.input.focused, true);
    assert.equal(h.input.scrolled, true);
    assert.match(h.toasts[0].message, /correct the highlighted errors/);
    h.type('https://twitch.tv/videos/123'); h.pause();
    assert.equal(h.helper.hidden, true);
});
test('required fields use the shared floating control and clear when corrected', () => {
    const h = harness();
    const field = h.element();
    field.id = 'id_run_export'; field.willValidate = true;
    field.validity = {valid: false}; field.validationMessage = 'Please fill in this field.';
    h.form.elements.unshift(field);
    assert.equal(h.submit(), true);
    const popup = h.popups.find(item => item.anchor === field);
    assert.ok(popup);
    assert.equal(popup.element.children[0].textContent, 'Please fill in this field.');
    assert.equal(field.focused, true);
    field.validity.valid = true;
    h.form.listeners.input({target: field});
    assert.equal(popup.element.hidden, true);
});
