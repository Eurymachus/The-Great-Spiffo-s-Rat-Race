document.addEventListener("DOMContentLoaded", () => {
    let trigger = null;
    document.querySelectorAll("[data-claim-open]").forEach(link => {
        link.addEventListener("click", event => {
            const dialog = document.getElementById(link.dataset.claimOpen);
            if (!dialog) return;
            event.preventDefault();
            trigger = link;
            dialog.showModal();
        });
    });
    document.querySelectorAll(".claim-detail-dialog").forEach(dialog => {
        dialog.querySelector("[data-claim-close]").addEventListener("click", () => dialog.close());
        dialog.addEventListener("click", event => {
            if (event.target !== dialog) return;
            const rect = dialog.getBoundingClientRect();
            if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) dialog.close();
        });
        dialog.addEventListener("close", () => { trigger?.focus(); });
        const decisionForm = dialog.querySelector("[data-claim-decision-form]");
        const reasonDialog = dialog.querySelector(".claim-reason-dialog");
        if (decisionForm && reasonDialog) {
            const note = decisionForm.elements.review_note;
            const reason = reasonDialog.querySelector("textarea");
            decisionForm.addEventListener("submit", event => {
                if (!event.submitter?.hasAttribute("data-claim-decline")) return;
                decisionForm.elements.reason.value = note.value.trim();
                if (!decisionForm.elements.reason.value) {
                    event.preventDefault();
                    reasonDialog.showModal();
                }
            });
            reasonDialog.querySelector(".claim-reason-cancel").addEventListener("click", () => reasonDialog.close());
            reason.addEventListener("input", () => reason.setCustomValidity(""));
            reasonDialog.querySelector("form").addEventListener("submit", event => {
                if (!reason.value.trim()) {
                    event.preventDefault();
                    reason.setCustomValidity("Enter a reason for declining this claim.");
                    reason.reportValidity();
                }
            });
            reasonDialog.addEventListener("close", event => {
                event.stopPropagation();
                if (reason.value.trim()) note.value = reason.value;
                decisionForm.querySelector("[data-claim-decline]").focus();
            });
        }
        if (dialog.hasAttribute("data-claim-auto-open")) dialog.showModal();
    });
});
