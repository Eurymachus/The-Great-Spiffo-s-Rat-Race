(() => {
    "use strict";
    const dialog = document.querySelector("[data-development-dialog]");
    if (!dialog || typeof dialog.showModal !== "function") return;

    let trigger = null;
    document.querySelectorAll("a[data-development-modal]").forEach((link) => {
        link.addEventListener("click", (event) => {
            event.preventDefault();
            trigger = link;
            dialog.showModal();
            dialog.scrollTop = 0;
        });
    });
    dialog.querySelector("[data-development-close]").addEventListener("click", () => {
        dialog.close();
    });
    dialog.addEventListener("click", (event) => {
        if (event.target === dialog) dialog.close();
    });
    dialog.addEventListener("close", () => {
        trigger?.focus();
    });
})();
