(() => {
    "use strict";
    const wrapper = document.querySelector("[data-registration-form]");
    if (!wrapper) return;

    const panels = [...wrapper.querySelectorAll("[data-registration-step]")];
    const markers = [...wrapper.querySelectorAll("[data-step-marker]")];
    const status = wrapper.querySelector("[data-current-step]");
    const back = wrapper.querySelector("[data-step-back]");
    const next = wrapper.querySelector("[data-step-next]");
    const submit = wrapper.querySelector("[data-step-submit]");
    let current = Number(wrapper.dataset.startStep) || 1;

    const show = (step, shouldScroll = true) => {
        current = Math.max(1, Math.min(3, step));
        panels.forEach((panel) => { panel.hidden = Number(panel.dataset.registrationStep) !== current; });
        markers.forEach((marker) => {
            const markerStep = Number(marker.dataset.stepMarker);
            marker.classList.toggle("is-current", markerStep === current);
            marker.classList.toggle("is-complete", markerStep < current);
        });
        status.textContent = current;
        back.hidden = current === 1;
        next.hidden = current === 3;
        submit.hidden = current !== 3;
        if (shouldScroll) wrapper.scrollIntoView({behavior: "smooth", block: "start"});
    };

    const currentPanelIsValid = () => {
        const fields = panels[current - 1].querySelectorAll("input, select, textarea");
        if (current === 2) {
            const password = wrapper.querySelector("[name='password']");
            const confirmation = wrapper.querySelector("[name='password_confirmation']");
            confirmation.setCustomValidity(
                password.value === confirmation.value ? "" : "The passwords do not match."
            );
        }
        for (const field of fields) {
            if (!field.reportValidity()) return false;
        }
        return true;
    };

    next.addEventListener("click", () => {
        if (currentPanelIsValid()) show(current + 1);
    });
    back.addEventListener("click", () => show(current - 1));
    wrapper.querySelector("[name='password_confirmation']").addEventListener("input", (event) => {
        event.currentTarget.setCustomValidity("");
    });
    show(current, false);
})();
