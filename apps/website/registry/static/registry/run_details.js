(() => {
    "use strict";

    const initialiseRunDialogs = (root = document) => {
        root.querySelectorAll(".run-detail-modal").forEach((dialog) => {
            if (dialog.dataset.runDetailReady || typeof dialog.showModal !== "function") return;
            dialog.dataset.runDetailReady = "true";
            const triggers = root.querySelectorAll(
                `[data-run-detail-open="${dialog.id}"]`
            );
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
    };

    let dashboardRequest = null;
    const refreshDashboard = () => {
        const current = document.querySelector("[data-dashboard-live]");
        if (!current || dashboardRequest) return dashboardRequest;
        const openDialogId = current.querySelector(".run-detail-modal[open]")?.id;
        dashboardRequest = fetch(current.dataset.refreshUrl, {
            credentials: "same-origin",
            headers: {"Accept": "text/html"},
            cache: "no-store",
        })
            .then((response) => {
                if (!response.ok) throw new Error("Unable to refresh dashboard.");
                return response.text();
            })
            .then((html) => {
                const parsed = new DOMParser().parseFromString(html, "text/html");
                const replacement = parsed.querySelector("[data-dashboard-live]");
                if (!replacement || !current.isConnected) return;
                current.replaceWith(replacement);
                initialiseRunDialogs(replacement);
                if (openDialogId) {
                    replacement.querySelector(`#${CSS.escape(openDialogId)}`)?.showModal();
                }
            })
            .catch(() => {})
            .finally(() => {
                dashboardRequest = null;
            });
        return dashboardRequest;
    };

    initialiseRunDialogs();
    document.addEventListener("notifications:changed", refreshDashboard);
})();
