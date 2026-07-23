(() => {
    "use strict";
    const dialog = document.querySelector("[data-avatar-dialog]");
    if (!dialog || typeof dialog.showModal !== "function") return;
    const input = dialog.querySelector("[data-avatar-input]");
    const preview = dialog.querySelector(".avatar-modal-preview");
    const filename = dialog.querySelector("[data-avatar-filename]");
    const error = dialog.querySelector("[data-avatar-error]");
    const submit = dialog.querySelector("[data-avatar-submit]");
    const originalPreview = preview?.innerHTML;
    const allowedTypes = new Set(["image/jpeg", "image/png", "image/webp"]);
    const maximumBytes = 5 * 1024 * 1024;
    let previewUrl = null;

    const rejectFile = (message) => {
        if (previewUrl) URL.revokeObjectURL(previewUrl);
        previewUrl = null;
        input.value = "";
        preview.innerHTML = originalPreview;
        error.textContent = message;
        error.hidden = false;
        submit.disabled = true;
    };

    let trigger = null;
    document.querySelectorAll("[data-avatar-open]").forEach((button) => {
        button.addEventListener("click", (event) => {
            event.preventDefault();
            event.stopPropagation();
            trigger = button;
            dialog.showModal();
        });
    });
    dialog.querySelector("[data-avatar-close]").addEventListener("click", () => dialog.close());
    input?.addEventListener("change", () => {
        const file = input.files?.[0];
        filename.textContent = file?.name || "No image selected";
        error.hidden = true;
        error.textContent = "";
        submit.disabled = true;
        if (previewUrl) URL.revokeObjectURL(previewUrl);
        previewUrl = null;
        if (!file) {
            preview.innerHTML = originalPreview;
            return;
        }
        if (!allowedTypes.has(file.type)) {
            rejectFile("Choose a JPEG, PNG or WebP image.");
            return;
        }
        if (file.size > maximumBytes) {
            rejectFile("The avatar must be no larger than 5 MB.");
            return;
        }
        previewUrl = URL.createObjectURL(file);
        const image = document.createElement("img");
        image.alt = "Selected avatar preview";
        image.src = previewUrl;
        image.addEventListener("load", () => {
            if (image.naturalWidth < 80 || image.naturalHeight < 80) {
                rejectFile("The avatar must be at least 80 × 80 pixels.");
                return;
            }
            preview.replaceChildren(image);
            submit.disabled = false;
        }, {once: true});
        image.addEventListener("error", () => rejectFile("The selected image could not be read."), {once: true});
    });
    dialog.querySelector(".avatar-upload-form")?.addEventListener("submit", (event) => {
        if (submit.disabled || !input.files?.length) event.preventDefault();
    });
    dialog.addEventListener("click", (event) => {
        if (event.target === dialog) dialog.close();
    });
    dialog.addEventListener("close", () => trigger?.focus());
    window.addEventListener("pagehide", () => {
        if (previewUrl) URL.revokeObjectURL(previewUrl);
    }, {once: true});
})();
