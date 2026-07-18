document.addEventListener("DOMContentLoaded", () => {
    const selects = [...document.querySelectorAll("select.media-library-select")];
    const managerButton = document.querySelector("[data-media-library-manager]");
    if (!selects.length && !managerButton) return;

    const libraryUrl = selects[0]?.dataset.libraryUrl || managerButton.dataset.mediaLibraryManager;
    const csrfToken = document.querySelector('[name="csrfmiddlewaretoken"]')?.value || "";
    let activeSelect = null;
    let library = [];
    let pending = [];

    const dialog = document.createElement("dialog");
    dialog.className = "media-library-dialog";
    dialog.innerHTML = `
        <div class="media-library-modal">
            <header><div><h2>Choose an image</h2><p>Select an existing image or upload new files.</p></div><button type="button" class="media-modal-close" aria-label="Close">×</button></header>
            <div class="media-library-grid" data-media-grid></div>
            <section class="media-upload-panel">
                <div class="media-upload-heading"><div><h3>Upload images</h3><p>PNG, JPEG, WebP or ICO, up to 5 MB each.</p></div><label class="button media-choose-files">Choose files<input type="file" accept=".png,.jpg,.jpeg,.webp,.ico,image/png,image/jpeg,image/webp,image/x-icon" multiple hidden></label></div>
                <div class="media-upload-list" data-upload-list><p class="media-empty">No files selected.</p></div>
                <div class="media-upload-actions"><span data-upload-summary></span><button type="button" class="button media-upload-button" disabled>Upload</button></div>
            </section>
        </div>`;
    document.body.append(dialog);

    const grid = dialog.querySelector("[data-media-grid]");
    const fileInput = dialog.querySelector('input[type="file"]');
    const uploadList = dialog.querySelector("[data-upload-list]");
    const uploadButton = dialog.querySelector(".media-upload-button");
    const uploadSummary = dialog.querySelector("[data-upload-summary]");

    const formatSize = (bytes) => bytes < 1024 * 1024 ? `${(bytes / 1024).toFixed(1)} KB` : `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    const deriveName = (filename) => filename.replace(/\.[^.]+$/, "").replace(/[-_]+/g, " ").replace(/\s+/g, " ").trim().replace(/\b\w/g, (letter) => letter.toUpperCase());
    const compatible = (file) => {
        const extension = file.name.split(".").pop().toLowerCase();
        if (!["png", "jpg", "jpeg", "webp", "ico"].includes(extension)) return "This file type is not supported.";
        if (file.size > 5 * 1024 * 1024) return "This file is larger than 5 MB.";
        return "";
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

    const updateControlPreview = (select) => {
        const preview = select.closest(".media-picker-control")?.querySelector(".media-picker-current");
        if (!preview) return;
        const image = library.find((candidate) => String(candidate.id) === select.value);
        preview.innerHTML = image ? `<img src="${image.url}" alt=""><span>${image.name}</span>` : `<span>No image selected</span>`;
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
            item.innerHTML = `<img src="${image.url}" alt=""><strong></strong><small>${image.type} · ${image.dimensions} · ${formatSize(image.size)}</small>`;
            item.querySelector("strong").textContent = image.name;
            item.addEventListener("click", () => {
                if (!activeSelect) {
                    window.open(image.url, "_blank", "noopener,noreferrer");
                    return;
                }
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

    const renderPending = () => {
        uploadList.replaceChildren();
        if (!pending.length) uploadList.innerHTML = '<p class="media-empty">No files selected.</p>';
        pending.forEach((entry, index) => {
            const row = document.createElement("div");
            row.className = `media-upload-row ${entry.error ? "is-invalid" : "is-valid"}`;
            const preview = entry.preview ? `<img src="${entry.preview}" alt="">` : '<span class="media-file-placeholder">×</span>';
            row.innerHTML = `${preview}<div class="media-upload-details"><strong></strong><small>${formatSize(entry.file.size)}</small>${entry.error ? '<p class="media-error"></p>' : '<label>Name<input type="text" maxlength="120"></label>'}</div><span class="media-validity">${entry.error ? "×" : "✓"}</span>`;
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

    const renderUploadState = () => {
        const valid = pending.filter((entry) => !entry.error && entry.name.trim());
        const invalid = pending.filter((entry) => entry.error || !entry.name.trim());
        uploadButton.disabled = !valid.length;
        uploadButton.textContent = valid.length ? `Upload ${valid.length} image${valid.length === 1 ? "" : "s"}` : "Upload";
        uploadSummary.textContent = pending.length ? `${valid.length} ready, ${invalid.length} not ready` : "";
    };

    fileInput.addEventListener("change", async () => {
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
        uploadButton.textContent = "Uploading…";
        try {
            const response = await fetch(libraryUrl, {method: "POST", headers: {"X-CSRFToken": csrfToken, "X-Requested-With": "XMLHttpRequest"}, body: data});
            const result = await response.json();
            if (!response.ok) throw new Error(result.error || "Upload failed.");
            library = result.images;
            const failures = result.results.filter((item) => !item.ok);
            pending = failures.map((item) => ({file: {name: item.filename, size: 0}, name: "", error: item.error, preview: ""}));
            refreshSelects();
            renderLibrary();
            renderPending();
            uploadSummary.textContent = failures.length ? "Some files could not be uploaded." : "Upload complete. Choose an image above.";
        } catch (error) {
            uploadSummary.textContent = error.message;
            renderUploadState();
        }
    });

    dialog.querySelector(".media-modal-close").addEventListener("click", () => dialog.close());
    dialog.addEventListener("click", (event) => { if (event.target === dialog) dialog.close(); });

    selects.forEach((select) => {
        const wrapper = document.createElement("div");
        wrapper.className = "media-picker-control";
        select.parentNode.insertBefore(wrapper, select);
        wrapper.append(select);
        const current = document.createElement("span"); current.className = "media-picker-current";
        const choose = document.createElement("button"); choose.type = "button"; choose.className = "button media-picker-button"; choose.textContent = "Choose image";
        choose.addEventListener("click", async () => {
            activeSelect = select;
            try { await loadLibrary(); dialog.showModal(); } catch (error) { window.alert(error.message); }
        });
        wrapper.append(current, choose);
        select.addEventListener("change", () => updateControlPreview(select));
    });

    managerButton?.addEventListener("click", async () => {
        activeSelect = null;
        try { await loadLibrary(); dialog.showModal(); } catch (error) { window.alert(error.message); }
    });

    loadLibrary().catch(() => {});
});
