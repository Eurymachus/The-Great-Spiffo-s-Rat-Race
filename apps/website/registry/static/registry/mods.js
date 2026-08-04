document.addEventListener("DOMContentLoaded", () => {
    const connectDialog = (dialogSelector, openSelector, closeSelector) => {
        const dialog = document.querySelector(dialogSelector);
        if (!dialog) return;
        document.querySelectorAll(openSelector).forEach((button) => {
            button.addEventListener("click", () => dialog.showModal());
        });
        dialog.querySelectorAll(closeSelector).forEach((button) => {
            button.addEventListener("click", () => dialog.close());
        });
        dialog.addEventListener("click", (event) => {
            if (event.target === dialog) dialog.close();
        });
        if (dialog.hasAttribute("data-open-on-load")) dialog.showModal();
    };

    connectDialog("[data-mod-submit-dialog]", "[data-mod-submit-open]", "[data-mod-submit-close]");
    connectDialog("[data-mod-rules-dialog]", "[data-mod-rules-open]", "[data-mod-rules-close]");

    const form = document.querySelector("[data-mod-review-form]");
    if (!form) return;
    const search = form.querySelector("[data-workshop-search]");
    const selectedId = form.querySelector('[name="workshop_id"]');
    const results = form.querySelector("[data-workshop-results]");
    const selection = form.querySelector("[data-workshop-selection]");
    const status = form.querySelector("[data-workshop-status]");
    const submit = form.querySelector("[data-mod-review-submit]");
    let timer;
    let requestNumber = 0;

    const setStatus = (message = "", error = false) => {
        status.textContent = message;
        status.classList.toggle("field-validation-error", Boolean(message) && error);
        search.closest(".field")?.classList.toggle("field-error", Boolean(message) && error);
        if (error) search.setAttribute("aria-invalid", "true");
        else search.removeAttribute("aria-invalid");
    };

    const clearSelection = () => {
        selectedId.value = "";
        selection.hidden = true;
        selection.classList.remove("mod-workshop-selection-existing");
        selection.replaceChildren();
        submit.disabled = true;
    };

    const chooseItem = (item) => {
        results.replaceChildren();
        selectedId.value = item.workshop_id;
        search.value = item.title;
        selection.hidden = false;
        const image = document.createElement("img");
        image.src = item.preview_url || "";
        image.alt = "";
        if (!item.preview_url) image.hidden = true;
        const copy = document.createElement("div");
        const title = document.createElement("strong");
        title.textContent = item.title;
        const details = document.createElement("small");
        details.textContent = `Workshop ID: ${item.workshop_id}`;
        copy.append(title, details);
        const ruling = document.createElement("span");
        ruling.className = "mod-workshop-existing-status";
        ruling.setAttribute("role", "status");
        ruling.textContent = item.existing ? `Already ${item.ruling}` : "";
        ruling.hidden = !item.existing;
        selection.classList.toggle("mod-workshop-selection-existing", item.existing);
        selection.replaceChildren(image, copy, ruling);
        setStatus();
        submit.disabled = item.existing;
    };

    const renderResults = (items) => {
        results.replaceChildren();
        items.forEach((item) => {
            const option = document.createElement("button");
            option.type = "button";
            option.className = "mod-workshop-result";
            option.setAttribute("role", "option");
            const image = document.createElement("img");
            image.src = item.preview_url || "";
            image.alt = "";
            if (!item.preview_url) image.hidden = true;
            const copy = document.createElement("span");
            const title = document.createElement("strong");
            title.textContent = item.title;
            const details = document.createElement("small");
            details.textContent = item.existing
                ? `Workshop ID: ${item.workshop_id} · ${item.ruling}`
                : `Workshop ID: ${item.workshop_id}`;
            copy.append(title, details);
            option.append(image, copy);
            option.addEventListener("click", () => chooseItem(item));
            results.appendChild(option);
        });
    };

    const lookup = async () => {
        const query = search.value.trim();
        clearSelection();
        results.replaceChildren();
        if (query.length < 3) {
            setStatus();
            return;
        }
        const currentRequest = ++requestNumber;
        setStatus("Searching Steam Workshop...");
        try {
            const response = await fetch(`${form.dataset.workshopLookupUrl}?q=${encodeURIComponent(query)}`, {
                headers: {"X-Requested-With": "XMLHttpRequest"},
            });
            const payload = await response.json();
            if (currentRequest !== requestNumber) return;
            if (!response.ok) {
                setStatus(payload.error || "Steam Workshop search failed.", true);
                return;
            }
            if (!payload.results.length) {
                setStatus("No matching Project Zomboid Workshop mods found.", true);
                return;
            }
            setStatus();
            if (payload.results.length === 1 && (/^\d{6,20}$/.test(query) || /steamcommunity\.com/i.test(query))) {
                chooseItem(payload.results[0]);
                return;
            }
            renderResults(payload.results);
        } catch (_error) {
            if (currentRequest === requestNumber) setStatus("Steam Workshop search failed. Please try again.", true);
        }
    };

    search.addEventListener("input", () => {
        requestNumber += 1;
        clearTimeout(timer);
        clearSelection();
        results.replaceChildren();
        setStatus();
        timer = setTimeout(lookup, 400);
    });
    if (search.value.trim()) lookup();
});
