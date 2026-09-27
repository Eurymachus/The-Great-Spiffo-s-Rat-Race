window.RatRacePages.register((pageSignal) => {
    "use strict";

    const exportTextarea = document.querySelector("#id_run_export");
    const exportFileInput = document.querySelector("[data-export-file-input]");
    const exportDropzone = document.querySelector("[data-export-dropzone]");
    const exportStatus = document.querySelector("[data-export-file-status]");
    const exportStatusMessage = document.querySelector("[data-export-file-status-message]");
    const exportPathChoose = document.querySelector("[data-export-path-choose]");
    const exportPaste = document.querySelector("[data-export-paste]");
    const maximumExportBytes = 24 * 1024 * 1024;

    const submissionForm = document.querySelector("[data-run-submission-form]");
    const vodInput = submissionForm?.querySelector("#id_manual_evidence_url");
    const vodHelper = submissionForm?.querySelector("[data-vod-helper]");
    let showSubmissionFieldError;
    let clearSubmissionFieldError;
    if (vodInput && vodHelper) {
        // Match the supported formats in vod_evidence.parse_vod_url.
        const isVodUrl = (value) => {
            try {
                if (/\\/.test(value)) return false;
                const url = new URL(value.trim());
                if (url.protocol !== "https:" || url.username || url.password || url.port) return false;
                if (["twitch.tv", "www.twitch.tv", "m.twitch.tv"].includes(url.hostname)) {
                    return /^\/videos\/[0-9]+\/?$/.test(url.pathname);
                }
                let id = "";
                if (["youtube.com", "www.youtube.com", "m.youtube.com"].includes(url.hostname)) {
                    const ids = url.pathname === "/watch" ? url.searchParams.getAll("v").filter(Boolean) : [];
                    id = ids.length === 1 ? ids[0] : (url.pathname.match(/^\/live\/([A-Za-z0-9_-]{11})\/?$/)?.[1] || "");
                } else if (url.hostname === "youtu.be") id = url.pathname.replace(/^\/+|\/+$/g, "");
                return /^[A-Za-z0-9_-]{11}$/.test(id);
            } catch { return false; }
        };
        const serverError = submissionForm.querySelector(".errorlist");
        const serverErrorField = serverError?.closest(".field, .submission-export-input")?.querySelector("textarea, input:not([type=hidden]):not([type=file]), select");
        const popup = window.RatRaceHint.create({
            anchor: vodInput, element: vodHelper, placement: "bottom", signal: pageSignal,
        });
        const describedBy = vodInput.getAttribute("aria-describedby") || "";
        vodInput.setAttribute("aria-describedby", `${describedBy} vod-validation-helper`.trim());
        let typingTimer;
        const revealError = (field) => {
            if (!field) return;
            const details = field.closest("details");
            if (details) details.open = true;
            field.focus({preventScroll: true});
            field.scrollIntoView({block: "center", behavior: "auto"});
        };
        const fieldHints = new Map();
        const showFieldError = (field, message = field.validationMessage) => {
            if (!field || field === vodInput) return;
            if (!field.matches("input, textarea, select, button")) field.tabIndex = -1;
            let entry = fieldHints.get(field);
            if (!entry) {
                const helper = document.createElement("div");
                helper.id = `${field.id || "submission"}-validation`;
                helper.setAttribute("role", "status");
                const label = document.createElement("span");
                const close = document.createElement("button");
                close.type = "button";
                close.dataset.hintClose = "";
                close.textContent = "\u00d7";
                close.setAttribute("aria-label", "Dismiss validation hint");
                helper.append(label, close);
                field.setAttribute("aria-describedby", `${field.getAttribute("aria-describedby") || ""} ${helper.id}`.trim());
                entry = {label, popup: window.RatRaceHint.create({
                    anchor: field, element: helper, placement: "bottom", signal: pageSignal,
                })};
                fieldHints.set(field, entry);
            }
            entry.label.textContent = message;
            field.setAttribute("aria-invalid", "true");
            entry.popup.show();
        };
        const clearFieldError = (field) => {
            fieldHints.get(field)?.popup.hide();
            field?.removeAttribute("aria-invalid");
        };
        showSubmissionFieldError = showFieldError;
        clearSubmissionFieldError = clearFieldError;
        // Keep server messages as a no-JavaScript fallback, then float them by
        // their visible control (media selects themselves are visually hidden).
        const serverFields = [];
        submissionForm.querySelectorAll("[data-field-errors]").forEach((errors) => {
            if (!errors.textContent.trim()) return;
            const name = errors.dataset.fieldErrors;
            const selector = {
                evidence_video: "[data-video-picker]",
                evidence_provider: ".submission-provider-selector",
                evidence_clips: "[data-clips-open]",
            }[name] || `#id_${name}`;
            const field = submissionForm.querySelector(selector) || vodInput;
            if (!field.matches("input, textarea, select, button")) field.tabIndex = -1;
            const message = errors.textContent.trim();
            errors.hidden = true;
            serverFields.push({field, message});
            let unresolved = true;
            field.addEventListener("focus", () => { if (unresolved) showFieldError(field, message); });
            field.addEventListener("input", () => { unresolved = false; clearFieldError(field); });
            field.addEventListener("change", () => { unresolved = false; clearFieldError(field); });
        });
        const notifyErrors = (field) => {
            revealError(field);
            window.RatRaceToast.show({
                type: "error", title: "Check your submission",
                message: "Please correct the highlighted errors.", signal: pageSignal,
            });
        };
        const validateVod = () => {
            clearTimeout(typingTimer);
            const invalid = Boolean(vodInput.value.trim()) && !isVodUrl(vodInput.value);
            const serverErrors = vodHelper.querySelector("[data-vod-server-errors]");
            const hasServerError = Boolean(serverErrors?.textContent.trim());
            if (invalid || hasServerError) popup.show(); else popup.hide();
            vodInput.setAttribute("aria-invalid", String(invalid || hasServerError));
            vodInput.setCustomValidity(invalid ? "Enter a valid Twitch or YouTube VOD link." : "");
            return !invalid;
        };
        vodInput.addEventListener("input", () => {
            vodHelper.querySelector("[data-vod-server-errors]")?.replaceChildren();
            vodInput.setCustomValidity("");
            clearTimeout(typingTimer);
            typingTimer = setTimeout(validateVod, 500);
        });
        vodInput.addEventListener("blur", validateVod);
        // Handle native constraints ourselves so hidden export fields can be revealed.
        submissionForm.noValidate = true;
        submissionForm.addEventListener("submit", (event) => {
            validateVod();
            const invalid = [...submissionForm.elements].find((field) => field.willValidate && !field.validity.valid);
            if (invalid) {
                event.preventDefault();
                invalid.setAttribute("aria-invalid", "true");
                notifyErrors(invalid);
                showFieldError(invalid);
            }
        });
        submissionForm.addEventListener("input", (event) => {
            if (event.target !== vodInput && event.target.validity?.valid) {
                clearFieldError(event.target);
            }
        });
        if (serverError && !document.querySelector("[data-submission-blocked-dialog]")) {
            const field = serverFields[0]?.field || serverErrorField;
            if (field) field.setAttribute("aria-invalid", "true");
            notifyErrors(field || vodInput);
            if (serverFields.length) showFieldError(serverFields[0].field, serverFields[0].message);
            validateVod();
        }
        pageSignal.addEventListener("abort", () => {
            clearTimeout(typingTimer);
        }, {once: true});
    }

    const showExportStatus = (message, failed = false, showPathAction = false) => {
        if (failed && showSubmissionFieldError && exportFileInput) {
            exportStatus.hidden = true;
            showSubmissionFieldError(document.querySelector(".submission-export-choose") || exportFileInput, message);
            return;
        }
        if (exportFileInput) clearSubmissionFieldError?.(document.querySelector(".submission-export-choose") || exportFileInput);
        if (!exportStatus) return;
        if (exportStatusMessage) exportStatusMessage.textContent = message;
        exportStatus.hidden = false;
        exportStatus.classList.toggle("is-error", failed);
        exportStatus.classList.toggle("is-path-help", showPathAction);
        if (exportPathChoose) exportPathChoose.hidden = !showPathAction;
    };

    const normalisePastedPath = (value) => {
        const trimmed = value.trim().replace(/^(["'])(.*)\1$/, "$2");
        const drivePath = /^[a-z]:[\\/].+\.txt$/i;
        const networkPath = /^\\\\[^\\]+\\.+\.txt$/i;
        return drivePath.test(trimmed) || networkPath.test(trimmed) ? trimmed : "";
    };

    const loadExportFile = async (file) => {
        if (!file || !exportTextarea) return;
        if (!file.name.toLowerCase().endsWith(".txt")) {
            showExportStatus("Choose the .txt file created by the Rat Race tracker.", true);
            return;
        }
        if (file.size > maximumExportBytes) {
            showExportStatus("The export file must be no larger than 24 MB.", true);
            return;
        }
        try {
            const value = await file.text();
            if (!value.trim()) throw new Error("The selected export file is empty.");
            exportTextarea.value = value;
            exportTextarea.dispatchEvent(new Event("input", {bubbles: true}));
            showExportStatus(
                `${file.name} loaded, ${value.length.toLocaleString()} characters. Ready for verification.`
            );
            if (exportPaste) exportPaste.open = false;
        } catch (error) {
            showExportStatus(error.message || "The export file could not be read.", true);
        }
    };

    exportFileInput?.addEventListener("change", () => {
        loadExportFile(exportFileInput.files?.[0]);
    });
    exportPathChoose?.addEventListener("click", () => exportFileInput?.click());
    document.addEventListener("paste", (event) => {
        if (!exportTextarea) return;
        const target = event.target;
        const isUnrelatedField =
            (target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement) &&
            target !== exportTextarea;
        if (isUnrelatedField) return;
        const pastedPath = normalisePastedPath(event.clipboardData?.getData("text/plain") || "");
        if (!pastedPath) return;
        event.preventDefault();
        showExportStatus(
            "Windows export path detected. Open the file chooser, paste this path into the File name field, then press Enter.",
            false,
            true
        );
    }, {signal: pageSignal});
    ["dragenter", "dragover"].forEach((eventName) => {
        exportDropzone?.addEventListener(eventName, (event) => {
            event.preventDefault();
            exportDropzone.classList.add("is-dragging");
        });
    });
    ["dragleave", "drop"].forEach((eventName) => {
        exportDropzone?.addEventListener(eventName, (event) => {
            event.preventDefault();
            exportDropzone.classList.remove("is-dragging");
        });
    });
    exportDropzone?.addEventListener("drop", (event) => {
        loadExportFile(event.dataTransfer?.files?.[0]);
    });
    exportTextarea?.form?.addEventListener("submit", () => {
        if (!exportTextarea.value.trim() && exportPaste) exportPaste.open = true;
    });

    const formatDuration = (seconds) => {
        const value = Number(seconds);
        if (!Number.isFinite(value) || value <= 0) return "";
        const hours = Math.floor(value / 3600);
        const minutes = Math.floor((value % 3600) / 60);
        const remainingSeconds = Math.floor(value % 60);
        if (hours) return `${hours}h ${minutes}m`;
        if (minutes) return `${minutes}m ${remainingSeconds}s`;
        return `${remainingSeconds}s`;
    };

    document.querySelectorAll("[data-duration-seconds]").forEach((element) => {
        element.textContent = formatDuration(element.dataset.durationSeconds);
    });

    const blockedDialog = document.querySelector("[data-submission-blocked-dialog]");
    if (blockedDialog) {
        blockedDialog.querySelectorAll("[data-submission-blocked-close]").forEach((button) => {
            button.addEventListener("click", () => blockedDialog.close());
        });
        blockedDialog.querySelectorAll("[data-submission-blocked-run]").forEach((button) => {
            button.addEventListener("click", () => blockedDialog.close());
        });
        blockedDialog.addEventListener("click", (event) => {
            if (event.target === blockedDialog) blockedDialog.close();
        });
        if (typeof blockedDialog.showModal === "function") blockedDialog.showModal();
        else blockedDialog.setAttribute("open", "");
    }

    const videoSelect = document.querySelector("#id_evidence_video");
    const videoPicker = document.querySelector("[data-video-picker]");
    const clipsRegion = document.querySelector("[data-evidence-clips]");
    const clipsPicker = document.querySelector("[data-clips-picker]");
    const clipsDialog = document.querySelector("[data-clips-dialog]");
    const clipsSummary = document.querySelector("[data-selected-clips-summary]");

    const updateVideoSelection = () => {
        if (!videoSelect || !videoPicker) return;
        videoPicker.querySelectorAll("[data-media-choice]").forEach((choice) => {
            const selected = choice.dataset.mediaValue === videoSelect.value;
            choice.classList.toggle("is-selected", selected);
            choice.setAttribute("aria-pressed", String(selected));
        });
    };

    const updateClipsSummary = () => {
        if (!clipsPicker || !clipsSummary) return;
        const selected = [...clipsPicker.querySelectorAll('input[type="checkbox"]:checked')];
        clipsSummary.textContent = selected.length
            ? `${selected.length} supporting clip${selected.length === 1 ? "" : "s"} selected.`
            : "No supporting clips selected.";
        clipsPicker.querySelectorAll(".submission-media-choice").forEach((choice) => {
            choice.classList.toggle("is-selected", choice.querySelector('input[type="checkbox"]')?.checked || false);
        });
    };

    videoPicker?.addEventListener("click", (event) => {
        const choice = event.target.closest("[data-media-choice]");
        if (!choice || !videoSelect) return;
        videoSelect.value = videoSelect.value === choice.dataset.mediaValue
            ? ""
            : choice.dataset.mediaValue || "";
        videoSelect.dispatchEvent(new Event("change", {bubbles: true}));
        updateVideoSelection();
    });

    clipsPicker?.addEventListener("change", updateClipsSummary);
    document.querySelector("[data-clips-open]")?.addEventListener("click", () => {
        if (typeof clipsDialog?.showModal === "function") clipsDialog.showModal();
        else clipsDialog?.setAttribute("open", "");
    });
    clipsDialog?.querySelectorAll("[data-clips-close]").forEach((button) => {
        button.addEventListener("click", () => clipsDialog.close());
    });
    clipsDialog?.addEventListener("click", (event) => {
        if (event.target === clipsDialog) clipsDialog.close();
    });
    updateVideoSelection();
    updateClipsSummary();

    const createThumbnail = (item) => {
        const thumbnail = document.createElement("span");
        thumbnail.className = "submission-media-thumbnail";
        if (item.thumbnail_url) {
            const image = document.createElement("img");
            image.src = item.thumbnail_url;
            image.alt = "";
            thumbnail.append(image);
        } else {
            const fallback = document.createElement("span");
            fallback.setAttribute("aria-hidden", "true");
            fallback.textContent = "No preview";
            thumbnail.append(fallback);
        }
        return thumbnail;
    };

    const createDetails = (item) => {
        const details = document.createElement("span");
        details.className = "submission-media-details";
        const title = document.createElement("strong");
        title.title = item.title || "Untitled media";
        const titleText = document.createElement("span");
        titleText.textContent = item.title || "Untitled media";
        title.append(titleText);
        const metadata = document.createElement("small");
        if (item.published_at) {
            const published = document.createElement("time");
            published.dateTime = item.published_at;
            published.textContent = new Intl.DateTimeFormat(undefined, {
                dateStyle: "medium", timeStyle: "short",
            }).format(new Date(item.published_at));
            metadata.append(published);
        }
        if (item.duration_seconds) {
            const duration = document.createElement("span");
            duration.textContent = formatDuration(item.duration_seconds);
            metadata.append(duration);
        }
        details.append(title, metadata);
        return details;
    };

    const prepareTitlePan = (event) => {
        const choice = event.target.closest(".submission-media-choice");
        const title = choice?.querySelector(".submission-media-details strong");
        const titleText = title?.querySelector(":scope > span");
        if (!title || !titleText) return;
        const overflow = Math.max(0, titleText.scrollWidth - title.clientWidth);
        choice.classList.toggle("has-overflowing-title", overflow > 2);
        choice.style.setProperty("--media-title-pan", `${-overflow}px`);
        choice.style.setProperty(
            "--media-title-pan-duration",
            `${Math.max(3.5, overflow / 24 + 2.5)}s`
        );
    };

    document.addEventListener("pointerover", prepareTitlePan, {signal: pageSignal});
    document.addEventListener("focusin", prepareTitlePan, {signal: pageSignal});

    const replaceVideos = (videos) => {
        if (!videoSelect) return;
        const selectedValue = videoSelect.value;
        videoSelect.replaceChildren(...videos.map((item) => {
            const option = document.createElement("option");
            option.value = item.value || "";
            option.textContent = item.title || item.label || "Choose a broadcast or video";
            option.selected = option.value === selectedValue;
            return option;
        }));
        if (!videoPicker) return;
        videoPicker.replaceChildren();
        const available = videos.filter((item) => item.value);
        if (!available.length) {
            const empty = document.createElement("p");
            empty.className = "submission-media-list-empty";
            empty.textContent = "No recent broadcasts or videos are available for this channel.";
            videoPicker.append(empty);
            return;
        }
        available.forEach((item) => {
            const choice = document.createElement("button");
            choice.type = "button";
            choice.className = "submission-media-choice";
            choice.dataset.mediaChoice = "";
            choice.dataset.mediaValue = item.value;
            choice.setAttribute("aria-pressed", "false");
            const selected = document.createElement("span");
            selected.className = "submission-media-selected";
            selected.setAttribute("aria-hidden", "true");
            selected.textContent = "Selected";
            choice.append(createThumbnail(item), createDetails(item), selected);
            videoPicker.append(choice);
        });
        updateVideoSelection();
    };

    const replaceClips = (clips) => {
        if (!clipsPicker) return;
        const selectedValues = new Set(
            [...clipsPicker.querySelectorAll('input[type="checkbox"]:checked')]
                .map((input) => input.value)
        );
        clipsPicker.replaceChildren();
        if (!clips.length) {
            const empty = document.createElement("p");
            empty.className = "submission-media-list-empty";
            empty.textContent = "No recent clips are available for this channel.";
            clipsPicker.append(empty);
            updateClipsSummary();
            return;
        }
        clips.forEach((item) => {
            const choice = document.createElement("label");
            choice.className = "submission-media-choice";
            const checkbox = document.createElement("input");
            checkbox.type = "checkbox";
            checkbox.name = "evidence_clips";
            checkbox.value = item.value;
            checkbox.checked = selectedValues.has(item.value);
            const selected = document.createElement("span");
            selected.className = "submission-media-selected";
            selected.setAttribute("aria-hidden", "true");
            selected.textContent = "Added";
            choice.append(checkbox, createThumbnail(item), createDetails(item), selected);
            clipsPicker.append(choice);
        });
        updateClipsSummary();
    };

    const refreshForm = document.querySelector("#refresh-streaming-media-form");
    const refreshButton = document.querySelector('[form="refresh-streaming-media-form"]');
    const providerInput = document.querySelector("#id_evidence_provider");
    const refreshProviderInput = refreshForm?.querySelector('[name="provider"]');
    const providerButtons = [...document.querySelectorAll("[data-evidence-provider]")];
    const status = document.querySelector("[data-media-refresh-status]");
    if (!refreshForm || !refreshButton || !providerInput || !refreshProviderInput || !videoSelect || !status) return;

    const setStatus = (message, failed = false) => {
        status.textContent = message;
        status.hidden = false;
        status.classList.toggle("is-error", failed);
    };

    const refreshMedia = async () => {
        const originalLabel = refreshButton.textContent;
        refreshButton.disabled = true;
        refreshButton.textContent = "Refreshing...";
        status.hidden = true;

        try {
            const response = await fetch(refreshForm.action, {
                method: "POST",
                body: new FormData(refreshForm),
                credentials: "same-origin",
                headers: {"X-Requested-With": "XMLHttpRequest"},
            });
            const payload = await response.json();
            if (!response.ok || !payload.ok) throw new Error(payload.message || "Streaming media could not be refreshed.");

            replaceVideos(payload.videos || []);
            replaceClips(payload.clips || []);
            document.querySelector("[data-media-refresh-empty]")?.remove();
            setStatus(payload.message);
        } catch (error) {
            setStatus(error.message || "Streaming media could not be refreshed.", true);
        } finally {
            refreshButton.disabled = false;
            refreshButton.textContent = originalLabel;
        }
    };

    refreshForm.addEventListener("submit", (event) => {
        event.preventDefault();
        refreshMedia();
    });

    providerButtons.forEach((button) => {
        button.addEventListener("click", () => {
            const provider = button.dataset.evidenceProvider;
            if (!provider || provider === providerInput.value) return;
            providerInput.value = provider;
            refreshProviderInput.value = provider;
            providerButtons.forEach((candidate) => {
                const selected = candidate === button;
                candidate.classList.toggle("is-selected", selected);
                candidate.setAttribute("aria-pressed", String(selected));
            });
            replaceVideos([{value: "", title: "Choose a broadcast or video"}]);
            replaceClips([]);
            refreshMedia();
        });
    });
});
