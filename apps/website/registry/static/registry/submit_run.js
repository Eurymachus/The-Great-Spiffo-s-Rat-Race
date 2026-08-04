(() => {
    "use strict";

    const blockedDialog = document.querySelector("[data-submission-blocked-dialog]");
    if (blockedDialog) {
        blockedDialog.querySelectorAll("[data-submission-blocked-close]").forEach((button) => {
            button.addEventListener("click", () => blockedDialog.close());
        });
        blockedDialog.addEventListener("click", (event) => {
            if (event.target === blockedDialog) blockedDialog.close();
        });
        if (typeof blockedDialog.showModal === "function") blockedDialog.showModal();
        else blockedDialog.setAttribute("open", "");
    }

    const refreshForm = document.querySelector("#refresh-streaming-media-form");
    const refreshButton = document.querySelector('[form="refresh-streaming-media-form"]');
    const providerInput = document.querySelector("#id_evidence_provider");
    const refreshProviderInput = refreshForm?.querySelector('[name="provider"]');
    const providerButtons = [...document.querySelectorAll("[data-evidence-provider]")];
    const videoSelect = document.querySelector("#id_evidence_video");
    const clipsRegion = document.querySelector("[data-evidence-clips]");
    const status = document.querySelector("[data-media-refresh-status]");
    if (!refreshForm || !refreshButton || !providerInput || !refreshProviderInput || !videoSelect || !clipsRegion || !status) return;

    const setStatus = (message, failed = false) => {
        status.textContent = message;
        status.hidden = false;
        status.classList.toggle("is-error", failed);
    };

    const replaceVideos = (videos) => {
        const selectedValue = videoSelect.value;
        videoSelect.replaceChildren(...videos.map(({value, label}) => {
            const option = document.createElement("option");
            option.value = value;
            option.textContent = label;
            option.selected = value === selectedValue;
            return option;
        }));
    };

    const replaceClips = (clips) => {
        const selectedValues = new Set(
            [...clipsRegion.querySelectorAll('input[type="checkbox"]:checked')]
                .map((input) => input.value)
        );
        clipsRegion.replaceChildren();
        if (!clips.length) return;

        const field = document.createElement("div");
        field.className = "field evidence-clips";
        const heading = document.createElement("label");
        heading.textContent = "Supporting clips";
        field.append(heading);

        const choices = document.createElement("div");
        choices.id = "id_evidence_clips";
        clips.forEach(({value, label}, index) => {
            const row = document.createElement("label");
            const checkbox = document.createElement("input");
            checkbox.type = "checkbox";
            checkbox.name = "evidence_clips";
            checkbox.value = value;
            checkbox.id = `id_evidence_clips_${index}`;
            checkbox.checked = selectedValues.has(value);
            row.append(checkbox, ` ${label}`);
            choices.append(row);
        });
        field.append(choices);
        clipsRegion.append(field);
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
            videoSelect.replaceChildren(new Option("Choose a broadcast or video", ""));
            clipsRegion.replaceChildren();
            refreshMedia();
        });
    });
})();
