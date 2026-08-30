(() => {
    "use strict";

    const sidebar = document.querySelector("#nav-sidebar");
    if (!sidebar) return;

    const storageKey = "rat-race-admin-sidebar-sections-v1";
    let savedState = {};

    try {
        savedState = JSON.parse(localStorage.getItem(storageKey) || "{}");
    } catch {
        savedState = {};
    }

    const saveState = () => {
        try {
            localStorage.setItem(storageKey, JSON.stringify(savedState));
        } catch {
            // Collapsing still works when browser storage is unavailable.
        }
    };

    const setExpanded = (module, button, expanded) => {
        module.classList.toggle("is-collapsed", !expanded);
        button.setAttribute("aria-expanded", String(expanded));
    };

    sidebar.querySelectorAll(".admin-sidebar-section-toggle").forEach((button) => {
        const module = button.closest(".module");
        const section = button.dataset.adminSidebarSection;
        if (!module || !section) return;

        const isCurrent = module.classList.contains("current-app");
        const expanded = isCurrent || savedState[section] === true;
        setExpanded(module, button, expanded);

        button.addEventListener("click", () => {
            const nextExpanded = button.getAttribute("aria-expanded") !== "true";
            setExpanded(module, button, nextExpanded);
            savedState[section] = nextExpanded;
            saveState();
        });
    });

    document.documentElement.classList.remove("admin-nav-sidebar-open");
    document.querySelector("#admin-sidebar-prepaint")?.remove();

    const filter = sidebar.querySelector("#nav-filter");
    if (filter) {
        const updateFilteringState = () => {
            sidebar.classList.toggle("is-filtering", filter.value.trim().length > 0);
        };
        filter.addEventListener("input", updateFilteringState);
        updateFilteringState();
    }
})();
