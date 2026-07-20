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
        block_type: [["small_heading", "Small heading"], ["heading", "Heading"], ["text", "Text"], ["action", "Button or link"], ["card_group", "Card group"], ["image", "Image"], ["gallery", "Gallery"]],
        audience: [["everyone", "Everyone"], ["visitors", "Signed-out visitors"], ["signed_in", "Signed-in participants"], ["hidden", "Hidden"]],
        destination: [["none", "No destination"], ["register", "Sign-up page"], ["login", "Login page"], ["account", "Participant account"]],
        style: [["default", "Standard"], ["primary", "Primary button"], ["secondary", "Secondary button"], ["link", "Text link"]],
        image_fit: [["cover", "Crop to fill"], ["contain", "Show whole image"]],
        image_height: [["standard", "Standard - maximum 24rem"], ["natural", "Natural proportions"], ["short", "Short banner - 12rem"], ["tall", "Tall banner - 32rem"], ["custom", "Custom height"]],
        image_position: [["left top", "Top left"], ["center top", "Top centre"], ["right top", "Top right"], ["left center", "Centre left"], ["center center", "Centre"], ["right center", "Centre right"], ["left bottom", "Bottom left"], ["center bottom", "Bottom centre"], ["right bottom", "Bottom right"]],
        card_columns: [["auto", "Automatic wrapping"], ["1", "1 card per row"], ["2", "2 cards per row"], ["3", "3 cards per row"], ["4", "4 cards per row"]],
    };
    let imageLibrary = [];
    const columnCounts = {single: 1, two: 2, wide_left: 2, wide_right: 2, three: 3, four: 4};
    const labels = {small_heading: "Small heading", heading: "Heading", text: "Text", action: "Button or link", card_group: "Card group", image: "Image", gallery: "Gallery"};

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
        if (type === "checkbox" || type === "radio") node.checked = value !== false;
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
            option.selected = String(value ?? "") === String(optionValue);
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
    const addMenu = el("div", "page-editor-add-menu");
    addMenu.setAttribute("role", "menu");
    addMenu.hidden = true;
    document.body.append(addMenu);
    let addMenuTrigger = null;
    const closeAddMenu = (restoreFocus = false) => {
        addMenu.hidden = true;
        if (restoreFocus) addMenuTrigger?.focus();
        addMenuTrigger?.setAttribute("aria-expanded", "false");
        addMenuTrigger = null;
        addMenu.replaceChildren();
    };
    const openAddMenu = (trigger, options, onSelect) => {
        closeAddMenu();
        addMenuTrigger = trigger;
        trigger.setAttribute("aria-expanded", "true");
        options.forEach(([value, label]) => {
            const option = el("button", "page-editor-add-menu-item", label);
            option.type = "button";
            option.setAttribute("role", "menuitem");
            option.addEventListener("click", () => { closeAddMenu(); onSelect(value); });
            addMenu.append(option);
        });
        addMenu.hidden = false;
        const rect = trigger.getBoundingClientRect();
        const menuWidth = Math.max(190, addMenu.getBoundingClientRect().width);
        addMenu.style.left = `${Math.max(8, Math.min(window.innerWidth - menuWidth - 8, rect.right - menuWidth))}px`;
        addMenu.style.top = `${Math.max(8, Math.min(window.innerHeight - addMenu.getBoundingClientRect().height - 8, rect.bottom + 4))}px`;
        addMenu.querySelector("button")?.focus();
    };
    const splitAddButton = (main, label, options, onSelect) => {
        const wrapper = el("span", "page-editor-split-button");
        main.parentNode?.insertBefore(wrapper, main);
        wrapper.append(main);
        const toggle = el("button", "button page-editor-split-toggle", "▾");
        toggle.type = "button";
        toggle.setAttribute("aria-label", `Choose ${label.toLowerCase()} type`);
        toggle.setAttribute("aria-haspopup", "menu");
        toggle.setAttribute("aria-expanded", "false");
        toggle.addEventListener("click", (event) => {
            event.preventDefault();
            event.stopPropagation();
            if (!addMenu.hidden && addMenuTrigger === toggle) { closeAddMenu(); toggle.blur(); }
            else openAddMenu(toggle, options, onSelect);
        });
        wrapper.append(toggle);
        return wrapper;
    };
    document.addEventListener("pointerdown", (event) => {
        if (!addMenu.hidden && !addMenu.contains(event.target) && event.target !== addMenuTrigger) closeAddMenu();
    });
    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && !addMenu.hidden) { event.preventDefault(); closeAddMenu(true); }
    });
    const removeConfirmation = el("div", "page-editor-remove-confirmation");
    removeConfirmation.hidden = true;
    removeConfirmation.setAttribute("role", "dialog");
    removeConfirmation.setAttribute("aria-modal", "false");
    document.body.append(removeConfirmation);
    let resolveRemoveConfirmation = null;
    const closeRemoveConfirmation = (confirmed = false) => {
        if (removeConfirmation.hidden) return;
        removeConfirmation.hidden = true;
        removeConfirmation.replaceChildren();
        const resolve = resolveRemoveConfirmation;
        resolveRemoveConfirmation = null;
        resolve?.(confirmed);
    };
    const confirmRemoval = (trigger, type) => new Promise((resolve) => {
        closeRemoveConfirmation(false);
        resolveRemoveConfirmation = resolve;
        const message = el("strong", "", `Remove this ${type}?`);
        const detail = el("span", "", "This takes effect immediately and cannot be undone.");
        const controls = el("span", "page-editor-remove-confirmation-actions");
        const cancel = el("button", "button", "Cancel");
        cancel.type = "button";
        const confirm = el("button", "button page-editor-confirm-remove", "Remove");
        confirm.type = "button";
        cancel.addEventListener("click", () => closeRemoveConfirmation(false));
        confirm.addEventListener("click", () => closeRemoveConfirmation(true));
        controls.append(cancel, confirm);
        removeConfirmation.append(message, detail, controls);
        removeConfirmation.hidden = false;
        const rect = trigger.getBoundingClientRect();
        const popoverRect = removeConfirmation.getBoundingClientRect();
        const below = rect.bottom + 6;
        const top = below + popoverRect.height <= window.innerHeight - 8
            ? below : Math.max(8, rect.top - popoverRect.height - 6);
        removeConfirmation.style.top = `${top}px`;
        removeConfirmation.style.left = `${Math.max(8, Math.min(window.innerWidth - popoverRect.width - 8, rect.right - popoverRect.width))}px`;
        cancel.focus();
    });
    document.addEventListener("pointerdown", (event) => {
        if (!removeConfirmation.hidden && !removeConfirmation.contains(event.target) && !event.target.closest(".page-editor-remove-icon")) closeRemoveConfirmation(false);
    });
    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && !removeConfirmation.hidden) { event.preventDefault(); closeRemoveConfirmation(false); }
    });
    const imageName = (id) => imageLibrary.find((image) => String(image.id) === String(id))?.name || "Selected image";
    const imagePickerField = (label, key, value, multiple = false) => {
        const wrapper = el("div", "page-editor-field page-editor-field-wide page-image-picker-field");
        wrapper.append(el("span", "page-image-picker-label", label));
        const hidden = input(key, multiple ? JSON.stringify(value || []) : (value || ""), "hidden");
        const preview = el("div", "page-image-picker-preview");
        const renderPreview = () => {
            preview.replaceChildren();
            const ids = multiple ? (JSON.parse(hidden.value || "[]")) : (hidden.value ? [hidden.value] : []);
            if (!ids.length) preview.append(el("span", "page-image-picker-empty", "No image selected"));
            ids.forEach((entry) => {
                const id = multiple ? entry.image : entry;
                const image = imageLibrary.find((candidate) => String(candidate.id) === String(id));
                const item = el("span", "page-image-picker-item");
                if (image) { const thumbnail = el("img"); thumbnail.src = image.url; thumbnail.alt = ""; item.append(thumbnail); }
                item.append(el("strong", "", image?.name || imageName(id)));
                preview.append(item);
            });
        };
        const choose = button(multiple ? "Choose gallery images" : "Select image", "choose-images");
        choose.dataset.multiple = multiple ? "true" : "false";
        wrapper.append(hidden, preview, choose);
        requestAnimationFrame(renderPreview);
        return wrapper;
    };
    const actions = (kind, index, total) => {
        const wrapper = el("span", "page-editor-summary-actions");
        const up = button("", `${kind}-up`);
        const down = button("", `${kind}-down`);
        up.classList.add("page-editor-move-icon", "is-up");
        down.classList.add("page-editor-move-icon", "is-down");
        up.setAttribute("aria-label", `Move ${kind} up`);
        down.setAttribute("aria-label", `Move ${kind} down`);
        [up, down].forEach((control) => {
            const icon = document.createElementNS("http://www.w3.org/2000/svg", "svg");
            icon.setAttribute("viewBox", "0 0 16 16");
            icon.setAttribute("aria-hidden", "true");
            const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
            path.setAttribute("d", "M8 13V3M3.5 7.5 8 3l4.5 4.5");
            icon.append(path);
            control.append(icon);
        });
        up.disabled = index === 0;
        down.disabled = index === total - 1;
        const remove = button("", `remove-${kind}`, true);
        remove.classList.add("page-editor-remove-icon");
        remove.setAttribute("aria-label", `Remove ${kind}`);
        wrapper.append(up, down, remove);
        return wrapper;
    };
    const summary = (title, kind, index, total, editableName = false) => {
        const row = el("summary");
        const handle = el("span", "page-editor-drag-handle", "☰");
        row.append(handle);
        if (editableName) {
            const edit = el("button", "page-editor-edit-name");
            edit.type = "button";
            edit.setAttribute("aria-label", "Edit section name");
            edit.innerHTML = '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="m3 11.5-.5 2 2-.5 7.8-7.8-1.5-1.5L3 11.5Z"/><path d="m9.8 4.7 1.5 1.5"/></svg>';
            row.append(edit);
        }
        row.append(el("span", "page-editor-summary-title", title), actions(kind, index, total));
        return row;
    };
    const updateSectionNameDirty = (sectionPanel) => {
        const summaryRow = sectionPanel.querySelector(":scope > summary");
        const title = summaryRow?.querySelector(":scope > .page-editor-summary-title");
        const edit = summaryRow?.querySelector(":scope > .page-editor-edit-name");
        let badge = summaryRow?.querySelector(":scope > .page-editor-unsaved-name");
        const dirty = (sectionPanel.dataset.name || "Section") !== (sectionPanel.dataset.savedName || "Section");
        sectionPanel.classList.toggle("has-unsaved-name", dirty);
        edit?.classList.toggle("is-unsaved", dirty);
        if (dirty && !badge && title) {
            badge = el("span", "page-editor-unsaved-name", "Unsaved");
            title.after(badge);
        } else if (!dirty) badge?.remove();
    };

    const readCards = (blockPanel) => [...blockPanel.querySelectorAll(":scope .page-card-list > .page-card-editor")].map((card) => ({
        id: card.dataset.id ? Number(card.dataset.id) : null,
        heading: card.querySelector('[data-key="heading"]').value,
        description: card.querySelector('[data-key="description"]').value,
    }));
    const readGallery = (blockPanel) => [...blockPanel.querySelectorAll(":scope .page-gallery-image")].map((row) => ({
        image: Number(row.dataset.image),
        alternative_text: row.querySelector('[data-key="gallery_alt"]').value,
        caption: row.querySelector('[data-key="gallery_caption"]').value,
    }));
    const read = () => [...list.querySelectorAll(":scope > .page-section-editor")].map((sectionPanel) => ({
        id: sectionPanel.dataset.id ? Number(sectionPanel.dataset.id) : null,
        name: sectionPanel.dataset.name?.trim() || "Section",
        _saved_name: sectionPanel.dataset.savedName || sectionPanel.dataset.name || "Section",
        is_visible: sectionPanel.querySelector(':scope > .page-section-body [data-key="is_visible"]').checked,
        width: sectionPanel.querySelector(':scope > .page-section-body [data-key="width"]').value,
        layout: sectionPanel.querySelector(':scope > .page-section-body [data-key="layout"]').value,
        background: sectionPanel.querySelector(':scope > .page-section-body [data-key="background"]').value,
        full_bleed_background: sectionPanel.querySelector(':scope > .page-section-body [data-key="full_bleed_background"]').checked,
        blocks: [...sectionPanel.querySelectorAll(":scope .page-block-list > .page-block-editor")].map((blockPanel) => ({
            id: blockPanel.dataset.id ? Number(blockPanel.dataset.id) : null,
            column: Number(blockPanel.closest(".page-column-editor").dataset.column),
            is_visible: blockPanel.querySelector('[data-key="audience"]').value !== "hidden",
            block_type: blockPanel.querySelector('[data-key="block_type"]').value,
            content: blockPanel.querySelector('[data-key="content"]')?.value || "",
            audience: blockPanel.querySelector('[data-key="audience"]').value === "hidden" ? "everyone" : blockPanel.querySelector('[data-key="audience"]').value,
            destination: blockPanel.querySelector('[data-key="destination"]')?.value || "none",
            style: blockPanel.querySelector('[data-key="style"]')?.value || "default",
            card_columns: blockPanel.querySelector('[data-key="card_columns"]')?.value || "auto",
            image_asset: blockPanel.querySelector('[data-key="image_asset"]')?.value || null,
            image_alt: blockPanel.querySelector('[data-key="image_alt"]')?.value || "",
            image_fit: blockPanel.querySelector('[data-key="image_fit"]')?.value || "cover",
            image_height: blockPanel.querySelector('[data-key="image_height"]')?.value || "standard",
            image_custom_height: Number(blockPanel.querySelector('[data-key="image_custom_height"]')?.value || 24),
            image_position: blockPanel.querySelector('[data-key="image_position"]')?.value || "center center",
            gallery_auto_scroll: blockPanel.querySelector('[data-key="gallery_auto_scroll"]')?.checked || false,
            gallery_scroll_speed: Number(blockPanel.querySelector('[data-key="gallery_scroll_speed"]')?.value || 5),
            gallery_loop: blockPanel.querySelector('[data-key="gallery_loop"]')?.checked ?? true,
            gallery_show_controls: blockPanel.querySelector('[data-key="gallery_show_controls"]')?.checked ?? true,
            gallery_show_captions: blockPanel.querySelector('[data-key="gallery_show_captions"]')?.checked ?? true,
            gallery_expandable: blockPanel.querySelector('[data-key="gallery_expandable"]')?.checked ?? true,
            gallery_images: readGallery(blockPanel),
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
    const newBlock = (blockType, column) => ({
        column, is_visible: true, block_type: blockType, content: "", audience: "everyone",
        destination: "none", style: "default", card_columns: "auto", image_asset: null,
        image_alt: "", image_fit: "cover", image_height: "standard", image_custom_height: 24,
        image_position: "center center", gallery_auto_scroll: false, gallery_scroll_speed: 5,
        gallery_loop: true, gallery_show_controls: true, gallery_show_captions: true,
        gallery_expandable: true, gallery_images: [], items: [],
    });
    const newSection = (layout = "single") => ({
        name: "Section", is_visible: true, width: "inherit", layout,
        background: "default", full_bleed_background: false, blocks: [],
    });
    const renderBlock = (block, index, total) => {
        const panel = el("details", "page-block-editor");
        panel.dataset.id = block.id || "";
        panel.append(summary(`${index + 1}. ${labels[block.block_type] || "Content block"}`, "block", index, total));
        const body = el("div", "page-block-body");
        const grid = el("div", "page-editor-grid");
        grid.append(
            selectField("Block type", "block_type", block.block_type || "text", choices.block_type),
            selectField("Audience", "audience", block.is_visible === false ? "hidden" : block.audience || "everyone", choices.audience)
        );
        if (block.block_type === "image") {
            grid.append(
                imagePickerField("Image", "image_asset", block.image_asset || ""),
                field("Alternative text", "image_alt", block.image_alt || "", "text", true),
                selectField("Image fit", "image_fit", block.image_fit || "cover", choices.image_fit),
                selectField("Height", "image_height", block.image_height || "standard", choices.image_height),
                field("Custom height (rem)", "image_custom_height", block.image_custom_height || 24, "number"),
                selectField("Focal position", "image_position", block.image_position || "center center", choices.image_position)
            );
        } else if (block.block_type === "gallery") {
            grid.append(
                imagePickerField("Gallery images", "gallery_selection", block.gallery_images || [], true),
                checkboxField("Scroll automatically", "gallery_auto_scroll", block.gallery_auto_scroll),
                field("Scroll interval (seconds)", "gallery_scroll_speed", block.gallery_scroll_speed || 5, "number"),
                checkboxField("Loop continuously", "gallery_loop", block.gallery_loop),
                checkboxField("Show navigation controls", "gallery_show_controls", block.gallery_show_controls),
                checkboxField("Show captions", "gallery_show_captions", block.gallery_show_captions),
                checkboxField("Allow expanded view", "gallery_expandable", block.gallery_expandable)
            );
        } else {
            const contentLabel = block.block_type === "action" ? "Button or link label" : block.block_type === "card_group" ? "Optional group heading" : "Content";
            grid.append(field(contentLabel, "content", block.content, block.block_type === "text" ? "textarea" : "text", true));
            if (block.block_type === "card_group") grid.append(selectField("Cards per row", "card_columns", block.card_columns || "auto", choices.card_columns));
        }
        if (block.block_type === "action") {
            grid.append(selectField("Destination", "destination", block.destination || "none", choices.destination), selectField("Appearance", "style", block.style || "default", choices.style));
        }
        body.append(grid);
        if (block.block_type === "gallery") {
            const galleryList = el("div", "page-gallery-list");
            (block.gallery_images || []).forEach((item, galleryIndex) => {
                const row = el("div", "page-gallery-image page-editor-grid");
                row.dataset.image = item.image;
                const heading = el("div", "page-gallery-image-heading page-editor-field-wide");
                heading.append(el("strong", "", `${galleryIndex + 1}. ${imageName(item.image)}`));
                row.append(heading, field("Alternative text", "gallery_alt", item.alternative_text || ""), field("Caption", "gallery_caption", item.caption || ""));
                galleryList.append(row);
            });
            body.append(galleryList);
        }
        if (block.block_type === "card_group") {
            const cards = el("details", "page-cards");
            const cardsSummary = el("summary");
            const cardsTitle = el("span", "page-editor-summary-title", `Cards (${(block.items || []).length})`);
            const cardsActions = el("span", "page-editor-summary-actions");
            const addCard = button("Add card", "add-card");
            addCard.classList.add("page-editor-add-item");
            cardsActions.append(addCard);
            cardsSummary.append(cardsTitle, cardsActions);
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
            panel.dataset.name = section.name || "Section";
            panel.dataset.savedName = section._saved_name || section.name || "Section";
            panel.append(summary(`${section.name || "Section"}${section.is_visible === false ? " - Hidden" : ""}`, "section", sectionIndex, sections.length, true));
            const body = el("div", "page-section-body");
            const settings = el("div", "page-editor-grid");
            settings.append(
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
                splitAddButton(addBlock, "Block", choices.block_type, (blockType) => {
                    sync();
                    const currentSectionPanel = columnPanel.closest(".page-section-editor");
                    const currentSection = sections[[...list.children].indexOf(currentSectionPanel)];
                    preserve(() => currentSection.blocks.push(newBlock(blockType, column)), false);
                });
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
            updateSectionNameDirty(panel);
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

    const libraryDialog = el("dialog", "page-image-library-dialog");
    libraryDialog.innerHTML = '<div class="page-image-library-modal"><header><div><h2>Choose images</h2><p>Select from the shared image library.</p></div><button type="button" class="page-image-library-close" aria-label="Close">&times;</button></header><div class="page-image-library-grid"></div><footer><button type="button" class="button page-image-library-apply">Use selected images</button></footer></div>';
    document.body.append(libraryDialog);
    const libraryGrid = libraryDialog.querySelector(".page-image-library-grid");
    const libraryApply = libraryDialog.querySelector(".page-image-library-apply");
    let activePicker = null;
    let activePickerMultiple = false;
    const openImagePicker = (picker, multiple) => {
        activePicker = picker;
        activePickerMultiple = multiple;
        const hidden = picker.querySelector('[data-key]');
        const selected = new Set(multiple
            ? JSON.parse(hidden.value || "[]").map((entry) => String(entry.image))
            : (hidden.value ? [String(hidden.value)] : []));
        libraryGrid.replaceChildren();
        imageLibrary.forEach((image) => {
            const item = el("label", "page-image-library-item");
            const choice = input("", selected.has(String(image.id)), multiple ? "checkbox" : "radio");
            choice.removeAttribute("data-key");
            choice.name = "page-image-library-choice";
            choice.value = image.id;
            const thumbnail = el("img"); thumbnail.src = image.url; thumbnail.alt = "";
            item.append(choice, thumbnail, el("strong", "", image.name), el("small", "", `${image.type} · ${image.dimensions}`));
            libraryGrid.append(item);
        });
        libraryApply.textContent = multiple ? "Use selected images" : "Use selected image";
        libraryDialog.showModal();
    };
    libraryApply.addEventListener("click", () => {
        const chosen = [...libraryGrid.querySelectorAll("input:checked")].map((choice) => Number(choice.value));
        if (!chosen.length) return;
        sync();
        const sectionPanel = activePicker.closest(".page-section-editor");
        const blockPanel = activePicker.closest(".page-block-editor");
        const section = sections[[...list.children].indexOf(sectionPanel)];
        const block = section.blocks[Number(blockPanel.dataset.blockIndex)];
        preserve(() => {
            if (activePickerMultiple) {
                const existing = new Map((block.gallery_images || []).map((item) => [Number(item.image), item]));
                block.gallery_images = chosen.map((id) => existing.get(id) || {image: id, alternative_text: "", caption: ""});
            } else block.image_asset = chosen[0];
        }, false);
        libraryDialog.close();
    });
    libraryDialog.querySelector(".page-image-library-close").addEventListener("click", () => libraryDialog.close());
    libraryDialog.addEventListener("click", (event) => { if (event.target === libraryDialog) libraryDialog.close(); });

    list.addEventListener("click", async (event) => {
        const control = event.target.closest("[data-action]");
        if (!control) return;
        event.preventDefault();
        sync();
        const action = control.dataset.action;
        if (action === "choose-images") {
            openImagePicker(control.closest(".page-image-picker-field"), control.dataset.multiple === "true");
            return;
        }
        const sectionPanel = control.closest(".page-section-editor");
        const sectionIndex = [...list.children].indexOf(sectionPanel);
        const section = sections[sectionIndex];
        const columnPanel = control.closest(".page-column-editor");
        const blockPanel = control.closest(".page-block-editor");
        const blockIndex = blockPanel ? Number(blockPanel.dataset.blockIndex) : -1;
        const block = blockPanel ? section.blocks[blockIndex] : null;
        const cardPanel = control.closest(".page-card-editor");
        const cardIndex = cardPanel && block ? [...cardPanel.parentElement.children].indexOf(cardPanel) : -1;

        if (action === "add-block") preserve(() => section.blocks.push(newBlock("text", Number(columnPanel.dataset.column))), false);
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
            if (!(await confirmRemoval(control, type))) return;
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
    });
    list.addEventListener("click", (event) => {
        const editable = event.target.closest(".page-section-editor > summary .page-editor-summary-title, .page-section-editor > summary .page-editor-edit-name");
        const title = editable?.closest("summary")?.querySelector(":scope > .page-editor-summary-title");
        if (!title || title.querySelector("input")) return;
        event.preventDefault();
        event.stopPropagation();
        const sectionPanel = title.closest(".page-section-editor");
        const originalName = sectionPanel.dataset.name || "Section";
        const editorInput = input("section_name_inline", originalName);
        editorInput.className = "page-editor-inline-name";
        title.replaceChildren(editorInput);
        const finish = (commit) => {
            if (!editorInput.isConnected) return;
            const name = commit ? editorInput.value.trim() || "Section" : originalName;
            sectionPanel.dataset.name = name;
            const sectionIndex = [...list.children].indexOf(sectionPanel);
            title.textContent = `${name}${sections[sectionIndex]?.is_visible === false ? " - Hidden" : ""}`;
            updateSectionNameDirty(sectionPanel);
            sync();
        };
        editorInput.addEventListener("click", (inputEvent) => inputEvent.stopPropagation());
        editorInput.addEventListener("keydown", (keyEvent) => {
            if (keyEvent.key === "Enter") {
                keyEvent.preventDefault();
                keyEvent.stopPropagation();
                finish(true);
            }
            if (keyEvent.key === "Escape") { keyEvent.preventDefault(); keyEvent.stopPropagation(); finish(false); }
        });
        editorInput.addEventListener("blur", () => finish(true), {once: true});
        editorInput.focus();
        editorInput.select();
    });
    editor.addEventListener("keydown", (event) => {
        if (event.key === "Enter" && event.target.matches('input:not([type="checkbox"]):not([type="radio"]):not([type="submit"])')) {
            event.preventDefault();
            event.target.blur();
        }
    });
    const addSectionButton = editor.querySelector("[data-add-section]");
    addSectionButton.addEventListener("click", () => preserve(() => sections.push(newSection())));
    splitAddButton(addSectionButton, "Section", choices.layout, (layout) => preserve(() => sections.push(newSection(layout))));

    let dragged = null;
    let pendingPickup = null;
    let suppressNextClick = false;
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const clearDropMarkers = () => list.querySelectorAll(".page-editor-live-destination, .page-editor-drop-zone, .page-editor-drop-target").forEach((node) => node.classList.remove("page-editor-live-destination", "page-editor-drop-zone", "page-editor-drop-target"));
    const animateReflow = (positions, panels) => {
        if (reducedMotion) return;
        panels.forEach((panel) => {
            if (panel === dragged?.panel || !positions.has(panel)) return;
            const previousTop = positions.get(panel);
            const nextTop = panel.getBoundingClientRect().top;
            const delta = previousTop - nextTop;
            if (!delta) return;
            panel.style.transition = "none";
            panel.style.transform = `translateY(${delta}px)`;
            requestAnimationFrame(() => {
                panel.style.transition = "transform 170ms ease-out";
                panel.style.transform = "";
                window.setTimeout(() => { panel.style.transition = ""; }, 180);
            });
        });
    };
    const beginPickup = (summary, event) => {
        sync();
        const sectionPanel = summary.closest(".page-section-editor");
        const sectionIndex = [...list.children].indexOf(sectionPanel);
        const blockPanel = summary.closest(".page-block-editor");
        const cardPanel = summary.closest(".page-card-editor");
        if (cardPanel) {
            const blockIndex = Number(blockPanel.dataset.blockIndex);
            const cardIndex = [...cardPanel.parentElement.children].indexOf(cardPanel);
            dragged = {kind: "card", item: sections[sectionIndex].blocks[blockIndex].items[cardIndex], block: sections[sectionIndex].blocks[blockIndex], panel: cardPanel};
        } else if (blockPanel) {
            dragged = {kind: "block", item: sections[sectionIndex].blocks[Number(blockPanel.dataset.blockIndex)], panel: blockPanel};
        } else {
            dragged = {kind: "section", item: sections[sectionIndex], panel: sectionPanel};
        }
        dragged.originalParent = dragged.panel.parentElement;
        dragged.originalNext = dragged.panel.nextElementSibling;
        dragged.dropped = false;
        const title = dragged.panel.querySelector(":scope > summary .page-editor-summary-title")?.textContent?.trim() || "Move item";
        const placeholder = el("div", "page-editor-drag-placeholder");
        const panelHeight = dragged.panel.getBoundingClientRect().height;
        placeholder.style.height = `${Math.max(48, panelHeight)}px`;
        placeholder.append(el("strong", "", title));
        dragged.panel.after(placeholder);
        dragged.placeholder = placeholder;
        const preview = el("div", "page-editor-pointer-preview", title);
        document.body.append(preview);
        dragged.preview = preview;
        dragged.pointerId = event.pointerId;
        dragged.panel.classList.add("page-editor-dragging");
        document.documentElement.classList.add("page-editor-is-dragging");
        preview.style.transform = `translate(${event.clientX + 18}px, ${event.clientY + 18}px)`;
        dragged.panel.classList.add("page-editor-drag-source-lifted");
        suppressNextClick = true;
    };
    const liveDestination = (event) => {
        if (dragged.panel.contains(event.target)) return null;
        let container = null;
        let candidates = [];
        let panelSelector = "";
        if (dragged.kind === "section") {
            container = list;
            panelSelector = ".page-section-editor";
            candidates = [...list.querySelectorAll(":scope > .page-section-editor")];
        } else if (dragged.kind === "block") {
            container = event.target.closest(".page-column-editor")?.querySelector(":scope > .page-block-list");
            panelSelector = ".page-block-editor";
            if (container) candidates = [...container.querySelectorAll(":scope > .page-block-editor")];
        } else {
            container = event.target.closest(".page-card-list");
            panelSelector = ".page-card-editor";
            if (container !== dragged.panel.closest(".page-card-list")) return null;
            if (container) candidates = [...container.querySelectorAll(":scope > .page-card-editor")];
        }
        if (!container) return null;
        candidates = candidates.filter((panel) => panel !== dragged.panel);
        const measured = candidates.map((panel) => {
            const header = panel.querySelector(":scope > summary") || panel;
            const rect = header.getBoundingClientRect();
            return {panel, centre: rect.top + rect.height / 2};
        });
        const directTarget = event.target.closest(panelSelector);
        const directEntry = measured.find((entry) => entry.panel === directTarget);
        const targetEntry = directEntry || measured.reduce((closest, entry) => (
            !closest || Math.abs(event.clientY - entry.centre) < Math.abs(event.clientY - closest.centre) ? entry : closest
        ), null);
        const targetIndex = targetEntry ? measured.indexOf(targetEntry) : -1;
        const beforeTarget = targetEntry && event.clientY < targetEntry.centre;
        const next = beforeTarget ? targetEntry.panel : measured[targetIndex + 1]?.panel || null;
        return {container, next, target: targetEntry?.panel || null};
    };
    const movePickup = (event) => {
        if (!dragged) return false;
        const destination = liveDestination(event);
        if (!destination) return false;
        clearDropMarkers();
        const placementUnchanged = dragged.placeholder.parentElement === destination.container
            && dragged.placeholder.nextElementSibling === destination.next;
        const animatedPanels = [...list.querySelectorAll(
            dragged.kind === "section" ? ":scope > .page-section-editor"
                : dragged.kind === "block" ? ".page-block-editor" : ".page-card-editor"
        )];
        const positions = new Map(animatedPanels.map((panel) => [panel, panel.getBoundingClientRect().top]));
        destination.container.insertBefore(dragged.placeholder, destination.next);
        if (!placementUnchanged) animateReflow(positions, animatedPanels);
        dragged.placeholder.classList.add("page-editor-live-destination");
        destination.target?.classList.add("page-editor-drop-target");
        const zone = dragged.kind === "block"
            ? destination.container.closest(".page-column-editor")
            : dragged.kind === "card" ? destination.container.closest(".page-cards") : dragged.panel;
        zone?.classList.add("page-editor-drop-zone");
        return true;
    };
    const finishPickup = (commit) => {
        if (!dragged) return;
        dragged.preview?.remove();
        if (!commit) {
            dragged.originalParent.insertBefore(
                dragged.panel,
                dragged.originalNext?.parentElement === dragged.originalParent ? dragged.originalNext : null
            );
            dragged.panel.classList.remove("page-editor-drag-source-lifted");
            dragged.placeholder?.remove();
            dragged.panel.classList.remove("page-editor-dragging", "page-editor-drag-source-lifted");
            clearDropMarkers();
            document.documentElement.classList.remove("page-editor-is-dragging");
            dragged = null;
            return;
        }
        dragged.dropped = true;
        dragged.placeholder.before(dragged.panel);
        dragged.placeholder.remove();
        dragged.panel.classList.remove("page-editor-drag-source-lifted");
        clearDropMarkers();
        dragged.panel.classList.remove("page-editor-dragging");
        preserve(() => {});
        dragged = null;
        document.documentElement.classList.remove("page-editor-is-dragging");
    };
    list.addEventListener("pointerdown", (event) => {
        if (event.button !== 0 || dragged || pendingPickup) return;
        const summary = event.target.closest("summary");
        if (!summary || !summary.querySelector(":scope > .page-editor-drag-handle")) return;
        if (event.target.closest("input, textarea, select, button")) return;
        if (event.target.closest(".page-editor-summary-actions")) return;
        const immediate = Boolean(event.target.closest(".page-editor-drag-handle"));
        if (immediate) {
            event.preventDefault();
            beginPickup(summary, event);
            return;
        }
        pendingPickup = {
            summary, pointerId: event.pointerId, startX: event.clientX, startY: event.clientY,
        };
    });
    document.addEventListener("pointermove", (event) => {
        if (pendingPickup && event.pointerId === pendingPickup.pointerId) {
            if (Math.hypot(event.clientX - pendingPickup.startX, event.clientY - pendingPickup.startY) > 7) {
                const pickup = pendingPickup;
                pendingPickup = null;
                beginPickup(pickup.summary, event);
            } else {
                return;
            }
        }
        if (!dragged || event.pointerId !== dragged.pointerId) return;
        event.preventDefault();
        dragged.preview.style.transform = `translate(${event.clientX + 18}px, ${event.clientY + 18}px)`;
        const target = document.elementFromPoint(event.clientX, event.clientY);
        if (target) movePickup({target, clientY: event.clientY});
        const edge = 56;
        if (event.clientY < edge) window.scrollBy(0, -12);
        else if (event.clientY > window.innerHeight - edge) window.scrollBy(0, 12);
    }, {passive: false});
    const releasePickup = (event) => {
        if (pendingPickup && event.pointerId === pendingPickup.pointerId) {
            pendingPickup = null;
            return;
        }
        if (!dragged || event.pointerId !== dragged.pointerId) return;
        event.preventDefault();
        finishPickup(dragged.placeholder.classList.contains("page-editor-live-destination"));
    };
    document.addEventListener("pointerup", releasePickup);
    document.addEventListener("pointercancel", (event) => {
        if (pendingPickup && event.pointerId === pendingPickup.pointerId) {
            pendingPickup = null;
        }
        if (dragged && event.pointerId === dragged.pointerId) finishPickup(false);
    });
    list.addEventListener("click", (event) => {
        if (!suppressNextClick) return;
        suppressNextClick = false;
        event.preventDefault();
        event.stopImmediatePropagation();
    }, true);

    form.addEventListener("submit", (event) => {
        sync();
        submitting = event.submitter?.name !== "_continue" || form.dataset.adminSaveBypass === "true";
        if (event.submitter?.name === "_continue" && submitting) savePageState();
        else {
            try { sessionStorage.removeItem(stateStorageKey); } catch (_) {}
        }
    });
    form.addEventListener("rat-race:admin-save-success", (event) => {
        const savedValue = event.detail.document.querySelector("#id_page_builder_data")?.value;
        let savedSections = [];
        try { savedSections = JSON.parse(savedValue || "[]"); } catch (_) { return; }
        sections.forEach((section, sectionIndex) => {
            const savedSection = savedSections[sectionIndex];
            if (!savedSection) return;
            section.id = savedSection.id;
            section.blocks.forEach((block, blockIndex) => {
                const savedBlock = savedSection.blocks?.[blockIndex];
                if (!savedBlock) return;
                block.id = savedBlock.id;
                block.items.forEach((item, itemIndex) => {
                    item.id = savedBlock.items?.[itemIndex]?.id || null;
                });
            });
        });
        [...list.querySelectorAll(":scope > .page-section-editor")].forEach((sectionPanel, sectionIndex) => {
            const section = sections[sectionIndex];
            sectionPanel.dataset.id = section?.id || "";
            section._saved_name = savedSections[sectionIndex]?.name || section.name;
            sectionPanel.dataset.savedName = section._saved_name;
            updateSectionNameDirty(sectionPanel);
            [...sectionPanel.querySelectorAll(".page-block-list > .page-block-editor")].forEach((blockPanel) => {
                const blockIndex = Number(blockPanel.dataset.blockIndex);
                const block = section?.blocks?.[blockIndex];
                blockPanel.dataset.id = block?.id || "";
                [...blockPanel.querySelectorAll(".page-card-list > .page-card-editor")].forEach((cardPanel, cardIndex) => {
                    cardPanel.dataset.id = block?.items?.[cardIndex]?.id || "";
                });
            });
        });
        payload.value = JSON.stringify(sections);
        baseline = JSON.stringify(sections);
        submitting = false;
    });
    window.addEventListener("beforeunload", (event) => {
        sync();
        if (!submitting && JSON.stringify(sections) !== baseline) { event.preventDefault(); event.returnValue = ""; }
    });
    render();
    restorePageState();
    sync();
    baseline = JSON.stringify(sections);
    if (editor.dataset.imageLibraryUrl) {
        fetch(editor.dataset.imageLibraryUrl, {headers: {"X-Requested-With": "XMLHttpRequest"}, credentials: "same-origin"})
            .then((response) => response.ok ? response.json() : Promise.reject())
            .then((data) => {
                imageLibrary = data.images || [];
                preserve(() => {});
                baseline = JSON.stringify(sections);
            })
            .catch(() => {});
    }
});
