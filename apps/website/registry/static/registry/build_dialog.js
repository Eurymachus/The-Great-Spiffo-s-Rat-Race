(() => {
    const initialise = () => {
    "use strict";

    document.querySelectorAll(".character-build-traits-dialog .leaderboard-trait-column ul").forEach((list) => {
        if (list.dataset.tooltipReady) return;
        list.dataset.tooltipReady = "true";
        const position = (row) => {
            const tooltip = row.querySelector(".leaderboard-trait-tooltip");
            if (!tooltip) return;
            tooltip.style.bottom = "auto";
            tooltip.style.top = "calc(100% + .35rem)";
            const bounds = list.getBoundingClientRect();
            const item = row.getBoundingClientRect();
            const height = tooltip.getBoundingClientRect().height;
            const gap = 6;
            const below = bounds.bottom - item.bottom - gap;
            const above = item.top - bounds.top - gap;
            let top = below >= height || below >= above ? item.height + gap : -height - gap;
            top = Math.max(bounds.top - item.top + 2, Math.min(top, bounds.bottom - item.top - height - 2));
            tooltip.style.top = `${top}px`;
        };
        list.querySelectorAll("li[tabindex]").forEach((row) => {
            row.addEventListener("pointerenter", () => position(row));
            row.addEventListener("focus", () => position(row));
        });
        list.addEventListener("scroll", () => {
            const row = list.querySelector("li:hover, li:focus");
            if (row) position(row);
        });
    });

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
        if (container.dataset.buildTabsReady) return;
        container.dataset.buildTabsReady = "true";
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
    };
    document.addEventListener("page:loaded", initialise);
    initialise();
})();
