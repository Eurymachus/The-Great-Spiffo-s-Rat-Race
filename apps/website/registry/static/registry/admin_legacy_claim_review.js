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
        if (dialog.hasAttribute("data-claim-auto-open")) dialog.showModal();
    });
});
