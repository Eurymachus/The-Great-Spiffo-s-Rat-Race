window.RatRacePages.register((pageSignal) => {
    const thumbnailRows = [...document.querySelectorAll(".mods-list .mod-entry:has(> img)")];
    const mobileRows = window.matchMedia("(max-width: 680px)");
    let thumbnailFrame;
    const fitThumbnails = () => {
        cancelAnimationFrame(thumbnailFrame);
        thumbnailFrame = requestAnimationFrame(() => {
            thumbnailRows.forEach((row) => {
                if (!mobileRows.matches && row.closest(".mods-list-compact")) {
                    row.style.removeProperty("--mod-thumbnail-size");
                    return;
                }
                // Reset before measuring so rotation can shrink as well as grow.
                row.style.removeProperty("--mod-thumbnail-size");
                for (let pass = 0; pass < 12; pass += 1) {
                    const size = Math.ceil(row.clientHeight);
                    const current = row.querySelector("img").getBoundingClientRect().width;
                    if (Math.abs(size - current) < 1) break;
                    // Keep a readable text column for unusually long titles.
                    const maximum = Math.floor(row.clientWidth / 2);
                    row.style.setProperty("--mod-thumbnail-size", `${Math.min(size, maximum)}px`);
                    if (size >= maximum) break;
                }
            });
        });
    };
    fitThumbnails();
    window.addEventListener("resize", fitThumbnails, {signal: pageSignal});
    document.fonts?.ready.then(() => { if (!pageSignal.aborted) fitThumbnails(); });
    pageSignal.addEventListener("abort", () => cancelAnimationFrame(thumbnailFrame), {once: true});

    const connectDialog = (dialogSelector, openSelector, closeSelector) => {
        const dialog = document.querySelector(dialogSelector);
        if (!dialog) return;
        const fitViewport = () => {
            const viewport = window.visualViewport;
            dialog.style.setProperty("--mod-viewport-height", `${viewport?.height || window.innerHeight}px`);
            dialog.style.setProperty("--mod-viewport-top", `${viewport?.offsetTop || 0}px`);
        };
        fitViewport();
        window.visualViewport?.addEventListener("resize", fitViewport, {signal: pageSignal});
        window.visualViewport?.addEventListener("scroll", fitViewport, {signal: pageSignal});
        window.addEventListener("resize", fitViewport, {signal: pageSignal});
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
    if (window.location.hash === "#submit-mod") {
        const submissionDialog = document.querySelector("[data-mod-submit-dialog]");
        if (submissionDialog && !submissionDialog.open) submissionDialog.showModal();
    }
    connectDialog("[data-mod-rules-dialog]", "[data-mod-rules-open]", "[data-mod-rules-close]");

    const form = document.querySelector("[data-mod-review-form]");
    if (!form) return;
    const reason = form.querySelector('[name="reason"]');
    let dismissReasonToast = () => {};
    const clearReasonError = () => {
        dismissReasonToast();
        reason.removeAttribute("aria-invalid");
        reason.closest(".field").classList.remove("has-error");
    };
    reason.addEventListener("input", () => {
        if (reason.value.trim()) clearReasonError();
    }, {signal: pageSignal});
    form.addEventListener("submit", (event) => {
        if (reason.value.trim()) return;
        event.preventDefault();
        reason.setAttribute("aria-invalid", "true");
        reason.closest(".field").classList.add("has-error");
        reason.focus();
        dismissReasonToast = window.RatRaceToast.show({
            message: "Please enter a reason.", type: "error", signal: pageSignal,
        });
    }, {signal: pageSignal});
    const search = form.querySelector("[data-workshop-search]");
    const selectedId = form.querySelector('[name="workshop_id"]');
    const results = form.querySelector("[data-workshop-results]");
    const selection = form.querySelector("[data-workshop-selection]");
    const status = form.querySelector("[data-workshop-status]");
    const submit = form.querySelector("[data-mod-review-submit]");
    let timer;
    pageSignal.addEventListener("abort", () => clearTimeout(timer), {once: true});
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
