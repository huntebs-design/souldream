(() => {
    const host = window.parent;
    const doc = host.document;
    const stateKey = "__dilseAdminDraftRetention";
    const previous = host[stateKey];
    if (!DILSE_ADMIN_DRAFT_AUTHENTICATED) {
        previous?.cleanup();
        delete host[stateKey];
        return;
    }
    if (previous) return;

    const drafts = new Map();
    const generations = new Map();
    const restored = new WeakSet();
    const prefix = "st-key-admin_message_text_";
    const fieldKey = (field) => {
        if (!(field instanceof host.HTMLTextAreaElement)) return null;
        const container = field.closest('[class*="st-key-admin_message_text_"]');
        return Array.from(container?.classList || []).find(name => name.startsWith(prefix)) || null;
    };
    const remember = (event) => {
        const key = fieldKey(event.target);
        if (key) drafts.set(key, event.target.value);
    };
    const restore = () => {
        doc.querySelectorAll('[class*="st-key-admin_message_text_"] textarea').forEach(field => {
            const key = fieldKey(field);
            if (!key || restored.has(field)) return;
            const split = key.lastIndexOf("_");
            const conversation = key.slice(0, split);
            const oldKey = generations.get(conversation);
            if (oldKey && oldKey !== key) drafts.delete(oldKey);
            generations.set(conversation, key);
            restored.add(field);
            const text = drafts.get(key);
            if (typeof text === "string" && !field.value && text) {
                const setter = Object.getOwnPropertyDescriptor(host.HTMLTextAreaElement.prototype, "value").set;
                setter.call(field, text);
                field.dispatchEvent(new host.Event("input", {bubbles: true}));
            }
            // Retain only the current tab's most recent conversation drafts.
            while (generations.size > 50) {
                const oldest = generations.keys().next().value;
                drafts.delete(generations.get(oldest));
                generations.delete(oldest);
            }
        });
    };
    const observer = new host.MutationObserver(restore);
    doc.addEventListener("input", remember, true);
    observer.observe(doc.body, {childList: true, subtree: true});
    host[stateKey] = {
        cleanup: () => {
            observer.disconnect();
            doc.removeEventListener("input", remember, true);
            drafts.clear();
            generations.clear();
        }
    };
    restore();
})();
