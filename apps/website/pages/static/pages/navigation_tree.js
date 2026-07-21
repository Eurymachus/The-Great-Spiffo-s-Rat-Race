document.addEventListener("DOMContentLoaded", () => {
    const editor = document.querySelector("[data-navigation-tree]");
    if (!editor) return;

    const root = editor.querySelector(".navigation-tree-root");
    const save = document.querySelector("[data-navigation-save]");
    const csrf = editor.querySelector('[name="csrfmiddlewaretoken"]')?.value || "";
    let dragged = null;
    let dirty = false;
    let suppressNextClick = false;

    let toastTimer = null;
    const showToast = (message, type = "success") => {
        let region = document.querySelector(".admin-save-toast-region");
        if (!region) {
            region = document.createElement("div");
            region.className = "admin-save-toast-region";
            region.setAttribute("aria-live", "polite");
            region.innerHTML = '<div class="admin-save-toast" role="status"></div>';
            document.body.append(region);
        }
        const toast = region.querySelector(".admin-save-toast");
        window.clearTimeout(toastTimer);
        toast.textContent = message;
        toast.className = `admin-save-toast is-${type}`;
        requestAnimationFrame(() => toast.classList.add("is-visible"));
        toastTimer = window.setTimeout(() => toast.classList.remove("is-visible"), type === "error" ? 5000 : 2600);
    };

    const directItems = (container) => [...container.children].filter((child) => child.matches("[data-navigation-item]"));
    const childContainer = (item) => item.querySelector(":scope > [data-navigation-children]");
    const itemDepth = (item) => {
        let depth = 1;
        let parent = item.parentElement?.closest("[data-navigation-item]");
        while (parent) {
            depth += 1;
            parent = parent.parentElement?.closest("[data-navigation-item]");
        }
        return depth;
    };
    const subtreeDepth = (item) => {
        const children = directItems(childContainer(item));
        return children.length ? 1 + Math.max(...children.map(subtreeDepth)) : 1;
    };
    const canMoveToDepth = (item, depth) => depth + subtreeDepth(item) - 1 <= 3;

    const clearMarkers = () => editor.querySelectorAll(".is-drop-before, .is-drop-after, .is-drop-inside").forEach((row) => {
        row.classList.remove("is-drop-before", "is-drop-after", "is-drop-inside");
        delete row.dataset.dropIntent;
    });
    const markDirty = () => {
        dirty = true;
        save.disabled = false;
    };

    const toggleItem = (item, force) => {
        const fields = item.querySelector(":scope > [data-navigation-fields]");
        const toggle = item.querySelector(":scope > [data-navigation-row] [data-navigation-toggle]");
        const expanded = force ?? !item.classList.contains("is-expanded");
        item.classList.toggle("is-expanded", expanded);
        fields.hidden = !expanded;
        toggle.setAttribute("aria-expanded", String(expanded));
        if (expanded) fields.querySelector("select, input")?.focus();
    };

    const editName = (item) => {
        const label = item.querySelector(":scope > [data-navigation-row] [data-navigation-summary-label]");
        const input = item.querySelector(":scope > [data-navigation-row] [data-navigation-label]");
        input.dataset.startValue = input.value;
        label.hidden = true;
        input.hidden = false;
        input.focus();
        input.select();
    };
    const finishNameEdit = (input, commit = true) => {
        if (input.hidden) return;
        const item = input.closest("[data-navigation-item]");
        const label = item.querySelector(":scope > [data-navigation-row] [data-navigation-summary-label]");
        const startValue = input.dataset.startValue || label.textContent;
        const nextValue = commit ? input.value.trim() : startValue;
        input.value = nextValue || startValue;
        label.textContent = input.value;
        input.hidden = true;
        label.hidden = false;
        if (commit && input.value !== startValue) markDirty();
    };

    editor.addEventListener("click", (event) => {
        if (suppressNextClick) {
            suppressNextClick = false;
            event.preventDefault();
            event.stopImmediatePropagation();
            return;
        }
        const nameTrigger = event.target.closest("[data-navigation-name-trigger]");
        if (nameTrigger) {
            event.preventDefault();
            editName(nameTrigger.closest("[data-navigation-item]"));
            return;
        }
        const row = event.target.closest("[data-navigation-row]");
        if (!row || event.target.closest("[data-navigation-handle]")) return;
        if (event.target.closest("button, input, select, a, label") && !event.target.closest("[data-navigation-toggle]")) return;
        toggleItem(row.closest("[data-navigation-item]"));
    });

    editor.addEventListener("input", (event) => {
        if (!event.target.closest("[data-navigation-fields]")) return;
        markDirty();
    });
    editor.addEventListener("change", (event) => {
        if (!event.target.closest("[data-navigation-fields]")) return;
        markDirty();
    });
    editor.addEventListener("keydown", (event) => {
        const input = event.target.closest("[data-navigation-label]");
        if (!input) return;
        if (event.key === "Enter") {
            event.preventDefault();
            finishNameEdit(input);
        } else if (event.key === "Escape") {
            event.preventDefault();
            finishNameEdit(input, false);
        }
    });
    editor.addEventListener("focusout", (event) => {
        const input = event.target.closest("[data-navigation-label]");
        if (input) finishNameEdit(input);
    });

    editor.addEventListener("pointerdown", (event) => {
        if (event.button !== 0) return;
        const row = event.target.closest("[data-navigation-row]");
        if (!row) return;
        const handle = event.target.closest("[data-navigation-handle]");
        if (!handle && event.target.closest("button, input, textarea, select, a, label, [data-navigation-name-trigger]")) return;
        row.closest("[data-navigation-item]").draggable = true;
    });
    editor.addEventListener("pointerup", () => {
        editor.querySelectorAll("[data-navigation-item][draggable=true]").forEach((item) => {
            if (item !== dragged) item.draggable = false;
        });
    });
    editor.addEventListener("dragstart", (event) => {
        const item = event.target.closest("[data-navigation-item]");
        if (!item?.draggable) return event.preventDefault();
        dragged = item;
        item.classList.add("is-dragging");
        event.dataTransfer.effectAllowed = "move";
        event.dataTransfer.setData("text/plain", item.dataset.id);
        const row = item.querySelector(":scope > [data-navigation-row]");
        if (row) event.dataTransfer.setDragImage(row, 24, Math.min(event.offsetY || 18, row.offsetHeight));
    });
    editor.addEventListener("dragover", (event) => {
        if (!dragged) return;
        const row = event.target.closest("[data-navigation-row]");
        const target = row?.closest("[data-navigation-item]");
        clearMarkers();
        if (!row || !target || target === dragged || dragged.contains(target)) return;

        const rect = row.getBoundingClientRect();
        const ratio = (event.clientY - rect.top) / rect.height;
        let intent = ratio < .28 ? "before" : ratio > .72 ? "after" : "inside";
        const destinationDepth = intent === "inside" ? itemDepth(target) + 1 : itemDepth(target);
        if (!canMoveToDepth(dragged, destinationDepth)) {
            if (intent === "inside") intent = ratio < .5 ? "before" : "after";
            if (!canMoveToDepth(dragged, itemDepth(target))) return;
        }
        event.preventDefault();
        event.dataTransfer.dropEffect = "move";
        row.dataset.dropIntent = intent;
        row.classList.add(`is-drop-${intent}`);
    });
    editor.addEventListener("drop", (event) => {
        if (!dragged) return;
        const row = event.target.closest("[data-navigation-row]");
        const target = row?.closest("[data-navigation-item]");
        const intent = row?.dataset.dropIntent;
        if (!target || !intent || target === dragged || dragged.contains(target)) return;
        event.preventDefault();
        if (intent === "inside") childContainer(target).append(dragged);
        else if (intent === "before") target.parentElement.insertBefore(dragged, target);
        else target.parentElement.insertBefore(dragged, target.nextSibling);
        clearMarkers();
        markDirty();
    });
    editor.addEventListener("dragend", () => {
        clearMarkers();
        suppressNextClick = Boolean(dragged);
        window.setTimeout(() => { suppressNextClick = false; }, 0);
        dragged?.classList.remove("is-dragging");
        if (dragged) dragged.draggable = false;
        dragged = null;
    });

    editor.addEventListener("keydown", (event) => {
        const handle = event.target.closest("[data-navigation-handle]");
        if (!handle || !event.altKey) return;
        const item = handle.closest("[data-navigation-item]");
        const siblings = directItems(item.parentElement);
        const index = siblings.indexOf(item);
        if (event.key === "ArrowUp" && index > 0) item.parentElement.insertBefore(item, siblings[index - 1]);
        else if (event.key === "ArrowDown" && index < siblings.length - 1) item.parentElement.insertBefore(siblings[index + 1], item);
        else if (event.key === "ArrowRight" && index > 0 && canMoveToDepth(item, itemDepth(siblings[index - 1]) + 1)) childContainer(siblings[index - 1]).append(item);
        else if (event.key === "ArrowLeft") {
            const parentItem = item.parentElement.closest("[data-navigation-item]");
            if (!parentItem) return;
            parentItem.parentElement.insertBefore(item, parentItem.nextSibling);
        } else return;
        event.preventDefault();
        markDirty();
        handle.focus();
    });

    const serialise = () => {
        const items = [];
        const walk = (container, parentId = null) => {
            directItems(container).forEach((item, index) => {
                const id = Number(item.dataset.id);
                const label = item.querySelector("[data-navigation-label]").value.trim();
                const pageValue = item.querySelector("[data-navigation-page]").value;
                items.push({
                    id,
                    parent_id: parentId,
                    position: index * 10,
                    label,
                    page_id: pageValue ? Number(pageValue) : null,
                    is_visible: item.querySelector("[data-navigation-visible]").checked,
                });
                walk(childContainer(item), id);
            });
        };
        walk(root);
        return items;
    };
    save.addEventListener("click", async () => {
        editor.classList.add("is-saving");
        save.disabled = true;
        try {
            const response = await fetch(editor.dataset.saveUrl, {
                method: "POST",
                headers: {"Content-Type": "application/json", "X-CSRFToken": csrf},
                body: JSON.stringify({items: serialise()}),
            });
            const result = await response.json();
            if (!response.ok || !result.saved) throw new Error(result.error || "Navigation could not be saved.");
            dirty = false;
            save.disabled = true;
            editor.querySelectorAll("[data-navigation-item]").forEach((item) => {
                const label = item.querySelector("[data-navigation-label]").value.trim();
                const page = item.querySelector("[data-navigation-page]");
                const selected = page.selectedOptions[0];
                const visible = item.querySelector("[data-navigation-visible]").checked;
                item.querySelector("[data-navigation-summary-label]").textContent = label;
                const destination = item.querySelector("[data-navigation-destination]");
                destination.textContent = page.value ? `Page · ${selected.dataset.address}` : "Menu group";
                let draft = item.querySelector("[data-navigation-draft]");
                const isDraft = page.value && selected.dataset.published === "false";
                if (isDraft && !draft) {
                    draft = document.createElement("span");
                    draft.className = "navigation-tree-badge is-warning";
                    draft.dataset.navigationDraft = "";
                    draft.textContent = "Draft page";
                    destination.after(draft);
                } else if (!isDraft) draft?.remove();
                let hidden = item.querySelector("[data-navigation-hidden]");
                if (!visible && !hidden) {
                    hidden = document.createElement("span");
                    hidden.className = "navigation-tree-badge is-warning";
                    hidden.dataset.navigationHidden = "";
                    hidden.textContent = "Hidden";
                    item.querySelector("[data-navigation-row]").append(hidden);
                } else if (visible) hidden?.remove();
            });
            showToast("Changes saved");
        } catch (error) {
            showToast(error.message || "Changes could not be saved. Please try again.", "error");
        } finally {
            editor.classList.remove("is-saving");
            save.disabled = !dirty;
        }
    });
    window.addEventListener("beforeunload", (event) => {
        if (!dirty) return;
        event.preventDefault();
        event.returnValue = "";
    });
});
