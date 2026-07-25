document.addEventListener("DOMContentLoaded", () => {
    const editor = document.querySelector("[data-navigation-tree]");
    if (!editor) return;

    const root = editor.querySelector(".navigation-tree-root");
    const save = document.querySelector("[data-navigation-save]");
    const csrf = editor.querySelector('[name="csrfmiddlewaretoken"]')?.value || "";
    let dragged = null;
    let pendingPickup = null;
    let dirty = false;
    let suppressNextClick = false;
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

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

    const removeConfirmation = document.createElement("div");
    removeConfirmation.className = "navigation-tree-remove-confirmation";
    removeConfirmation.hidden = true;
    removeConfirmation.setAttribute("role", "dialog");
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
    const confirmRemoval = (trigger, item) => new Promise((resolve) => {
        closeRemoveConfirmation(false);
        resolveRemoveConfirmation = resolve;
        const label = item.querySelector("[data-navigation-summary-label]")?.textContent.trim() || "navigation item";
        const hasChildren = item.querySelector(":scope > [data-navigation-children] > [data-navigation-item]");
        const message = document.createElement("strong");
        message.textContent = `Remove “${label}”?`;
        const detail = document.createElement("span");
        detail.textContent = hasChildren
            ? "This also removes every item inside this menu. It takes effect immediately and cannot be undone."
            : "This takes effect immediately and cannot be undone.";
        const controls = document.createElement("span");
        controls.className = "navigation-tree-remove-confirmation-actions";
        const cancel = document.createElement("button");
        cancel.type = "button";
        cancel.className = "button";
        cancel.textContent = "Cancel";
        const confirm = document.createElement("button");
        confirm.type = "button";
        confirm.className = "button navigation-tree-confirm-remove";
        confirm.textContent = "Remove";
        cancel.addEventListener("click", () => closeRemoveConfirmation(false));
        confirm.addEventListener("click", () => closeRemoveConfirmation(true));
        controls.append(cancel, confirm);
        removeConfirmation.append(message, detail, controls);
        removeConfirmation.hidden = false;
        const rect = trigger.getBoundingClientRect();
        const popup = removeConfirmation.getBoundingClientRect();
        const below = rect.bottom + 6;
        removeConfirmation.style.top = `${below + popup.height <= window.innerHeight - 8 ? below : Math.max(8, rect.top - popup.height - 6)}px`;
        removeConfirmation.style.left = `${Math.max(8, Math.min(window.innerWidth - popup.width - 8, rect.right - popup.width))}px`;
        cancel.focus();
    });
    document.addEventListener("pointerdown", (event) => {
        if (!removeConfirmation.hidden && !removeConfirmation.contains(event.target) && !event.target.closest("[data-navigation-remove]")) closeRemoveConfirmation(false);
    });
    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && !removeConfirmation.hidden) {
            event.preventDefault();
            closeRemoveConfirmation(false);
        }
    });

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

    const clearMarkers = () => editor.querySelectorAll(".navigation-tree-live-destination, .navigation-tree-drop-target, .navigation-tree-drop-zone").forEach((node) => {
        node.classList.remove("navigation-tree-live-destination", "navigation-tree-drop-target", "navigation-tree-drop-zone");
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
        const addChildTrigger = event.target.closest("[data-navigation-add-child]");
        if (addChildTrigger) {
            event.preventDefault();
            const parentItem = addChildTrigger.closest("[data-navigation-item]");
            addChildTrigger.disabled = true;
            fetch(addChildTrigger.dataset.addChildUrl, {
                method: "POST",
                headers: {"X-CSRFToken": csrf},
            }).then(async (response) => {
                const result = await response.json();
                if (!response.ok || !result.created) throw new Error(result.error || "The child navigation item could not be added.");
                const fragment = document.createRange().createContextualFragment(result.html);
                const child = fragment.querySelector("[data-navigation-item]");
                childContainer(parentItem).append(fragment);
                toggleItem(parentItem, true);
                editName(child);
                showToast("Child navigation item added");
            }).catch((error) => {
                showToast(error.message || "The child navigation item could not be added.", "error");
            }).finally(() => {
                addChildTrigger.disabled = false;
            });
            return;
        }
        const removeTrigger = event.target.closest("[data-navigation-remove]");
        if (removeTrigger) {
            event.preventDefault();
            const item = removeTrigger.closest("[data-navigation-item]");
            confirmRemoval(removeTrigger, item).then(async (confirmed) => {
                if (!confirmed) return;
                removeTrigger.disabled = true;
                try {
                    const response = await fetch(removeTrigger.dataset.removeUrl, {
                        method: "POST",
                        headers: {"X-CSRFToken": csrf},
                    });
                    const result = await response.json();
                    if (!response.ok || !result.removed) throw new Error(result.error || "The navigation item could not be removed.");
                    item.remove();
                    showToast("Navigation item removed");
                } catch (error) {
                    removeTrigger.disabled = false;
                    showToast(error.message || "The navigation item could not be removed.", "error");
                }
            });
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

    const animateReflow = (positions) => {
        if (reducedMotion) return;
        editor.querySelectorAll("[data-navigation-item]").forEach((item) => {
            if (item === dragged?.item || !positions.has(item)) return;
            const delta = positions.get(item) - item.getBoundingClientRect().top;
            if (!delta) return;
            item.style.transition = "none";
            item.style.transform = `translateY(${delta}px)`;
            requestAnimationFrame(() => {
                item.style.transition = "transform 170ms ease-out";
                item.style.transform = "";
                window.setTimeout(() => { item.style.transition = ""; }, 180);
            });
        });
    };
    const beginPickup = (row, event) => {
        const item = row.closest("[data-navigation-item]");
        const label = item.querySelector(":scope > [data-navigation-row] [data-navigation-summary-label]")?.textContent.trim() || "Navigation item";
        const placeholder = document.createElement("li");
        placeholder.className = "navigation-tree-drag-placeholder";
        placeholder.style.height = `${Math.max(52, item.getBoundingClientRect().height)}px`;
        const placeholderLabel = document.createElement("strong");
        placeholderLabel.textContent = label;
        placeholder.append(placeholderLabel);
        item.after(placeholder);
        const preview = document.createElement("div");
        preview.className = "navigation-tree-pointer-preview";
        preview.textContent = label;
        document.body.append(preview);
        dragged = {
            item,
            placeholder,
            preview,
            pointerId: event.pointerId,
            originalParent: item.parentElement,
            originalNext: item.nextElementSibling === placeholder ? placeholder.nextElementSibling : item.nextElementSibling,
        };
        item.classList.add("navigation-tree-drag-source-lifted");
        document.documentElement.classList.add("navigation-tree-is-dragging");
        preview.style.transform = `translate(${event.clientX + 18}px, ${event.clientY + 18}px)`;
        suppressNextClick = true;
    };
    const destinationFor = (clientX, clientY) => {
        const items = [...editor.querySelectorAll("[data-navigation-item]")].filter(
            (item) => item !== dragged.item && !dragged.item.contains(item)
        );
        const measured = items.map((item) => {
            const row = item.querySelector(":scope > [data-navigation-row]");
            const rect = row.getBoundingClientRect();
            return {item, centre: rect.top + rect.height / 2};
        });
        const firstBelow = measured.findIndex((entry) => clientY < entry.centre);
        const insertionIndex = firstBelow < 0 ? measured.length : firstBelow;
        const horizontalOrigin = root.getBoundingClientRect().left + 56;
        const requestedDepth = Math.max(
            1,
            Math.min(3, 1 + Math.round((clientX - horizontalOrigin) / 48))
        );
        let depth = Math.min(requestedDepth, 4 - subtreeDepth(dragged.item));
        let parentItem = null;
        while (depth > 1) {
            const parentDepth = depth - 1;
            for (const entry of measured.slice(0, insertionIndex).reverse()) {
                const entryDepth = itemDepth(entry.item);
                if (entryDepth === parentDepth) {
                    parentItem = entry.item;
                    break;
                }
                if (entryDepth < parentDepth) break;
            }
            if (parentItem) break;
            depth -= 1;
        }
        const container = parentItem ? childContainer(parentItem) : root;
        const next = directItems(container)
            .filter((item) => item !== dragged.item)
            .find((item) => {
                const row = item.querySelector(":scope > [data-navigation-row]");
                const rect = row.getBoundingClientRect();
                return clientY < rect.top + rect.height / 2;
            }) || null;
        return {container, next, target: parentItem, depth};
    };
    const movePickup = (clientX, clientY) => {
        const destination = destinationFor(clientX, clientY);
        if (!destination) return false;
        clearMarkers();
        const unchanged = dragged.placeholder.parentElement === destination.container
            && dragged.placeholder.nextElementSibling === destination.next;
        const positions = new Map([...editor.querySelectorAll("[data-navigation-item]")].map((item) => [item, item.getBoundingClientRect().top]));
        destination.container.insertBefore(dragged.placeholder, destination.next);
        if (!unchanged) animateReflow(positions);
        dragged.placeholder.classList.add("navigation-tree-live-destination");
        destination.target?.querySelector(":scope > [data-navigation-row]")?.classList.add("navigation-tree-drop-target");
        destination.container.classList.add("navigation-tree-drop-zone");
        return true;
    };
    const finishPickup = (commit) => {
        if (!dragged) return;
        const {item, placeholder, preview, originalParent, originalNext} = dragged;
        preview.remove();
        if (commit) {
            placeholder.before(item);
            markDirty();
        } else {
            originalParent.insertBefore(item, originalNext?.parentElement === originalParent ? originalNext : null);
        }
        placeholder.remove();
        item.classList.remove("navigation-tree-drag-source-lifted");
        clearMarkers();
        document.documentElement.classList.remove("navigation-tree-is-dragging");
        dragged = null;
    };
    editor.addEventListener("pointerdown", (event) => {
        if (event.button !== 0 || dragged || pendingPickup) return;
        const row = event.target.closest("[data-navigation-row]");
        if (!row) return;
        const handle = event.target.closest("[data-navigation-handle]");
        if (!handle && event.target.closest("button, input, textarea, select, a, label, [data-navigation-name-trigger]")) return;
        if (handle) {
            event.preventDefault();
            beginPickup(row, event);
            return;
        }
        pendingPickup = {row, pointerId: event.pointerId, startX: event.clientX, startY: event.clientY};
    });
    document.addEventListener("pointermove", (event) => {
        if (pendingPickup && event.pointerId === pendingPickup.pointerId) {
            if (Math.hypot(event.clientX - pendingPickup.startX, event.clientY - pendingPickup.startY) <= 7) return;
            const pickup = pendingPickup;
            pendingPickup = null;
            beginPickup(pickup.row, event);
        }
        if (!dragged || event.pointerId !== dragged.pointerId) return;
        event.preventDefault();
        dragged.preview.style.transform = `translate(${event.clientX + 18}px, ${event.clientY + 18}px)`;
        movePickup(event.clientX, event.clientY);
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
        finishPickup(dragged.placeholder.classList.contains("navigation-tree-live-destination"));
    };
    document.addEventListener("pointerup", releasePickup);
    document.addEventListener("pointercancel", (event) => {
        if (pendingPickup && event.pointerId === pendingPickup.pointerId) pendingPickup = null;
        if (dragged && event.pointerId === dragged.pointerId) finishPickup(false);
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
                const destinationDescription = page.value ? `Page · ${selected.dataset.address}` : "Menu group · no page destination";
                destination.dataset.tooltip = destinationDescription;
                destination.setAttribute("aria-label", `Destination: ${destinationDescription}`);
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
