(() => {
    "use strict";

    const video = document.querySelector("[data-submission-video]");
    if (!video) return;

    const storageKey = `rat-race-admin-submission-video-${video.dataset.preferenceUser}-v1`;
    try {
        const saved = localStorage.getItem(storageKey);
        if (saved === "collapsed" || saved === "expanded") {
            video.open = saved === "expanded";
        }
    } catch {
        // The native disclosure remains usable when browser storage is unavailable.
    }

    video.addEventListener("toggle", () => {
        try {
            localStorage.setItem(storageKey, video.open ? "expanded" : "collapsed");
        } catch {
            // Storage restrictions must not prevent opening or closing the player.
        }
    });
})();
