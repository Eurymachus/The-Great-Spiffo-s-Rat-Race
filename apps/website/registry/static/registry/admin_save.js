(() => {
    "use strict";

    const form = document.querySelector(
        "body.change-form form[id$='_form'], body.add-form form[id$='_form']"
    );
    const continueButton = form?.querySelector('[type="submit"][name="_continue"]');
    if (!form || !continueButton || !window.fetch || !window.DOMParser) return;

    const initialHasErrors = Boolean(document.querySelector(".errornote, .errorlist"));
    let saving = false;
    let dirty = initialHasErrors;
    let toastTimer = null;
    const region = document.createElement("div");
    region.className = "admin-save-toast-region";
    region.setAttribute("aria-live", "polite");
    region.setAttribute("aria-atomic", "true");
    const toast = document.createElement("div");
    toast.className = "admin-save-toast";
    toast.setAttribute("role", "status");
    region.append(toast);
    document.body.append(region);

    const showToast = (message, type = "success") => {
        window.clearTimeout(toastTimer);
        toast.textContent = message;
        toast.className = `admin-save-toast is-${type}`;
        requestAnimationFrame(() => toast.classList.add("is-visible"));
        toastTimer = window.setTimeout(() => toast.classList.remove("is-visible"), type === "error" ? 5000 : 2600);
    };

    const updateReadonlyFields = (savedDocument) => {
        document.querySelectorAll(".readonly").forEach((current) => {
            const row = current.closest(".form-row");
            const fieldClass = [...(row?.classList || [])].find((name) => name.startsWith("field-"));
            if (!fieldClass) return;
            const saved = savedDocument.querySelector(`.${fieldClass} .readonly`);
            if (saved) current.innerHTML = saved.innerHTML;
        });
    };

    const adoptSavedLocation = (savedDocument, responseUrl) => {
        const savedForm = savedDocument.querySelector("body.change-form form[id$='_form']");
        const savedEditor = savedDocument.querySelector("[data-page-editor]");
        const currentEditor = document.querySelector("[data-page-editor]");
        const savedAction = savedForm?.getAttribute("action");
        form.action = savedAction ? new URL(savedAction, responseUrl).href : responseUrl;
        if (savedEditor && currentEditor) {
            if (savedEditor.dataset.removeUrl) {
                currentEditor.dataset.removeUrl = savedEditor.dataset.removeUrl;
            }
        }
        if (responseUrl && responseUrl !== window.location.href) {
            window.history.replaceState(window.history.state, "", responseUrl);
        }
    };

    const setDirty = (nextDirty) => {
        dirty = nextDirty;
        continueButton.disabled = saving || !dirty;
    };
    const markDirty = (event) => {
        if (event.target?.name === "csrfmiddlewaretoken") return;
        setDirty(true);
    };

    continueButton.value = "Save";
    setDirty(initialHasErrors);
    form.addEventListener("input", markDirty);
    form.addEventListener("change", markDirty);
    form.addEventListener("rat-race:admin-dirty", () => setDirty(true));
    form.addEventListener("rat-race:admin-editor-ready", () => setDirty(initialHasErrors));

    form.addEventListener("submit", async (event) => {
        const submitter = event.submitter;
        if (form.dataset.adminSaveBypass === "true" || submitter?.name !== "_continue") return;
        event.preventDefault();
        if (saving) return;

        saving = true;
        continueButton.disabled = true;
        form.dispatchEvent(new CustomEvent("rat-race:admin-save-start"));

        try {
            await Promise.resolve();
            const data = new FormData(form);
            data.append(submitter.name, submitter.value || "Save and continue editing");
            const response = await fetch(form.action || window.location.href, {
                method: "POST",
                body: data,
                headers: {"X-Requested-With": "XMLHttpRequest"},
                credentials: "same-origin",
            });

            if (response.ok) {
                const savedDocument = new DOMParser().parseFromString(await response.text(), "text/html");
                const savedForm = savedDocument.querySelector("body.change-form form[id$='_form']");
                const hasErrors = savedDocument.querySelector(".errornote, .errorlist");
                if (savedForm && !hasErrors) {
                updateReadonlyFields(savedDocument);
                adoptSavedLocation(savedDocument, response.url);
                form.querySelectorAll('input[type="file"]').forEach((input) => { input.value = ""; });
                form.dispatchEvent(new CustomEvent("rat-race:admin-save-success", {
                    detail: {document: savedDocument, responseUrl: response.url},
                }));
                setDirty(false);
                showToast("Changes saved");
                return;
                }
                form.dataset.adminSaveBypass = "true";
                continueButton.disabled = false;
                form.dispatchEvent(new CustomEvent("rat-race:admin-save-fallback"));
                form.requestSubmit(submitter);
                return;
            }
            throw new Error(`Save failed with status ${response.status}.`);
        } catch (_) {
            form.dispatchEvent(new CustomEvent("rat-race:admin-save-failure"));
            showToast("Changes could not be saved. Please try again.", "error");
        } finally {
            saving = false;
            continueButton.disabled = !dirty;
        }
    });
})();
