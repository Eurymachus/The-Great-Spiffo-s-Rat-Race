(() => {
    "use strict";

    const activateTab = (container, tab) => {
        const name = tab.dataset.buildTab;
        const tabs = [...container.querySelectorAll("[data-build-tab]")];
        const panels = [...container.querySelectorAll("[data-build-tab-panel]")];
        tabs.forEach((candidate) => {
            const active = candidate === tab;
            candidate.setAttribute("aria-selected", String(active));
            candidate.tabIndex = active ? 0 : -1;
        });
        panels.forEach((panel) => {
            panel.hidden = panel.dataset.buildTabPanel !== name;
        });
        tab.focus();
    };

    document.querySelectorAll("[data-build-tabs]").forEach((container) => {
        const tabs = [...container.querySelectorAll("[data-build-tab]")];
        tabs.forEach((tab, index) => {
            tab.addEventListener("click", () => activateTab(container, tab));
            tab.addEventListener("keydown", (event) => {
                if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
                event.preventDefault();
                let targetIndex = index;
                if (event.key === "ArrowLeft") targetIndex = (index - 1 + tabs.length) % tabs.length;
                if (event.key === "ArrowRight") targetIndex = (index + 1) % tabs.length;
                if (event.key === "Home") targetIndex = 0;
                if (event.key === "End") targetIndex = tabs.length - 1;
                activateTab(container, tabs[targetIndex]);
            });
        });
    });
})();
