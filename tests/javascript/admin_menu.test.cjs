const assert = require('node:assert/strict');
const {test} = require('node:test');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

function setup() {
    const timers = new Map();
    let timerId = 0;
    class Element {
        constructor() {
            this.events = {};
            this.dataset = {};
            this.style = {};
            this.attributes = {};
            this.hidden = true;
            this.classList = {remove() {}, toggle() {}};
        }
        addEventListener(name, handler) { (this.events[name] ||= []).push(handler); }
        emit(name, values = {}) {
            const event = {target: this, pointerType: 'mouse', detail: 1, preventDefault() {}, ...values};
            for (const handler of this.events[name] || []) handler(event);
        }
        setAttribute(name, value) { this.attributes[name] = value; }
        querySelectorAll() { return []; }
        matches() { return false; }
        focus() { document.activeElement = this; }
        getBoundingClientRect() { return {right: 300}; }
    }
    const document = new Element();
    const window = new Element();
    const ids = Object.fromEntries(['admin-menu-trigger', 'nav-sidebar', 'main', 'admin-menu-close', 'content-start'].map(id => [id, new Element()]));
    document.body = new Element();
    document.documentElement = new Element();
    document.documentElement.clientWidth = 1600;
    document.getElementById = id => ids[id];
    document.querySelector = () => null;
    const menus = [true, true, false].map(hover => {
        const section = new Element(), trigger = new Element(), panel = new Element();
        trigger.closest = () => section;
        section.closest = () => hover ? {} : null;
        section.querySelector = selector => selector === '[data-menu-dropdown]' ? trigger : panel;
        section.contains = target => [section, trigger, panel].includes(target);
        return {section, trigger, panel};
    });
    document.querySelectorAll = selector => selector === '[data-menu-dropdown]' ? menus.map(menu => menu.trigger) : [];
    vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../../apps/website/registry/static/registry/admin_menu.js'), 'utf8'), {
        document, window, localStorage: {},
        setTimeout(callback) { timers.set(++timerId, callback); return timerId; },
        clearTimeout(id) { timers.delete(id); },
    });
    return {menus, document, flush() {
        const pending = [...timers.values()];
        timers.clear();
        pending.forEach(callback => callback());
    }};
}

test('clicking a hovered icon keeps it open; leaving closes despite retained focus', () => {
    const {menus: [menu], flush} = setup();
    menu.section.emit('pointerenter');
    menu.trigger.focus();
    menu.trigger.emit('click');
    assert.equal(menu.panel.hidden, false);
    menu.section.emit('pointerleave');
    flush();
    assert.equal(menu.panel.hidden, true);
});

test('reentering cancels dismissal and switching cancels the previous menu timer', () => {
    const {menus: [first, second], flush} = setup();
    first.section.emit('pointerenter');
    first.section.emit('pointerleave');
    first.section.emit('pointerenter');
    flush();
    assert.equal(first.panel.hidden, false);
    first.section.emit('pointerleave');
    second.section.emit('pointerenter');
    flush();
    assert.equal(first.panel.hidden, true);
    assert.equal(second.panel.hidden, false);
});

test('keyboard navigation survives pointer exit and dismisses when focus leaves', () => {
    const {menus: [menu], document, flush} = setup();
    menu.section.emit('pointerenter');
    menu.section.emit('keydown', {key: 'ArrowDown'});
    menu.section.emit('pointerleave');
    flush();
    assert.equal(menu.panel.hidden, false);
    document.emit('focusin');
    assert.equal(menu.panel.hidden, true);
});

test('touch and profile menus retain click toggling', () => {
    const {menus} = setup();
    for (const menu of [menus[0], menus[2]]) {
        menu.section.emit('pointerenter', {pointerType: 'touch'});
        assert.equal(menu.panel.hidden, true);
        menu.trigger.emit('click');
        assert.equal(menu.panel.hidden, false);
        menu.trigger.emit('click');
        assert.equal(menu.panel.hidden, true);
    }
});
