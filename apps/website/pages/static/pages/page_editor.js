document.addEventListener("DOMContentLoaded", () => {
    const editor = document.querySelector("[data-page-editor]");
    const payload = document.querySelector("#id_page_builder_data");
    if (!editor || !payload) return;

    const list = editor.querySelector("[data-section-list]");
    let sections = [];
    try { sections = JSON.parse(payload.value || "[]"); } catch (_) { sections = []; }

    const field = (label, key, value, type = "text", wide = false) => {
        const wrapper = document.createElement("label");
        wrapper.className = `page-editor-field${wide ? " page-editor-field-wide" : ""}`;
        wrapper.append(document.createTextNode(label));
        const input = type === "textarea" ? document.createElement("textarea") : document.createElement("input");
        if (type !== "textarea") input.type = type;
        input.value = value || "";
        input.dataset.key = key;
        wrapper.append(input);
        return wrapper;
    };

    const button = (text, action, danger = false, label = "") => {
        const control = document.createElement("button");
        control.type = "button";
        control.className = `button${danger ? " page-editor-danger" : ""}`;
        control.textContent = text;
        control.dataset.action = action;
        if (label) {
            control.setAttribute("aria-label", label);
            control.title = label;
        }
        return control;
    };

    const orderButtons = (upAction, downAction, index, total, subject) => {
        const actions = document.createElement("span");
        actions.className = "page-editor-summary-actions";
        const up = button("↑", upAction, false, `Move ${subject} up`);
        const down = button("↓", downAction, false, `Move ${subject} down`);
        up.disabled = index === 0;
        down.disabled = index === total - 1;
        actions.append(up, down);
        return actions;
    };

    const dragHandle = (subject) => {
        const handle = document.createElement("span");
        handle.className = "page-editor-drag-handle";
        handle.draggable = true;
        handle.textContent = "☰";
        handle.setAttribute("aria-hidden", "true");
        handle.title = `Drag to reorder ${subject}`;
        return handle;
    };

    const read = () => {
        return [...list.querySelectorAll(":scope > .page-section-editor")].map((panel) => ({
            id: panel.dataset.id ? Number(panel.dataset.id) : null,
            section_type: panel.querySelector('[data-key="section_type"]').value,
            is_visible: panel.querySelector('[data-key="is_visible"]').checked,
            small_heading: panel.querySelector('[data-key="small_heading"]').value,
            main_heading: panel.querySelector('[data-key="main_heading"]').value,
            introduction: panel.querySelector('[data-key="introduction"]').value,
            visitor_primary_button: panel.querySelector('[data-key="visitor_primary_button"]').value,
            visitor_secondary_link: panel.querySelector('[data-key="visitor_secondary_link"]').value,
            signed_in_button: panel.querySelector('[data-key="signed_in_button"]').value,
            items: [...panel.querySelectorAll(".page-card-list > .page-card-editor")].map((card) => ({
                id: card.dataset.id ? Number(card.dataset.id) : null,
                heading: card.querySelector('[data-key="heading"]').value,
                description: card.querySelector('[data-key="description"]').value,
            })),
        }));
    };
    const sync = () => { payload.value = JSON.stringify(read()); };

    const refreshOrderControls = () => {
        const sectionPanels = [...list.querySelectorAll(":scope > .page-section-editor")];
        sectionPanels.forEach((panel, sectionIndex) => {
            const sectionType = panel.querySelector('[data-key="section_type"]').value;
            const isVisible = panel.querySelector('[data-key="is_visible"]').checked;
            const summary = panel.querySelector(":scope > summary");
            summary.querySelector(":scope > .page-editor-summary-title").textContent = `${sectionIndex + 1}. ${sectionType === "steps" ? "Numbered information cards" : "Introduction and actions"}${isVisible ? "" : " - Hidden"}`;
            summary.querySelector('[data-action="section-up"]').disabled = sectionIndex === 0;
            summary.querySelector('[data-action="section-down"]').disabled = sectionIndex === sectionPanels.length - 1;

            const cardPanels = [...panel.querySelectorAll(".page-card-list > .page-card-editor")];
            cardPanels.forEach((card, cardIndex) => {
                const cardSummary = card.querySelector(":scope > summary");
                const heading = card.querySelector('[data-key="heading"]').value;
                cardSummary.querySelector(":scope > .page-editor-summary-title").textContent = `${cardIndex + 1}. ${heading || "Untitled card"}`;
                cardSummary.querySelector('[data-action="card-up"]').disabled = cardIndex === 0;
                cardSummary.querySelector('[data-action="card-down"]').disabled = cardIndex === cardPanels.length - 1;
            });
        });
    };

    const render = () => {
        list.replaceChildren();
        if (!sections.length) {
            const empty = document.createElement("p");
            empty.className = "page-editor-empty";
            empty.textContent = "This page has no sections yet.";
            list.append(empty);
        }
        sections.forEach((section, sectionIndex) => {
            const panel = document.createElement("details");
            panel.className = "page-section-editor";
            panel.dataset.id = section.id || "";
            const summary = document.createElement("summary");
            const summaryTitle = document.createElement("span");
            summaryTitle.className = "page-editor-summary-title";
            summaryTitle.textContent = `${sectionIndex + 1}. ${section.section_type === "steps" ? "Numbered information cards" : "Introduction and actions"}${section.is_visible === false ? " - Hidden" : ""}`;
            summary.append(dragHandle("section"), summaryTitle, orderButtons("section-up", "section-down", sectionIndex, sections.length, "section"));
            panel.append(summary);
            const body = document.createElement("div");
            body.className = "page-section-body";
            const grid = document.createElement("div");
            grid.className = "page-editor-grid";

            const typeField = document.createElement("label");
            typeField.className = "page-editor-field";
            typeField.append(document.createTextNode("Section type"));
            const select = document.createElement("select");
            select.dataset.key = "section_type";
            [["introduction", "Introduction and actions"], ["steps", "Numbered information cards"]].forEach(([value, label]) => {
                const option = document.createElement("option"); option.value = value; option.textContent = label; option.selected = section.section_type === value; select.append(option);
            });
            typeField.append(select);
            const visible = document.createElement("label");
            visible.className = "page-editor-field";
            const checkbox = document.createElement("input"); checkbox.type = "checkbox"; checkbox.dataset.key = "is_visible"; checkbox.checked = section.is_visible !== false;
            visible.append(checkbox, document.createTextNode(" Visible publicly"));
            grid.append(typeField, visible,
                field("Small heading", "small_heading", section.small_heading),
                field("Main heading", "main_heading", section.main_heading),
                field("Introduction", "introduction", section.introduction, "textarea", true),
                field("Visitor primary button", "visitor_primary_button", section.visitor_primary_button),
                field("Visitor secondary link", "visitor_secondary_link", section.visitor_secondary_link),
                field("Signed-in button", "signed_in_button", section.signed_in_button));
            body.append(grid);

            const cards = document.createElement("details"); cards.className = "page-cards"; cards.open = true;
            const cardsSummary = document.createElement("summary");
            const cardsSummaryTitle = document.createElement("span"); cardsSummaryTitle.textContent = `Cards (${(section.items || []).length})`;
            const addCard = button("Add card", "add-card"); addCard.classList.add("page-editor-add-card");
            cardsSummary.append(cardsSummaryTitle, addCard); cards.append(cardsSummary);
            const cardList = document.createElement("div"); cardList.className = "page-card-list";
            (section.items || []).forEach((item, itemIndex) => {
                const card = document.createElement("details"); card.className = "page-card-editor"; card.dataset.id = item.id || "";
                const cardSummary = document.createElement("summary");
                const cardSummaryTitle = document.createElement("span"); cardSummaryTitle.className = "page-editor-summary-title"; cardSummaryTitle.textContent = `${itemIndex + 1}. ${item.heading || "Untitled card"}`;
                cardSummary.append(dragHandle("card"), cardSummaryTitle, orderButtons("card-up", "card-down", itemIndex, section.items.length, "card")); card.append(cardSummary);
                const cardBody = document.createElement("div"); cardBody.className = "page-card-body page-editor-grid";
                cardBody.append(field("Heading", "heading", item.heading), field("Description", "description", item.description, "textarea", true));
                const cardToolbar = document.createElement("div"); cardToolbar.className = "page-card-toolbar page-editor-field-wide";
                cardToolbar.append(button("Remove card", "remove-card", true)); cardBody.append(cardToolbar); card.append(cardBody); cardList.append(card);
            });
            cards.append(cardList); body.append(cards);
            const toolbar = document.createElement("div"); toolbar.className = "page-editor-toolbar";
            toolbar.append(button("Remove section", "remove-section", true)); body.append(toolbar); panel.append(body); list.append(panel);
        });
    };

    const rerenderPreservingState = ({openCard = null, openLastSection = false} = {}) => {
        const scrollPosition = {x: window.scrollX, y: window.scrollY};
        const state = [...list.querySelectorAll(":scope > .page-section-editor")].map((panel) => {
            const cards = panel.querySelector(":scope > .page-section-body > .page-cards");
            return {
                sectionOpen: panel.open,
                cardsOpen: cards?.open ?? false,
                cardOpen: cards ? [...cards.querySelectorAll(".page-card-list > .page-card-editor")].map((card) => card.open) : [],
            };
        });

        render();

        const sectionPanels = [...list.querySelectorAll(":scope > .page-section-editor")];
        sectionPanels.forEach((panel, sectionIndex) => {
            if (state[sectionIndex]) panel.open = state[sectionIndex].sectionOpen;
            const cards = panel.querySelector(":scope > .page-section-body > .page-cards");
            if (!cards) return;
            if (state[sectionIndex]) cards.open = state[sectionIndex].cardsOpen;
            [...cards.querySelectorAll(".page-card-list > .page-card-editor")].forEach((card, cardIndex) => {
                if (state[sectionIndex]?.cardOpen[cardIndex]) card.open = true;
            });
        });

        if (openLastSection && sectionPanels.length) sectionPanels[sectionPanels.length - 1].open = true;
        if (openCard !== null) {
            const sectionPanel = sectionPanels[openCard];
            const cards = sectionPanel?.querySelector(":scope > .page-section-body > .page-cards");
            const cardPanels = cards ? [...cards.querySelectorAll(".page-card-list > .page-card-editor")] : [];
            if (sectionPanel) sectionPanel.open = true;
            if (cards) cards.open = true;
            if (cardPanels.length) cardPanels[cardPanels.length - 1].open = true;
        }

        window.scrollTo(scrollPosition.x, scrollPosition.y);
        window.requestAnimationFrame(() => window.scrollTo(scrollPosition.x, scrollPosition.y));
    };

    editor.addEventListener("click", (event) => {
        if (event.target.closest(".page-editor-drag-handle")) {
            event.preventDefault();
            event.stopPropagation();
            return;
        }
        const action = event.target.dataset.action;
        if (!action) return;
        event.preventDefault();
        event.stopPropagation();
        sections = read();
        const sectionPanel = event.target.closest(".page-section-editor");
        const sectionIndex = [...list.querySelectorAll(":scope > .page-section-editor")].indexOf(sectionPanel);
        const cardPanel = event.target.closest(".page-card-editor");
        const cardIndex = cardPanel ? [...cardPanel.parentElement.children].indexOf(cardPanel) : -1;
        if (action === "section-up" && sectionPanel.previousElementSibling) {
            list.insertBefore(sectionPanel, sectionPanel.previousElementSibling);
            refreshOrderControls();
            sync();
            return;
        }
        if (action === "section-down" && sectionPanel.nextElementSibling) {
            list.insertBefore(sectionPanel.nextElementSibling, sectionPanel);
            refreshOrderControls();
            sync();
            return;
        }
        if (action === "card-up" && cardPanel.previousElementSibling) {
            cardPanel.parentElement.insertBefore(cardPanel, cardPanel.previousElementSibling);
            refreshOrderControls();
            sync();
            return;
        }
        if (action === "card-down" && cardPanel.nextElementSibling) {
            cardPanel.parentElement.insertBefore(cardPanel.nextElementSibling, cardPanel);
            refreshOrderControls();
            sync();
            return;
        }
        if (action === "add-card") sections[sectionIndex].items.push({});
        if (action === "remove-card") sections[sectionIndex].items.splice(cardIndex, 1);
        if (action === "remove-section") sections.splice(sectionIndex, 1);
        rerenderPreservingState({openCard: action === "add-card" ? sectionIndex : null});
        sync();
    });
    list.addEventListener("input", () => { refreshOrderControls(); sync(); });
    list.addEventListener("change", () => { refreshOrderControls(); sync(); });

    let draggedPanel = null;
    let draggedList = null;

    const clearDragState = () => {
        list.querySelectorAll(".page-editor-dragging, .page-editor-drop-before, .page-editor-drop-after").forEach((element) => {
            element.classList.remove("page-editor-dragging", "page-editor-drop-before", "page-editor-drop-after");
        });
        draggedPanel = null;
        draggedList = null;
    };

    list.addEventListener("dragstart", (event) => {
        const handle = event.target.closest(".page-editor-drag-handle");
        if (!handle) {
            event.preventDefault();
            return;
        }
        draggedPanel = handle.closest(".page-card-editor, .page-section-editor");
        draggedList = draggedPanel.parentElement;
        draggedPanel.classList.add("page-editor-dragging");
        event.dataTransfer.effectAllowed = "move";
        event.dataTransfer.setData("text/plain", "page-editor-order");
    });

    list.addEventListener("dragover", (event) => {
        if (!draggedPanel) return;
        const selector = draggedPanel.classList.contains("page-card-editor") ? ".page-card-editor" : ".page-section-editor";
        const hoveredPanel = event.target.closest(selector);
        if (!hoveredPanel || hoveredPanel.parentElement !== draggedList) return;
        event.preventDefault();
        event.dataTransfer.dropEffect = "move";
        draggedList.querySelectorAll(".page-editor-drop-before, .page-editor-drop-after").forEach((element) => {
            element.classList.remove("page-editor-drop-before", "page-editor-drop-after");
        });
        const candidates = [...draggedList.querySelectorAll(`:scope > ${selector}`)].filter((panel) => panel !== draggedPanel);
        const nextPanel = candidates.find((panel) => {
            const bounds = panel.getBoundingClientRect();
            return event.clientY < bounds.top + bounds.height / 2;
        });
        if (nextPanel) {
            nextPanel.classList.add("page-editor-drop-before");
        } else if (candidates.length) {
            candidates[candidates.length - 1].classList.add("page-editor-drop-after");
        }
    });

    list.addEventListener("drop", (event) => {
        if (!draggedPanel) return;
        const selector = draggedPanel.classList.contains("page-card-editor") ? ".page-card-editor" : ".page-section-editor";
        const beforeTarget = draggedList.querySelector(":scope > .page-editor-drop-before");
        const afterTarget = draggedList.querySelector(":scope > .page-editor-drop-after");
        if (!beforeTarget && !afterTarget) {
            clearDragState();
            return;
        }
        event.preventDefault();
        draggedList.insertBefore(draggedPanel, beforeTarget || afterTarget.nextElementSibling);
        refreshOrderControls();
        sync();
        clearDragState();
    });

    list.addEventListener("dragend", clearDragState);
    editor.querySelector("[data-add-section]").addEventListener("click", () => { sections = read(); sections.push({section_type: "introduction", is_visible: true, items: []}); rerenderPreservingState({openLastSection: true}); sync(); });
    editor.closest("form").addEventListener("submit", sync);
    render();
});
