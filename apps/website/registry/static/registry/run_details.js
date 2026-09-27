(() => {
    "use strict";

    const localDateTimeFormatter = (includeSeconds = false) => new Intl.DateTimeFormat(
        undefined,
        {
            day: "numeric",
            month: "short",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit",
            ...(includeSeconds ? {second: "2-digit"} : {}),
        }
    );

    const localiseDateTimes = (root = document) => {
        root.querySelectorAll("[data-local-datetime]").forEach((time) => {
            const value = new Date(time.dateTime);
            if (Number.isNaN(value.getTime())) return;
            time.textContent = localDateTimeFormatter(
                time.hasAttribute("data-local-seconds")
            ).format(value);
            time.title = value.toLocaleString();
        });
    };

    const evidenceHintsDismissed = new Set();
    const showEvidenceHint = (dialog) => {
        const action = dialog.querySelector(".run-detail-evidence-button");
        if (!action) return;
        const key = `run-evidence-hint-dismissed:${dialog.id}`;
        if (evidenceHintsDismissed.has(key)) return;
        try { if (sessionStorage.getItem(key)) return; } catch (_) { /* Use in-memory state when storage is unavailable. */ }
        const hint = document.createElement("div");
        hint.setAttribute("role", "status");
        const label = document.createElement("span");
        label.textContent = action.getAttribute("aria-label");
        const dismiss = document.createElement("button");
        dismiss.type = "button";
        dismiss.textContent = "\u00d7";
        dismiss.dataset.hintClose = "";
        dismiss.setAttribute("aria-label", "Dismiss evidence helper");
        hint.append(label, dismiss);
        const popup = window.RatRaceHint.create({
            anchor: action, element: hint, placement: "top", container: dialog,
            onVisibility: (visible) => action.classList.toggle("has-evidence-helper", visible),
            onDismiss: () => {
                evidenceHintsDismissed.add(key);
                try { sessionStorage.setItem(key, "1"); } catch (_) { /* Keep dismissal in memory when storage is unavailable. */ }
                popup.destroy();
            },
        });
        action.addEventListener("click", popup.destroy, {once: true});
        action.scrollIntoView({block: "nearest", inline: "nearest"});
        popup.show();
    };

    const initialiseRunDialogs = (root = document) => {
        localiseDateTimes(root);
        root.querySelectorAll("[data-run-build-open]").forEach((trigger) => {
            if (trigger.dataset.runBuildReady) return;
            const dialog = document.getElementById(trigger.dataset.runBuildOpen);
            if (!dialog || typeof dialog.showModal !== "function") return;
            trigger.dataset.runBuildReady = "true";
            trigger.addEventListener("click", () => dialog.showModal());
            dialog.querySelector("[data-build-close]")?.addEventListener("click", () => dialog.close());
            dialog.addEventListener("click", (event) => {
                if (event.target === dialog) dialog.close();
            });
            dialog.addEventListener("close", () => trigger.focus());
        });
        root.querySelectorAll(".run-outpost-dialog").forEach((dialog) => {
            if (dialog.dataset.outpostDialogReady || typeof dialog.showModal !== "function") return;
            dialog.dataset.outpostDialogReady = "true";
            const triggers = root.querySelectorAll(`[data-outpost-dialog-open="${dialog.id}"]`);
            let activeTrigger = null;
            triggers.forEach((trigger) => trigger.addEventListener("click", () => {
                activeTrigger = trigger;
                dialog.showModal();
            }));
            dialog.querySelector("[data-outpost-dialog-close]")?.addEventListener("click", () => dialog.close());
            dialog.addEventListener("click", (event) => {
                if (event.target === dialog) dialog.close();
            });
            dialog.addEventListener("close", () => activeTrigger?.focus());
        });
        root.querySelectorAll(".run-skills-dialog").forEach((dialog) => {
            if (dialog.dataset.skillsDialogReady || typeof dialog.showModal !== "function") return;
            dialog.dataset.skillsDialogReady = "true";
            const triggers = root.querySelectorAll(`[data-skills-dialog-open="${dialog.id}"]`);
            let activeTrigger = null;
            triggers.forEach((trigger) => trigger.addEventListener("click", () => {
                activeTrigger = trigger;
                dialog.showModal();
            }));
            dialog.querySelector("[data-skills-dialog-close]")?.addEventListener("click", () => dialog.close());
            dialog.addEventListener("click", (event) => {
                if (event.target === dialog) dialog.close();
            });
            dialog.addEventListener("close", () => activeTrigger?.focus());
        });
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
                    showEvidenceHint(dialog);
                });
            });
            close?.addEventListener("click", () => dialog.close());
            dialog.addEventListener("click", (event) => {
                if (event.target === dialog) dialog.close();
            });
            dialog.addEventListener("close", () => activeTrigger?.focus());
        });
        root.querySelectorAll(".run-deactivate-modal").forEach((dialog) => {
            if (dialog.dataset.runDeactivateReady || typeof dialog.showModal !== "function") return;
            dialog.dataset.runDeactivateReady = "true";
            const triggers = root.querySelectorAll(
                `[data-run-deactivate-open="${dialog.id}"]`
            );
            let activeTrigger = null;
            triggers.forEach((trigger) => {
                trigger.addEventListener("click", () => {
                    activeTrigger = trigger;
                    trigger.closest(".run-detail-modal")?.close();
                    dialog.showModal();
                });
            });
            dialog.querySelectorAll("[data-run-deactivate-close]").forEach((close) => {
                close.addEventListener("click", () => dialog.close());
            });
            dialog.addEventListener("click", (event) => {
                if (event.target === dialog) dialog.close();
            });
            dialog.addEventListener("close", () => activeTrigger?.focus());

            const form = dialog.querySelector('form [name="return_to_submission"]')?.form;
            if (form) {
                form.addEventListener("submit", async (event) => {
                    event.preventDefault();
                    const submit = form.querySelector('[type="submit"]');
                    const originalLabel = submit?.textContent || "Deactivate permanently";
                    if (submit) {
                        submit.disabled = true;
                        submit.textContent = "Deactivating...";
                    }
                    try {
                        const response = await fetch(form.action, {
                            method: "POST",
                            body: new FormData(form),
                            credentials: "same-origin",
                            headers: {"Accept": "application/json"},
                        });
                        const payload = await response.json();
                        if (!response.ok || !payload.ok) {
                            throw new Error(payload.message || "The run could not be deactivated.");
                        }

                        dialog.close();
                        root.querySelector(`[data-run-detail-open="run-detail-${dialog.id.replace("run-deactivate-", "")}"]`)?.remove();
                        root.querySelector(`#${CSS.escape(dialog.id.replace("run-deactivate-", "run-detail-"))}`)?.remove();
                        root.querySelector("[data-submission-blocked-dialog]")?.remove();
                        root.querySelectorAll("form.stacked-form > .errorlist.nonfield").forEach((errors) => errors.remove());
                        const notice = document.createElement("p");
                        notice.className = "submission-deactivation-success";
                        notice.setAttribute("role", "status");
                        notice.textContent = payload.message;
                        root.querySelector(".run-submission-card > form")?.before(notice);
                        dialog.remove();
                    } catch (error) {
                        let errorMessage = dialog.querySelector("[data-run-deactivate-error]");
                        if (!errorMessage) {
                            errorMessage = document.createElement("p");
                            errorMessage.dataset.runDeactivateError = "";
                            errorMessage.className = "errorlist";
                            errorMessage.setAttribute("role", "alert");
                            form.before(errorMessage);
                        }
                        errorMessage.textContent = error.message || "The run could not be deactivated.";
                        if (submit) {
                            submit.disabled = false;
                            submit.textContent = originalLabel;
                        }
                    }
                });
            }
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

    document.addEventListener("page:loaded", () => initialiseRunDialogs());
    initialiseRunDialogs();
    document.addEventListener("notifications:changed", refreshDashboard);
})();
