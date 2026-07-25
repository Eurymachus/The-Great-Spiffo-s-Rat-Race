(() => {
    "use strict";
    const dialog = document.querySelector("[data-connection-dialog]");
    if (!dialog || typeof dialog.showModal !== "function") return;

    const title = dialog.querySelector("[data-connection-title]");
    const kicker = dialog.querySelector("[data-connection-kicker]");
    const copy = dialog.querySelector("[data-connection-copy]");
    const note = dialog.querySelector("[data-connection-note]");
    const icon = dialog.querySelector("[data-connection-icon]");
    const confirm = dialog.querySelector("[data-connection-confirm]");
    let pendingTarget = null;
    let trigger = null;

    const providerIcon = (provider) => {
        const image = document.querySelector(
            `.streaming-provider-icon-${provider} img`
        );
        if (!image) return "";
        return `<span class="streaming-provider-icon" aria-hidden="true"><img src="${image.src}" alt=""></span>`;
    };

    const openDialog = (target) => {
        const action = target.dataset.connectionAction;
        const provider = target.dataset.connectionProvider;
        const label = target.dataset.connectionLabel;
        const isDisconnect = action === "disconnect";
        const isReconnect = action === "reconnect";

        pendingTarget = target;
        trigger = target.matches("form")
            ? target.querySelector("button[type='submit']")
            : target;
        kicker.textContent = label;
        title.textContent = isDisconnect
            ? `Disconnect ${label}?`
            : `${isReconnect ? "Reconnect" : "Connect"} ${label}`;
        icon.innerHTML = providerIcon(provider);
        copy.textContent = isDisconnect
            ? `This will revoke ${label} access and completely remove the connection from your Rat Race account.`
            : `You’ll continue to ${label} to confirm this connection on its official authorization page.`;
        note.textContent = isDisconnect
            ? "Cached provider media will be removed. Evidence already attached to submitted runs remains preserved."
            : provider === "discord"
            ? "The Rat Race requests only your basic Discord identity. It cannot inspect servers, read messages or install a bot."
            : "The Rat Race uses this connection to confirm your Twitch channel and let you select recent broadcasts or clips as submission evidence.";
        confirm.textContent = isDisconnect
            ? "Disconnect"
            : `Continue to ${label}`;
        confirm.classList.toggle("is-danger", isDisconnect);
        dialog.showModal();
    };

    document.querySelectorAll("[data-connection-action]").forEach((target) => {
        const eventName = target.matches("form") ? "submit" : "click";
        target.addEventListener(eventName, (event) => {
            event.preventDefault();
            openDialog(target);
        });
    });

    confirm.addEventListener("click", () => {
        if (!pendingTarget) return;
        if (pendingTarget.matches("form")) {
            pendingTarget.submit();
        } else {
            window.location.assign(pendingTarget.href);
        }
    });
    dialog.querySelector("[data-connection-close]").addEventListener("click", () => dialog.close());
    dialog.querySelector("[data-connection-cancel]").addEventListener("click", () => dialog.close());
    dialog.addEventListener("click", (event) => {
        if (event.target === dialog) dialog.close();
    });
    dialog.addEventListener("close", () => {
        pendingTarget = null;
        trigger?.focus();
    });
})();
