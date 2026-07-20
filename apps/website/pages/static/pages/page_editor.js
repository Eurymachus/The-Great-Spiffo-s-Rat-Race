document.addEventListener("DOMContentLoaded", () => {
    const editor = document.querySelector("[data-page-editor]");
    const payload = document.querySelector("#id_page_builder_data");
    if (!editor || !payload) return;

    const list = editor.querySelector("[data-section-list]");
    const form = editor.closest("form");
    const stateStorageKey = `rat-race-page-editor:${window.location.pathname}`;
    let sections = [];
    let baseline = "";
    let submitting = false;
    try { sections = JSON.parse(payload.value || "[]"); } catch (_) { sections = []; }

    const choices = {
        width: [["inherit", "Use page width"], ["narrow", "Narrow"], ["standard", "Standard"], ["wide", "Wide"], ["full", "Full width"]],
        layout: [["single", "Single column"], ["two", "Two equal columns"], ["wide_left", "Two columns - wide left"], ["wide_right", "Two columns - wide right"], ["three", "Three columns"], ["four", "Four columns"]],
        background: [["default", "Page background"], ["surface", "Raised surface"], ["alternate", "Alternate surface"]],
        block_type: [["small_heading", "Small heading"], ["heading", "Heading"], ["text", "Text"], ["action", "Button or link"], ["card_group", "Card group"]],
        audience: [["everyone", "Everyone"], ["visitors", "Signed-out visitors"], ["signed_in", "Signed-in participants"]],
        destination: [["none", "No destination"], ["register", "Sign-up page"], ["login", "Login page"], ["account", "Participant account"]],
        style: [["default", "Standard"], ["primary", "Primary button"], ["secondary", "Secondary button"], ["link", "Text link"]],
    };
    const columnCounts = {single: 1, two: 2, wide_left: 2, wide_right: 2, three: 3, four: 4};
    const labels = {small_heading: "Small heading", heading: "Heading", text: "Text", action: "Button or link", card_group: "Card group"};

    const el = (tag, className = "", text = "") => {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text) node.textContent = text;
        return node;
    };
    const button = (text, action, danger = false) => {
        const node = el("button", `button${danger ? " page-editor-danger" : ""}`, text);
        node.type = "button";
        node.dataset.action = action;
        return node;
    };
    const input = (key, value = "", type = "text") => {
        const node = type === "textarea" ? el("textarea") : el("input");
        if (type !== "textarea") node.type = type;
        if (type === "checkbox") node.checked = value !== false;
        else node.value = value || "";
        node.dataset.key = key;
        return node;
    };
    const field = (label, key, value, type = "text", wide = false) => {
        const wrapper = el("label", `page-editor-field${wide ? " page-editor-field-wide" : ""}`, label);
        wrapper.append(input(key, value, type));
        return wrapper;
    };
    const selectField = (label, key, value, options) => {
        const wrapper = el("label", "page-editor-field", label);
        const select = el("select");
        select.dataset.key = key;
        options.forEach(([optionValue, optionLabel]) => {
            const option = el("option", "", optionLabel);
            option.value = optionValue;
            option.selected = value === optionValue;
            select.append(option);
        });
        wrapper.append(select);
        return wrapper;
    };
    const checkboxField = (label, key, value) => {
        const wrapper = el("label", "page-editor-field page-editor-checkbox");
        wrapper.append(input(key, value, "checkbox"), el("span", "page-editor-checkbox-label", label));
        return wrapper;
    };
    const actions = (kind, index, total) => {
        const wrapper = el("span", "page-editor-summary-actions");
        const up = button("↑", `${kind}-up`);
        const down = button("↓", `${kind}-down`);
        up.disabled = index === 0;
        down.disabled = index === total - 1;
        wrapper.append(up, down, button("×", `remove-${kind}`, true));
        return wrapper;
    };
    const summary = (title, kind, index, total) => {
        const row = el("summary");
        const handle = el("span", "page-editor-drag-handle", "☰");
        handle.draggable = true;
        row.append(handle, el("span", "page-editor-summary-title", title), actions(kind, index, total));
        return row;
    };

    const readCards = (blockPanel) => [...blockPanel.querySelectorAll(":scope .page-card-list > .page-card-editor")].map((card) => ({
        id: card.dataset.id ? Number(card.dataset.id) : null,
        heading: card.querySelector('[data-key="heading"]').value,
        description: card.querySelector('[data-key="description"]').value,
    }));
    const read = () => [...list.querySelectorAll(":scope > .page-section-editor")].map((sectionPanel) => ({
        id: sectionPanel.dataset.id ? Number(sectionPanel.dataset.id) : null,
        name: sectionPanel.querySelector(':scope > .page-section-body [data-key="name"]').value.trim() || "Section",
        is_visible: sectionPanel.querySelector(':scope > .page-section-body [data-key="is_visible"]').checked,
        width: sectionPanel.querySelector(':scope > .page-section-body [data-key="width"]').value,
        layout: sectionPanel.querySelector(':scope > .page-section-body [data-key="layout"]').value,
        background: sectionPanel.querySelector(':scope > .page-section-body [data-key="background"]').value,
        full_bleed_background: sectionPanel.querySelector(':scope > .page-section-body [data-key="full_bleed_background"]').checked,
        blocks: [...sectionPanel.querySelectorAll(":scope .page-block-list > .page-block-editor")].map((blockPanel) => ({
            id: blockPanel.dataset.id ? Number(blockPanel.dataset.id) : null,
            column: Number(blockPanel.closest(".page-column-editor").dataset.column),
            is_visible: blockPanel.querySelector('[data-key="is_visible"]').checked,
            block_type: blockPanel.querySelector('[data-key="block_type"]').value,
            content: blockPanel.querySelector('[data-key="content"]').value,
            audience: blockPanel.querySelector('[data-key="audience"]')?.value || "everyone",
            destination: blockPanel.querySelector('[data-key="destination"]')?.value || "none",
            style: blockPanel.querySelector('[data-key="style"]')?.value || "default",
            items: readCards(blockPanel),
        })),
    }));
    const sync = () => { sections = read(); payload.value = JSON.stringify(sections); };

    const renderCard = (card, index, total) => {
        const panel = el("details", "page-card-editor");
        panel.dataset.id = card.id || "";
        panel.append(summary(`${index + 1}. ${card.heading || "Untitled card"}`, "card", index, total));
        const body = el("div", "page-card-body page-editor-grid");
        body.append(field("Heading", "heading", card.heading), field("Description", "description", card.description, "textarea", true));
        panel.append(body);
        return panel;
    };
    const renderBlock = (block, index, total) => {
        const panel = el("details", "page-block-editor");
        panel.dataset.id = block.id || "";
        panel.append(summary(`${index + 1}. ${labels[block.block_type] || "Content block"}`, "block", index, total));
        const body = el("div", "page-block-body");
        const grid = el("div", "page-editor-grid");
        grid.append(selectField("Block type", "block_type", block.block_type || "text", choices.block_type), checkboxField("Visible publicly", "is_visible", block.is_visible));
        const contentLabel = block.block_type === "action" ? "Button or link label" : block.block_type === "card_group" ? "Optional group heading" : "Content";
        grid.append(field(contentLabel, "content", block.content, block.block_type === "text" ? "textarea" : "text", true));
        if (block.block_type === "action") {
            grid.append(selectField("Audience", "audience", block.audience || "everyone", choices.audience), selectField("Destination", "destination", block.destination || "none", choices.destination), selectField("Appearance", "style", block.style || "default", choices.style));
        }
        body.append(grid);
        if (block.block_type === "card_group") {
            const cards = el("details", "page-cards");
            const cardsSummary = el("summary");
            cardsSummary.append(el("span", "", `Cards (${(block.items || []).length})`), button("Add card", "add-card"));
            cards.append(cardsSummary);
            const cardList = el("div", "page-card-list");
            (block.items || []).forEach((card, cardIndex) => cardList.append(renderCard(card, cardIndex, block.items.length)));
            cards.append(cardList);
            body.append(cards);
        }
        panel.append(body);
        return panel;
    };
    const render = () => {
        list.replaceChildren();
        if (!sections.length) list.append(el("p", "page-editor-empty", "This page has no sections yet."));
        sections.forEach((section, sectionIndex) => {
            const panel = el("details", "page-section-editor");
            panel.dataset.id = section.id || "";
            panel.append(summary(`${sectionIndex + 1}. ${section.name || "Section"}${section.is_visible === false ? " - Hidden" : ""}`, "section", sectionIndex, sections.length));
            const body = el("div", "page-section-body");
            const settings = el("div", "page-editor-grid");
            settings.append(
                field("Section name", "name", section.name || "Section", "text", true),
                checkboxField("Visible publicly", "is_visible", section.is_visible),
                selectField("Content width", "width", section.width || "inherit", choices.width),
                selectField("Column layout", "layout", section.layout || "single", choices.layout),
                selectField("Background", "background", section.background || "default", choices.background),
                checkboxField("Extend background to screen edges", "full_bleed_background", section.full_bleed_background)
            );
            body.append(settings);
            const columns = el("div", `page-columns-editor page-columns-${section.layout || "single"}`);
            const columnCount = columnCounts[section.layout] || 1;
            for (let column = 0; column < columnCount; column += 1) {
                const blocks = (section.blocks || [])
                    .map((block, index) => ({block, index}))
                    .filter(({block}) => Number(block.column || 0) === column);
                const columnPanel = el("section", "page-column-editor");
                columnPanel.dataset.column = column;
                const header = el("div", "page-column-header");
                const columnActions = el("span", "page-editor-summary-actions");
                const addBlock = button("Add block", "add-block");
                addBlock.classList.add("page-editor-add-item");
                columnActions.append(addBlock);
                header.append(el("strong", "page-editor-summary-title", `Column ${column + 1} (${blocks.length} blocks)`), columnActions);
                columnPanel.append(header);
                const blockList = el("div", "page-block-list");
                blocks.forEach(({block, index}, columnIndex) => {
                    const blockPanel = renderBlock(block, columnIndex, blocks.length);
                    blockPanel.dataset.blockIndex = index;
                    blockList.append(blockPanel);
                });
                columnPanel.append(blockList);
                columns.append(columnPanel);
            }
            body.append(columns);
            panel.append(body);
            list.append(panel);
        });
        payload.value = JSON.stringify(sections);
    };

    const preserve = (mutate, syncBefore = true) => {
        if (syncBefore) sync();
        const open = [...list.querySelectorAll("details")].map((node, index) => node.open ? index : -1).filter((index) => index >= 0);
        const scroll = window.scrollY;
        mutate();
        render();
        [...list.querySelectorAll("details")].forEach((node, index) => { node.open = open.includes(index); });
        window.scrollTo(0, scroll);
        sync();
    };
    const capturePageState = () => ({
        openPanels: [...list.querySelectorAll("details")].map((node) => node.open),
        scrollX: window.scrollX,
        scrollY: window.scrollY,
    });
    const savePageState = () => {
        try {
            sessionStorage.setItem(stateStorageKey, JSON.stringify(capturePageState()));
        } catch (_) {
            // The editor still submits normally if browser storage is unavailable.
        }
    };
    const restorePageState = () => {
        let savedState = null;
        try {
            savedState = JSON.parse(sessionStorage.getItem(stateStorageKey) || "null");
            sessionStorage.removeItem(stateStorageKey);
        } catch (_) {
            savedState = null;
        }
        if (!savedState) return;
        [...list.querySelectorAll("details")].forEach((node, index) => {
            node.open = savedState.openPanels?.[index] === true;
        });
        requestAnimationFrame(() => requestAnimationFrame(() => {
            window.scrollTo(savedState.scrollX || 0, savedState.scrollY || 0);
        }));
    };
    const persistRemoval = async (type, id) => {
        if (!id) return true;
        const token = form.querySelector('[name="csrfmiddlewaretoken"]')?.value;
        const url = editor.dataset.removeUrl.replace("CONTENT_TYPE", type).replace(/0\/$/, `${id}/`);
        return (await fetch(url, {method: "POST", headers: {"X-CSRFToken": token, "X-Requested-With": "XMLHttpRequest"}, credentials: "same-origin"})).ok;
    };

    list.addEventListener("click", async (event) => {
        const control = event.target.closest("[data-action]");
        if (!control) return;
        event.preventDefault();
        sync();
        const action = control.dataset.action;
        const sectionPanel = control.closest(".page-section-editor");
        const sectionIndex = [...list.children].indexOf(sectionPanel);
        const section = sections[sectionIndex];
        const columnPanel = control.closest(".page-column-editor");
        const blockPanel = control.closest(".page-block-editor");
        const blockIndex = blockPanel ? Number(blockPanel.dataset.blockIndex) : -1;
        const block = blockPanel ? section.blocks[blockIndex] : null;
        const cardPanel = control.closest(".page-card-editor");
        const cardIndex = cardPanel && block ? [...cardPanel.parentElement.children].indexOf(cardPanel) : -1;

        if (action === "add-block") preserve(() => section.blocks.push({column: Number(columnPanel.dataset.column), is_visible: true, block_type: "text", content: "", audience: "everyone", destination: "none", style: "default", items: []}), false);
        else if (action === "add-card") preserve(() => block.items.push({heading: "", description: ""}), false);
        else if (action.endsWith("-up") || action.endsWith("-down")) {
            const delta = action.endsWith("-up") ? -1 : 1;
            preserve(() => {
                if (action.startsWith("section")) [sections[sectionIndex], sections[sectionIndex + delta]] = [sections[sectionIndex + delta], sections[sectionIndex]];
                else if (action.startsWith("block")) {
                    const columnIndices = section.blocks
                        .map((candidate, index) => ({candidate, index}))
                        .filter(({candidate}) => Number(candidate.column || 0) === Number(block.column || 0))
                        .map(({index}) => index);
                    const position = columnIndices.indexOf(blockIndex);
                    const otherIndex = columnIndices[position + delta];
                    [section.blocks[blockIndex], section.blocks[otherIndex]] = [section.blocks[otherIndex], section.blocks[blockIndex]];
                }
                else [block.items[cardIndex], block.items[cardIndex + delta]] = [block.items[cardIndex + delta], block.items[cardIndex]];
            }, false);
        } else if (action.startsWith("remove-")) {
            const type = action.replace("remove-", "");
            const subject = type === "section" ? section : type === "block" ? block : block.items[cardIndex];
            if (!window.confirm(`Permanently remove this ${type}? This takes effect immediately and cannot be undone.`)) return;
            if (!(await persistRemoval(type, subject.id))) return window.alert(`The ${type} could not be removed.`);
            preserve(() => {
                if (type === "section") sections.splice(sectionIndex, 1);
                else if (type === "block") section.blocks.splice(blockIndex, 1);
                else block.items.splice(cardIndex, 1);
            }, false);
            baseline = JSON.stringify(sections);
        }
    });
    list.addEventListener("change", (event) => {
        if (event.target.dataset.key === "block_type" || event.target.dataset.key === "layout") preserve(() => {});
        else sync();
    });
    list.addEventListener("input", (event) => {
        sync();
        if (event.target.dataset.key === "name") {
            const sectionPanel = event.target.closest(".page-section-editor");
            const sectionIndex = [...list.children].indexOf(sectionPanel);
            const title = sectionPanel.querySelector(":scope > summary .page-editor-summary-title");
            if (title) title.textContent = `${sectionIndex + 1}. ${event.target.value.trim() || "Section"}${sections[sectionIndex].is_visible === false ? " - Hidden" : ""}`;
        }
    });
    editor.querySelector("[data-add-section]").addEventListener("click", () => preserve(() => sections.push({name: "Section", is_visible: true, width: "inherit", layout: "single", background: "default", full_bleed_background: false, blocks: []})));

    form.addEventListener("submit", (event) => {
        sync();
        submitting = true;
        if (event.submitter?.name === "_continue") savePageState();
        else {
            try { sessionStorage.removeItem(stateStorageKey); } catch (_) {}
        }
    });
    window.addEventListener("beforeunload", (event) => {
        sync();
        if (!submitting && JSON.stringify(sections) !== baseline) { event.preventDefault(); event.returnValue = ""; }
    });
    render();
    restorePageState();
    sync();
    baseline = JSON.stringify(sections);
});
