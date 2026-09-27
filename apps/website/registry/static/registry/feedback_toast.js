// Immediate action feedback, separate from persistent live site notifications.
window.RatRaceToast = (() => {
    let dismissCurrent = () => {};
    document.addEventListener("page:before-change", () => dismissCurrent());
    return {
        show({message, type = "info", title, signal, duration = 7000}) {
            if (!["info", "error"].includes(type)) throw new Error("Invalid feedback toast type");
            dismissCurrent();
            if (signal?.aborted) return () => {};
            const region = document.createElement("div");
            region.className = "feedback-toast-region";
            const toast = document.createElement("div");
            toast.className = `feedback-toast feedback-toast--${type}`;
            const announcement = document.createElement("div");
            announcement.className = "feedback-toast-copy";
            announcement.setAttribute("role", type === "error" ? "alert" : "status");
            announcement.setAttribute("aria-atomic", "true");
            const icon = document.createElement("span");
            icon.className = "feedback-toast-icon";
            icon.setAttribute("aria-hidden", "true");
            icon.textContent = type === "error" ? "!" : "i";
            const close = document.createElement("button");
            close.type = "button";
            close.className = "feedback-toast-close";
            close.setAttribute("aria-label", "Dismiss message");
            close.textContent = "\u00d7";
            toast.append(icon, announcement, close);
            region.append(toast);
            // Render above a modal when feedback originates in one.
            const host = document.activeElement?.closest("dialog[open]") || document.body;
            host.append(region);
            let timer;
            let announceTimer;
            const dismiss = () => {
                clearTimeout(timer);
                clearTimeout(announceTimer);
                region.remove();
                signal?.removeEventListener("abort", dismiss);
                host.removeEventListener("close", dismiss);
                if (dismissCurrent === dismiss) dismissCurrent = () => {};
            };
            const schedule = () => {
                clearTimeout(timer);
                if (duration > 0) timer = setTimeout(dismiss, duration);
            };
            // Populate the mounted live region so repeated messages are announced.
            announceTimer = setTimeout(() => {
                const heading = document.createElement("strong");
                heading.textContent = title || (type === "error" ? "Something needs attention" : "Information");
                const detail = document.createElement("span");
                detail.textContent = message;
                announcement.append(heading, detail);
            }, 0);
            close.addEventListener("click", dismiss);
            toast.addEventListener("pointerenter", () => clearTimeout(timer));
            toast.addEventListener("pointerleave", schedule);
            toast.addEventListener("focusin", () => clearTimeout(timer));
            toast.addEventListener("focusout", schedule);
            host.addEventListener("close", dismiss);
            signal?.addEventListener("abort", dismiss, {once: true});
            dismissCurrent = dismiss;
            schedule();
            return dismiss;
        },
    };
})();
