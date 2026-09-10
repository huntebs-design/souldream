const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('components/admin_draft_retention.js', 'utf8');
let fields = [];
let listener;
let observer;
let observerCount = 0;
class TextArea {
    constructor(key, value = '') { this.key = key; this._value = value; }
    get value() { return this._value; }
    set value(text) { this._value = text; }
    closest() { return {classList: [this.key]}; }
    dispatchEvent() { listener?.({target: this}); }
}
const doc = {
    body: {},
    querySelectorAll: () => fields,
    addEventListener: (_, callback) => { listener = callback; },
    removeEventListener: () => { listener = undefined; },
};
const host = {
    document: doc,
    HTMLTextAreaElement: TextArea,
    Event: class {},
    MutationObserver: class {
        constructor(callback) { observer = callback; observerCount++; }
        observe() {}
        disconnect() { observer = undefined; }
    },
};
const run = (authenticated) => vm.runInNewContext(
    source.replace('DILSE_ADMIN_DRAFT_AUTHENTICATED', JSON.stringify(authenticated)),
    {window: {parent: host}},
);
const mount = (conversation, nonce = 0) => {
    const field = new TextArea(`st-key-admin_message_text_${conversation}_${nonce}`);
    fields = [field];
    observer?.();
    return field;
};
run(true);
let first = mount('one');
first.value = 'First unsent reply'; first.dispatchEvent();
let second = mount('two');
assert.equal(second.value, '');
second.value = 'Second unsent reply'; second.dispatchEvent();
first = mount('one');
assert.equal(first.value, 'First unsent reply');
second = mount('two');
assert.equal(second.value, 'Second unsent reply');
second.value = ''; second.dispatchEvent();
assert.equal(mount('two').value, '');
assert.equal(mount('one', 1).value, '', 'Sending must not restore the previous draft');
assert.equal(mount('one', 0).value, '', 'The old draft must be discarded');
run(true);
assert.equal(observerCount, 1, 'Reruns must not add duplicate observers');
run(false);
assert.equal(listener, undefined);
assert.equal(observer, undefined);
assert.equal(host.__dilseAdminDraftRetention, undefined);
run(true);
assert.equal(mount('two').value, '', 'Locking must clear all drafts');
console.log('Admin draft lifecycle checks passed');
