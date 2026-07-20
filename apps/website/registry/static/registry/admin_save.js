(() => {
    "use strict";

    const form = document.querySelector("body.change-form form[id$='_form']");
    const continueButton = form?.querySelector('[type="submit"][name="_continue"]');
    if (!form || !continueButton || !window.fetch || !window.DOMParser) return;

    let saving = false;
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

            if (response.ok && response.redirected) {
                const savedDocument = new DOMParser().parseFromString(await response.text(), "text/html");
                if (!savedDocument.querySelector("body.change-form form[id$='_form']")) {
                    throw new Error("The saved form was not returned.");
                }
                updateReadonlyFields(savedDocument);
                form.querySelectorAll('input[type="file"]').forEach((input) => { input.value = ""; });
                form.dispatchEvent(new CustomEvent("rat-race:admin-save-success", {
                    detail: {document: savedDocument, responseUrl: response.url},
                }));
                showToast("Changes saved");
                return;
            }

            if (response.ok) {
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
            continueButton.disabled = false;
        }
    });
})();
