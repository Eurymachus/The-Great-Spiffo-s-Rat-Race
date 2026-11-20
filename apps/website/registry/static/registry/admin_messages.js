(() => {
    "use strict";

    const list = document.querySelector(".messagelist");
    if (!list) return;
    const region = document.createElement("div");
    region.className = "admin-save-toast-region admin-message-toasts";
    region.setAttribute("aria-label", "Action messages");
    document.body.append(region);

    for (const message of [...list.children]) {
        const persistent = message.classList.contains("error") || message.classList.contains("warning");
        const type = message.classList.contains("error") ? "error"
            : message.classList.contains("warning") ? "warning"
            : message.classList.contains("success") ? "success" : "info";
        const toast = document.createElement("div");
        toast.className = `admin-save-toast is-${type}`;
        const copy = document.createElement("div");
        copy.className = "admin-message-copy";
        copy.setAttribute("role", persistent ? "alert" : "status");
        const close = document.createElement("button");
        close.type = "button";
        close.className = "admin-message-close";
        close.setAttribute("aria-label", "Dismiss message");
        close.textContent = "×";
        toast.append(copy, close);
        region.append(toast);
        // Preserve Django's escaped text and any deliberately supplied links.
        copy.append(...message.childNodes);
        let timer;
        const dismiss = () => {
            window.clearTimeout(timer);
            toast.remove();
            if (!region.children.length) region.remove();
        };
        const pause = () => window.clearTimeout(timer);
        const schedule = () => {
            pause();
            if (!persistent && !toast.matches(":hover") && !toast.contains(document.activeElement)) {
                timer = window.setTimeout(dismiss, 8000);
            }
        };
        close.addEventListener("click", dismiss);
        toast.addEventListener("mouseenter", pause);
        toast.addEventListener("mouseleave", schedule);
        toast.addEventListener("focusin", pause);
        toast.addEventListener("focusout", () => window.setTimeout(schedule, 0));
        requestAnimationFrame(() => toast.classList.add("is-visible"));
        schedule();
    }
    list.remove();
})();
