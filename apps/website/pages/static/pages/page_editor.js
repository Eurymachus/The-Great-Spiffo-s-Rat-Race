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

    const button = (text, action, danger = false) => {
        const control = document.createElement("button");
        control.type = "button";
        control.className = `button${danger ? " page-editor-danger" : ""}`;
        control.textContent = text;
        control.dataset.action = action;
        return control;
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
            summary.textContent = `${sectionIndex + 1}. ${section.section_type === "steps" ? "Numbered information cards" : "Introduction and actions"}${section.is_visible === false ? " - Hidden" : ""}`;
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
            const cardsSummary = document.createElement("summary"); cardsSummary.textContent = `Cards (${(section.items || []).length})`; cards.append(cardsSummary);
            const cardList = document.createElement("div"); cardList.className = "page-card-list";
            (section.items || []).forEach((item, itemIndex) => {
                const card = document.createElement("details"); card.className = "page-card-editor"; card.dataset.id = item.id || "";
                const cardSummary = document.createElement("summary"); cardSummary.textContent = `${itemIndex + 1}. ${item.heading || "Untitled card"}`; card.append(cardSummary);
                const cardBody = document.createElement("div"); cardBody.className = "page-card-body page-editor-grid";
                cardBody.append(field("Heading", "heading", item.heading), field("Description", "description", item.description, "textarea", true));
                const cardToolbar = document.createElement("div"); cardToolbar.className = "page-card-toolbar page-editor-field-wide";
                const cardActions = document.createElement("div"); cardActions.className = "page-editor-actions";
                cardActions.append(button("Move up", "card-up"), button("Move down", "card-down"));
                cardToolbar.append(cardActions, button("Remove card", "remove-card", true)); cardBody.append(cardToolbar); card.append(cardBody); cardList.append(card);
            });
            cards.append(cardList, button("Add card", "add-card")); body.append(cards);
            const toolbar = document.createElement("div"); toolbar.className = "page-editor-toolbar";
            const actions = document.createElement("div"); actions.className = "page-editor-actions"; actions.append(button("Move up", "section-up"), button("Move down", "section-down"));
            toolbar.append(actions, button("Remove section", "remove-section", true)); body.append(toolbar); panel.append(body); list.append(panel);
        });
    };

    editor.addEventListener("click", (event) => {
        const action = event.target.dataset.action;
        if (!action) return;
        sections = read();
        const sectionPanel = event.target.closest(".page-section-editor");
        const sectionIndex = [...list.querySelectorAll(":scope > .page-section-editor")].indexOf(sectionPanel);
        const cardPanel = event.target.closest(".page-card-editor");
        const cardIndex = cardPanel ? [...cardPanel.parentElement.children].indexOf(cardPanel) : -1;
        if (action === "add-card") sections[sectionIndex].items.push({});
        if (action === "remove-card") sections[sectionIndex].items.splice(cardIndex, 1);
        if (action === "card-up" && cardIndex > 0) [sections[sectionIndex].items[cardIndex - 1], sections[sectionIndex].items[cardIndex]] = [sections[sectionIndex].items[cardIndex], sections[sectionIndex].items[cardIndex - 1]];
        if (action === "card-down" && cardIndex < sections[sectionIndex].items.length - 1) [sections[sectionIndex].items[cardIndex + 1], sections[sectionIndex].items[cardIndex]] = [sections[sectionIndex].items[cardIndex], sections[sectionIndex].items[cardIndex + 1]];
        if (action === "remove-section") sections.splice(sectionIndex, 1);
        if (action === "section-up" && sectionIndex > 0) [sections[sectionIndex - 1], sections[sectionIndex]] = [sections[sectionIndex], sections[sectionIndex - 1]];
        if (action === "section-down" && sectionIndex < sections.length - 1) [sections[sectionIndex + 1], sections[sectionIndex]] = [sections[sectionIndex], sections[sectionIndex + 1]];
        render();
        sync();
    });
    list.addEventListener("input", sync);
    list.addEventListener("change", sync);
    editor.querySelector("[data-add-section]").addEventListener("click", () => { sections = read(); sections.push({section_type: "introduction", is_visible: true, items: []}); render(); sync(); });
    editor.closest("form").addEventListener("submit", sync);
    render();
});
