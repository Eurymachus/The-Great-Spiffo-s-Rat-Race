const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('apps/website/registry/static/registry/feedback_toast.js', 'utf8');
function harness() {
    const element = () => ({children: [], attrs: {}, listeners: {},
        append(...children) {this.children.push(...children);},
        setAttribute(k, v) {this.attrs[k] = v;},
        addEventListener(k, fn) {this.listeners[k] = fn;}, removeEventListener(k) {delete this.listeners[k];},
        remove() {this.removed = true;}});
    const body = element();
    const document = {...element(), body, createElement: element};
    const timers = new Map(); let id = 0;
    const window = {};
    vm.runInNewContext(source, {window, document,
        setTimeout(fn, duration) {timers.set(++id, {fn, duration}); return id;}, clearTimeout(id) {timers.delete(id);}});
    return {window, document, body, timers, element,
        announce() { for (const [id, timer] of timers) if (timer.duration === 0) { timers.delete(id); timer.fn(); } }};
}
test('info and errors have distinct presentation and announcement roles', () => {
    const h = harness();
    for (const type of ['info', 'error']) {
        h.window.RatRaceToast.show({type, message: '<plain text>'}); h.announce();
        const toast = h.body.children.at(-1).children[0];
        assert.equal(toast.className, `feedback-toast feedback-toast--${type}`);
        assert.equal(toast.children[1].attrs.role, type === 'error' ? 'alert' : 'status');
        assert.equal(toast.children[1].children[1].textContent, '<plain text>');
    }
    assert.equal(h.body.children[0].removed, true);
});
test('dismissal, timeout pausing and page navigation clean up feedback', () => {
    const h = harness(); h.window.RatRaceToast.show({message: 'Hello'}); h.announce();
    const region = h.body.children[0], toast = region.children[0];
    toast.listeners.pointerenter(); assert.equal(h.timers.size, 0);
    toast.listeners.pointerleave(); assert.equal(h.timers.size, 1);
    toast.children[2].listeners.click(); assert.equal(region.removed, true); assert.equal(h.timers.size, 0);
    h.window.RatRaceToast.show({message: 'Again'});
    h.document.listeners['page:before-change']();
    assert.equal(h.body.children[1].removed, true); assert.equal(h.timers.size, 0);
});
test('feedback mounts in an active dialog and is removed when it closes', () => {
    const h = harness(), dialog = h.element();
    h.document.activeElement = {closest: () => dialog};
    h.window.RatRaceToast.show({message: 'In modal'});
    assert.equal(h.body.children.length, 0);
    dialog.listeners.close(); assert.equal(dialog.children[0].removed, true);
});
