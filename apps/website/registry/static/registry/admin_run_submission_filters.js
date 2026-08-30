(() => {
    "use strict";

    const changelistPath = "/admin/registry/runsubmission/";
    if (window.location.pathname !== changelistPath) return;

    const storageKey = "ratRace.admin.runSubmission.filters.v1";
    const filterNames = new Set(["approval_state", "export_format"]);

    const filterQuery = (search) => {
        const source = new URLSearchParams(search);
        const filters = new URLSearchParams();
        source.forEach((value, name) => {
            if (filterNames.has(name) || name.startsWith("submitted_at__")) {
                filters.append(name, value);
            }
        });
        return filters.toString();
    };

    const currentFilters = filterQuery(window.location.search);
    if (!window.location.search) {
        const savedFilters = localStorage.getItem(storageKey);
        if (savedFilters) {
            window.location.replace(`${changelistPath}?${savedFilters}`);
            return;
        }
    } else if (currentFilters) {
        localStorage.setItem(storageKey, currentFilters);
    }

    document.querySelectorAll("#changelist-filter a").forEach((link) => {
        link.addEventListener("click", () => {
            const destination = new URL(link.href, window.location.href);
            const destinationFilters = filterQuery(destination.search);
            if (destinationFilters) {
                localStorage.setItem(storageKey, destinationFilters);
            } else {
                localStorage.removeItem(storageKey);
            }
        });
    });
})();
