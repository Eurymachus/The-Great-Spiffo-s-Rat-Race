document.addEventListener("DOMContentLoaded", () => {
    const selects = [...document.querySelectorAll("select.media-library-select")];
    const managerButton = document.querySelector("[data-media-library-manager]");
    if (!selects.length && !managerButton) return;

    const libraryUrl = selects[0]?.dataset.libraryUrl || managerButton.dataset.mediaLibraryManager;
    const csrfToken = document.querySelector('[name="csrfmiddlewaretoken"]')?.value || "";
    let activeSelect = null;
    let library = [];
    let pending = [];
    let uploadOnly = false;

    const dialog = document.createElement("dialog");
    dialog.className = "media-library-dialog";
    dialog.innerHTML = `
        <div class="media-library-modal">
            <header><div><h2 data-modal-title>Choose an image</h2><p data-modal-introduction>Select an existing image or upload new files.</p></div><button type="button" class="media-modal-close" aria-label="Close">&times;</button></header>
            <section class="media-library-section" data-library-section>
                <div class="media-library-grid" data-media-grid></div>
            </section>
            <section class="media-upload-panel">
                <div class="media-upload-heading"><div><h3>Upload images</h3><p>PNG, JPEG, WebP or ICO, up to 5 MB each.</p></div><label class="button media-choose-files">Choose files<input type="file" accept=".png,.jpg,.jpeg,.webp,.ico,image/png,image/jpeg,image/webp,image/x-icon" multiple hidden></label></div>
                <div class="media-upload-list" data-upload-list><p class="media-empty">No files selected.</p></div>
                <div class="media-upload-actions"><span data-upload-summary></span><button type="button" class="button media-upload-button" disabled>Upload</button></div>
            </section>
        </div>`;
    document.body.append(dialog);

    const modalTitle = dialog.querySelector("[data-modal-title]");
    const modalIntroduction = dialog.querySelector("[data-modal-introduction]");
    const librarySection = dialog.querySelector("[data-library-section]");
    const grid = dialog.querySelector("[data-media-grid]");
    const fileInput = dialog.querySelector('input[type="file"]');
    const uploadList = dialog.querySelector("[data-upload-list]");
    const uploadButton = dialog.querySelector(".media-upload-button");
    const uploadSummary = dialog.querySelector("[data-upload-summary]");

    document.querySelectorAll(".managed-image-name").forEach((nameButton) => {
        nameButton.addEventListener("click", () => {
            if (nameButton.hidden) return;
            const originalName = nameButton.textContent.trim();
            const editor = document.createElement("span");
            editor.className = "managed-image-name-editor";
            editor.innerHTML = '<input type="text" maxlength="120"><button type="button" class="button" data-name-save>Save</button><button type="button" class="button" data-name-cancel>Cancel</button><small class="managed-image-name-error" hidden></small>';
            const input = editor.querySelector("input");
            const save = editor.querySelector("[data-name-save]");
            const cancel = editor.querySelector("[data-name-cancel]");
            const error = editor.querySelector(".managed-image-name-error");
            input.value = originalName;
            nameButton.hidden = true;
            nameButton.after(editor);
            input.focus();
            input.select();

            const closeEditor = () => {
                editor.remove();
                nameButton.hidden = false;
                nameButton.focus();
            };
            cancel.addEventListener("click", closeEditor);
            save.addEventListener("click", async () => {
                const name = input.value.trim();
                error.hidden = true;
                save.disabled = true;
                try {
                    const data = new FormData();
                    data.append("name", name);
                    const response = await fetch(nameButton.dataset.renameUrl, {
                        method: "POST",
                        headers: {"X-CSRFToken": csrfToken, "X-Requested-With": "XMLHttpRequest"},
                        body: data,
                    });
                    const result = await response.json();
                    if (!response.ok) throw new Error(result.error || "The image name could not be saved.");
                    nameButton.textContent = result.name;
                    const libraryImage = library.find((image) => String(image.id) === String(result.id));
                    if (libraryImage) libraryImage.name = result.name;
                    closeEditor();
                } catch (saveError) {
                    error.textContent = saveError.message;
                    error.hidden = false;
                    save.disabled = false;
                    input.focus();
                }
            });
            input.addEventListener("keydown", (event) => {
                if (event.key === "Enter") { event.preventDefault(); save.click(); }
                if (event.key === "Escape") { event.preventDefault(); closeEditor(); }
            });
        });
    });

    const formatSize = (bytes) => bytes < 1024 * 1024 ? `${(bytes / 1024).toFixed(1)} KB` : `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    const deriveName = (filename) => filename.replace(/\.[^.]+$/, "").replace(/[-_]+/g, " ").replace(/\s+/g, " ").trim().replace(/\b\w/g, (letter) => letter.toUpperCase());
    const compatible = (file) => {
        const extension = file.name.split(".").pop().toLowerCase();
        if (!["png", "jpg", "jpeg", "webp", "ico"].includes(extension)) return "This file type is not supported.";
        if (file.size > 5 * 1024 * 1024) return "This file is larger than 5 MB.";
        return "";
    };

    const resetPending = () => {
        pending.forEach((entry) => { if (entry.preview) URL.revokeObjectURL(entry.preview); });
        pending = [];
        fileInput.value = "";
        uploadSummary.textContent = "";
        renderPending();
    };

    const updateControlPreview = (select) => {
        const control = select.closest(".media-picker-control");
        const preview = control?.querySelector(".media-picker-current");
        if (!preview) return;
        const image = library.find((candidate) => String(candidate.id) === select.value);
        const clear = control.querySelector(".media-picker-clear");
        if (clear) clear.disabled = !select.value;
        preview.replaceChildren();
        if (!image) {
            preview.innerHTML = '<span class="media-picker-placeholder">No image selected</span>';
            return;
        }
        const thumbnail = document.createElement("img");
        thumbnail.src = image.url;
        thumbnail.alt = "";
        const name = document.createElement("strong");
        name.textContent = image.name;
        preview.append(thumbnail, name);
    };

    const refreshSelects = () => {
        selects.forEach((select) => {
            const value = select.value;
            const blank = select.querySelector('option[value=""]')?.textContent || "---------";
            select.replaceChildren(new Option(blank, ""));
            library.forEach((image) => select.append(new Option(image.name, image.id)));
            select.value = value;
            updateControlPreview(select);
        });
    };

    const renderLibrary = () => {
        grid.replaceChildren();
        if (!library.length) {
            grid.innerHTML = '<p class="media-empty">No images have been uploaded yet.</p>';
            return;
        }
        library.forEach((image) => {
            const item = document.createElement("button");
            item.type = "button";
            item.className = "media-library-item";
            if (activeSelect && String(image.id) === activeSelect.value) item.classList.add("is-selected");
            item.innerHTML = `<img src="${image.url}" alt=""><strong></strong><small>${image.type} &middot; ${image.dimensions} &middot; ${formatSize(image.size)}</small>`;
            item.querySelector("strong").textContent = image.name;
            item.addEventListener("click", () => {
                activeSelect.value = String(image.id);
                activeSelect.dispatchEvent(new Event("change", {bubbles: true}));
                updateControlPreview(activeSelect);
                dialog.close();
            });
            grid.append(item);
        });
    };

    const loadLibrary = async () => {
        const response = await fetch(libraryUrl, {headers: {"X-Requested-With": "XMLHttpRequest"}});
        if (!response.ok) throw new Error("The image library could not be loaded.");
        library = (await response.json()).images;
        refreshSelects();
        renderLibrary();
    };

    const renderUploadState = () => {
        const valid = pending.filter((entry) => !entry.error && entry.name.trim());
        const invalid = pending.filter((entry) => entry.error || !entry.name.trim());
        uploadButton.disabled = !valid.length;
        uploadButton.textContent = valid.length ? `Upload ${valid.length} image${valid.length === 1 ? "" : "s"}` : "Upload";
        uploadSummary.textContent = pending.length ? `${valid.length} ready, ${invalid.length} not ready` : "";
    };

    const renderPending = () => {
        uploadList.replaceChildren();
        if (!pending.length) uploadList.innerHTML = '<p class="media-empty">No files selected.</p>';
        pending.forEach((entry) => {
            const row = document.createElement("div");
            row.className = `media-upload-row ${entry.error ? "is-invalid" : "is-valid"}`;
            const preview = entry.preview ? `<img src="${entry.preview}" alt="">` : '<span class="media-file-placeholder">&times;</span>';
            row.innerHTML = `${preview}<div class="media-upload-details"><strong></strong><small>${formatSize(entry.file.size)}</small>${entry.error ? '<p class="media-error"></p>' : '<label>Name<input type="text" maxlength="120"></label>'}</div><span class="media-validity">${entry.error ? "&times;" : "&#10003;"}</span>`;
            row.querySelector("strong").textContent = entry.file.name;
            if (entry.error) row.querySelector(".media-error").textContent = entry.error;
            else {
                const nameInput = row.querySelector("input");
                nameInput.value = entry.name;
                nameInput.addEventListener("input", () => { entry.name = nameInput.value; renderUploadState(); });
            }
            uploadList.append(row);
        });
        renderUploadState();
    };

    fileInput.addEventListener("change", () => {
        pending.forEach((entry) => { if (entry.preview) URL.revokeObjectURL(entry.preview); });
        pending = [...fileInput.files].map((file) => ({file, name: deriveName(file.name), error: compatible(file), preview: ""}));
        pending.forEach((entry) => { if (!entry.error) entry.preview = URL.createObjectURL(entry.file); });
        renderPending();
    });

    uploadButton.addEventListener("click", async () => {
        const valid = pending.filter((entry) => !entry.error && entry.name.trim());
        const data = new FormData();
        valid.forEach((entry) => { data.append("images", entry.file); data.append("names", entry.name.trim()); });
        uploadButton.disabled = true;
        uploadButton.textContent = "Uploading...";
        try {
            const response = await fetch(libraryUrl, {method: "POST", headers: {"X-CSRFToken": csrfToken, "X-Requested-With": "XMLHttpRequest"}, body: data});
            const result = await response.json();
            if (!response.ok) throw new Error(result.error || "Upload failed.");
            library = result.images;
            const failures = result.results.filter((item) => !item.ok);
            pending = failures.map((item) => ({file: {name: item.filename, size: 0}, name: "", error: item.error, preview: ""}));
            refreshSelects();
            if (!uploadOnly) renderLibrary();
            renderPending();
            uploadSummary.textContent = failures.length ? "Some files could not be uploaded." : "Upload complete.";
        } catch (error) {
            uploadSummary.textContent = error.message;
            renderUploadState();
        }
    });

    const openModal = async ({select = null, uploadsOnly = false} = {}) => {
        activeSelect = select;
        uploadOnly = uploadsOnly;
        resetPending();
        librarySection.hidden = uploadOnly;
        dialog.classList.toggle("is-upload-only", uploadOnly);
        modalTitle.textContent = uploadOnly ? "Upload images" : "Choose an image";
        modalIntroduction.textContent = uploadOnly ? "Choose one or more image files to add to the library." : "Select an existing image or upload new files.";
        if (!uploadOnly) await loadLibrary();
        dialog.showModal();
    };

    dialog.querySelector(".media-modal-close").addEventListener("click", () => dialog.close());
    dialog.addEventListener("click", (event) => { if (event.target === dialog) dialog.close(); });

    selects.forEach((select) => {
        const wrapper = document.createElement("div");
        wrapper.className = "media-picker-control";
        select.parentNode.insertBefore(wrapper, select);
        wrapper.append(select);
        const current = document.createElement("span");
        current.className = "media-picker-current";
        const choose = document.createElement("button");
        choose.type = "button";
        choose.className = "button media-picker-button";
        choose.textContent = "Select image";
        choose.addEventListener("click", async () => {
            try { await openModal({select}); } catch (error) { window.alert(error.message); }
        });
        const clear = document.createElement("button");
        clear.type = "button";
        clear.className = "button media-picker-clear";
        clear.textContent = "Clear";
        clear.disabled = !select.value;
        clear.addEventListener("click", () => {
            select.value = "";
            select.dispatchEvent(new Event("change", {bubbles: true}));
        });
        wrapper.append(current, choose, clear);
        select.addEventListener("change", () => updateControlPreview(select));
    });

    managerButton?.addEventListener("click", () => openModal({uploadsOnly: true}));
    loadLibrary().catch(() => {});

    const panels = [...document.querySelectorAll(".branding-image-panel")];
    if (panels.length) {
        const form = document.querySelector("#content-main form");
        const viewStateKey = `branding-image-view:${window.location.pathname}`;
        let lastSubmitter = null;
        form?.addEventListener("click", (event) => {
            const submitter = event.target.closest('button[type="submit"], input[type="submit"]');
            if (submitter) lastSubmitter = submitter;
        });
        form?.addEventListener("submit", (event) => {
            const submitter = event.submitter || lastSubmitter;
            if (submitter?.name !== "_continue") {
                sessionStorage.removeItem(viewStateKey);
                return;
            }
            sessionStorage.setItem(viewStateKey, JSON.stringify({
                scrollX: window.scrollX,
                scrollY: window.scrollY,
                openPanels: panels.filter((panel) => panel.open).map((panel) => panel.dataset.imagePanel),
            }));
        });
        try {
            const saved = sessionStorage.getItem(viewStateKey);
            if (saved) {
                sessionStorage.removeItem(viewStateKey);
                const state = JSON.parse(saved);
                panels.forEach((panel) => { panel.open = state.openPanels.includes(panel.dataset.imagePanel); });
                const restoreScroll = () => window.scrollTo(state.scrollX, state.scrollY);
                restoreScroll();
                requestAnimationFrame(restoreScroll);
                setTimeout(restoreScroll, 0);
            }
        } catch (_) {
            // The form remains fully usable when browser storage is unavailable.
        }
    }
});
