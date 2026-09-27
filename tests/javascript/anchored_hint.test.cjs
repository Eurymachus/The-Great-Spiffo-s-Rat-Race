const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('apps/website/registry/static/registry/anchored_hint.js', 'utf8');
function harness(placement, rect = {left: 300, right: 340, top: 300, bottom: 340, width: 40, height: 40}) {
    const events = () => ({listeners: {}, addEventListener(name, fn) {this.listeners[name] = fn;}, removeEventListener() {}});
    const container = {...events(), append(node) {this.child = node;}};
    const anchor = {isConnected: true, closest: () => null, getClientRects: () => [rect], getBoundingClientRect: () => rect, focus() {this.focused = true;}};
    const button = events();
    const element = {classList: {add() {}}, dataset: {}, style: {setProperty(k, v) {this[k] = v;}},
        offsetWidth: 160, offsetHeight: 40, querySelector: () => button, remove() {this.removed = true;}};
    const document = {...events(), body: container};
    const window = {...events(), innerWidth: 800, innerHeight: 600};
    let disconnected = false;
    vm.runInNewContext(source, {window, document, AbortController,
        ResizeObserver: class {observe() {} disconnect() {disconnected = true;}}});
    const popup = window.RatRaceHint.create({anchor, element, placement});
    return {popup, element, anchor, button, document, rect, get disconnected() {return disconnected;}};
}
test('positions all four sides outside the anchor', () => {
    const expected = {top: ['240px', '250px'], bottom: ['240px', '350px'], left: ['130px', '300px'], right: ['350px', '300px']};
    for (const side of Object.keys(expected)) {
        const h = harness(side); h.popup.show();
        assert.equal(h.element.hidden, false);
        assert.equal(h.element.dataset.placement, side);
        assert.deepEqual([h.element.style.left, h.element.style.top], expected[side]);
    }
});
test('flips at the viewport edge and clamps horizontal overflow', () => {
    const h = harness('bottom', {left: 0, right: 40, top: 550, bottom: 590, width: 40, height: 40});
    h.popup.show();
    assert.equal(h.element.dataset.placement, 'top');
    assert.equal(h.element.style.left, '8px');
});
test('scroll repositions and hides a helper when its anchor leaves the viewport', () => {
    const h = harness('bottom'); h.popup.show();
    h.rect.top = 200; h.rect.bottom = 240;
    h.document.listeners.scroll(); assert.equal(h.element.style.top, '250px');
    h.rect.top = -100; h.rect.bottom = -60;
    h.document.listeners.scroll(); assert.equal(h.element.hidden, true);
});
test('dismissal restores focus and navigation releases the popup', () => {
    const h = harness('top'); h.popup.show(); h.button.listeners.click();
    assert.equal(h.element.hidden, true); assert.equal(h.anchor.focused, true);
    h.document.listeners['page:before-change']();
    assert.equal(h.element.removed, true); assert.equal(h.disconnected, true);
    h.popup.show(); assert.equal(h.element.hidden, true);
});
test('collapsing details hides retained bounds and reopening repositions the hint', () => {
    const h = harness('bottom'); h.popup.show();
    const details = {querySelector: () => ({contains: () => false})};
    h.anchor.closest = selector => selector === 'details:not([open])' ? details : null;
    h.document.listeners.toggle();
    assert.equal(h.element.hidden, true);
    h.anchor.closest = () => null;
    h.rect.top = 200; h.rect.bottom = 240;
    h.document.listeners.toggle();
    assert.equal(h.element.hidden, false);
    assert.equal(h.element.style.top, '250px');
});
test('an anchor with no rendered box hides its hint', () => {
    const h = harness('bottom'); h.popup.show();
    h.anchor.getClientRects = () => [];
    h.popup.position();
    assert.equal(h.element.hidden, true);
});
