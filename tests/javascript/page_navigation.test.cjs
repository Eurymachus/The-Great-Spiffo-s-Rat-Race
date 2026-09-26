const {test} = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const source = fs.readFileSync('apps/website/registry/static/registry/page_navigation.js', 'utf8');

function harness({scripts = [], responseUrl, account = 'test', eligible = true, executable = false, fail = false, ok = true, email = null} = {}) {
    const listeners = {};
    const location = {origin: 'https://example.test', href: 'https://example.test/', pathname: '/', search: '', assign: url => assigned.push(url)};
    const assigned = [], warnings = [], requests = [], events = [];
    let swapped = false;
    const main = {dataset: {softNavigation: 'on', navigationUser: 'test'}, setAttribute() {}, removeAttribute() {}, contains: () => false, replaceWith() { swapped = true; }};
    const decoded = {};
    const emailLink = {getAttribute: () => '/cdn-cgi/l/email-protection#' + email, setAttribute: (key, value) => {decoded.href = value;}};
    const emailSpan = {dataset: {cfemail: email}, replaceWith: value => {decoded.text = value;}};
    const replacement = {dataset: {softNavigation: eligible ? 'on' : 'off', navigationUser: account}, querySelector: () => executable, querySelectorAll: selector => email ? (selector.startsWith('a[') ? [emailLink] : [emailSpan]) : [], focus() {}};
    const script = (src, cf = false, inside = false) => ({getAttribute: key => key === 'src' ? src : cf ? 'false' : null, closest: () => inside ? {} : null});
    const document = {
        referrer: '', baseURI: location.href, createTextNode: value => value,
        getElementById: () => main,
        querySelectorAll: selector => selector === 'script[src]' ? [script('/static/app.123abc.js?v=1')] : [],
        addEventListener: (name, fn) => {listeners[name] = fn;},
        dispatchEvent: event => events.push(event),
    };
    const window = {addEventListener() {}, dispatchEvent() {}, scrollTo() {}};
    const parsed = {title: 'Destination', getElementById: () => replacement, querySelectorAll: () => scripts.map(s => script(...s))};
    vm.runInNewContext(source, {document, window, location, URL, URLSearchParams, AbortController, TextDecoder, Uint8Array,
        scrollX: 0, scrollY: 0, history: {replaceState() {}, pushState() {}},
        console: {warn: (...args) => warnings.push(args)},
        CustomEvent: class {constructor(type, init) {this.type = type;this.detail = init?.detail;}}, Event: class {},
        DOMParser: class {parseFromString() {return parsed;}},
        fetch: async url => {requests.push(url);if(fail) throw new TypeError('network');return {ok, url:responseUrl || url, redirected:!!responseUrl, text: async () => '<html></html>'};},
    });
    return {assigned, warnings, requests, events, decoded, get swapped() {return swapped;}, async click(path, overrides = {}) {
        const href = new URL(path, location.href).href;
        const link = {href, target:'', hasAttribute: () => false, ...overrides.link};
        const event = {button:0, target:{closest:() => link}, preventDefault() {this.defaultPrevented = true;}, ...overrides};
        listeners.click(event);
        await new Promise(resolve => setImmediate(resolve));
        return event;
    }};
}

test('production hashed assets plus self-removing Cloudflare decoder use one GET and swap', async () => {
    const h = harness({scripts:[['/static/app.123abc.js?v=1'], ['/cdn-cgi/scripts/5c5dd728/cloudflare-static/email-decode.min.js', true]]});
    await h.click('/rules/');
    assert.equal(h.swapped, true);assert.equal(h.requests.length, 1);assert.deepEqual(h.assigned, []);
});
test('unknown application scripts still fall back with a diagnostic', async () => {
    const h = harness({scripts:[['/static/new.js']]});await h.click('/mods/');
    assert.equal(h.swapped, false);assert.equal(h.warnings[0][1].reason, 'unknown-script');assert.equal(h.assigned.length, 1);
});
test('external Cloudflare lookalike is not exempt', async () => {
    const h = harness({scripts:[['https://other.test/cdn-cgi/scripts/abc/cloudflare-static/email-decode.min.js', true]]});await h.click('/rules/');assert.equal(h.swapped, false);
});
test('executable main content is never inserted', async () => {
    const h = harness({executable:true});await h.click('/rules/');assert.equal(h.warnings[0][1].reason, 'executable-content');
});
test('notification redirects to participant page swap and refresh badge', async () => {
    const h = harness({responseUrl:'https://example.test/account/'});await h.click('/account/notifications/00000000-0000-0000-0000-000000000001/');
    assert.equal(h.swapped, true);assert.ok(h.events.some(e => e.type === 'notification:opened'));
});
test('admin and authentication redirects load a full document', async () => {
    for(const path of ['/admin/registry/', '/login/']) {
        const h = harness({responseUrl:'https://example.test'+path});await h.click('/account/');
        assert.equal(h.swapped, false);assert.equal(h.warnings[0][1].reason, 'unsupported-destination');
    }
});
test('identity changes and ineligible pages fall back', async () => {
    for(const config of [{account:'another'}, {eligible:false}]) {
        const h = harness(config);await h.click('/rules/');assert.equal(h.swapped,false);assert.equal(h.assigned.length,1);
    }
});
test('external, admin, download and modified clicks retain browser behavior', async () => {
    for(const [path, overrides] of [['https://other.test/',{}], ['/admin/',{}], ['/rules/',{ctrlKey:true}], ['/rules/',{link:{hasAttribute:()=>true}}], ['/rules/',{link:{target:'_blank'}}]]) {
        const h = harness();const event = await h.click(path, overrides);assert.equal(h.requests.length,0);assert.ok(!event.defaultPrevented);
    }
});
test('fetch exceptions report a redacted diagnostic', async () => {
    const h = harness({fail:true});await h.click('/rules/?private=value');
    assert.equal(h.warnings[0][1].reason,'navigation-exception');assert.equal(h.warnings[0][1].path,'/rules/');assert.equal(JSON.stringify(h.warnings).includes('private'),false);
});

test('protected emails remain usable after a partial page change', async () => {
    const h = harness({email:'45363035352a37310531223637376b262a28'});await h.click('/privacy/');
    assert.equal(h.decoded.text,'support@tgsrr.com');assert.equal(h.decoded.href,'mailto:support@tgsrr.com');assert.equal(h.swapped,true);
});
test('malformed protected email produces a diagnostic rather than inserting broken content', async () => {
    const h = harness({email:'not-hex'});await h.click('/privacy/');assert.equal(h.swapped,false);assert.equal(h.warnings[0][1].reason,'navigation-exception');
});
test('HTTP failure logs its fallback cause', async () => {
    const h = harness({ok:false});await h.click('/rules/');assert.equal(h.warnings[0][1].reason,'http-status');assert.equal(h.swapped,false);
});
