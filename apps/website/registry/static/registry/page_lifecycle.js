// Initialise page controls once per visit and release persistent listeners on departure.
window.RatRacePages = {
    register(initialise) {
        let controller;
        const run = () => {
            controller?.abort();
            controller = new AbortController();
            initialise(controller.signal);
        };
        document.addEventListener("page:before-change", () => controller?.abort());
        document.addEventListener("page:loaded", run);
        if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", run, {once: true});
        else run();
    },
};
