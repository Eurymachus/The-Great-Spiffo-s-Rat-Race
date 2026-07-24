(() => {
    "use strict";
    document.querySelectorAll(".run-detail-modal").forEach((dialog) => {
        const triggers = document.querySelectorAll(
            `[data-run-detail-open="${dialog.id}"]`
        );
        if (!dialog || typeof dialog.showModal !== "function") return;
        const close = dialog.querySelector("[data-run-detail-close]");
        let activeTrigger = null;
        triggers.forEach((trigger) => {
            trigger.addEventListener("click", () => {
                activeTrigger = trigger;
                dialog.showModal();
            });
        });
        close?.addEventListener("click", () => dialog.close());
        dialog.addEventListener("click", (event) => {
            if (event.target === dialog) dialog.close();
        });
        dialog.addEventListener("close", () => activeTrigger?.focus());
    });
})();
