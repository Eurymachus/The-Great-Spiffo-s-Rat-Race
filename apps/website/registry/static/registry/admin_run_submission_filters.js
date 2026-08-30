(() => {
    "use strict";

    const configurations = {
        "/admin/registry/runsubmission/": {
            cookieKey: "rat_race_admin_run_submission_filters",
            filterNames: ["queue_state", "challenge_mode"],
        },
        "/admin/registry/challengerun/": {
            cookieKey: "rat_race_admin_challenge_run_filters",
            filterNames: [
                "challenge_mode",
                "lifecycle_status",
                "status",
                "export_format",
                "bootstrapped",
                "updated",
            ],
        },
    };
    const changelistPath = window.location.pathname;
    const configuration = configurations[changelistPath];
    if (!configuration) return;

    const { cookieKey } = configuration;
    const filterNames = new Set(configuration.filterNames);

    const filterQuery = (search) => {
        const source = new URLSearchParams(search);
        const filters = new URLSearchParams();
        source.forEach((value, name) => {
            if (filterNames.has(name)) {
                filters.append(name, value);
            }
        });
        return filters.toString();
    };

    const currentFilters = filterQuery(window.location.search);
    const secure = window.location.protocol === "https:" ? "; Secure" : "";
    const setCookie = (filters) => {
        document.cookie = `${cookieKey}=${encodeURIComponent(filters)}; Path=${changelistPath}; Max-Age=31536000; SameSite=Lax${secure}`;
    };
    const clearCookie = () => {
        document.cookie = `${cookieKey}=; Path=${changelistPath}; Max-Age=0; SameSite=Lax${secure}`;
    };
    if (window.location.search && currentFilters) {
        setCookie(currentFilters);
    }

    document.querySelectorAll(".run-queue-filters a").forEach((link) => {
        link.addEventListener("click", () => {
            const destination = new URL(link.href, window.location.href);
            const destinationFilters = filterQuery(destination.search);
            if (destinationFilters) {
                setCookie(destinationFilters);
            } else {
                clearCookie();
            }
        });
    });

    const moreFilters = document.querySelector(".challenge-run-more-filters");
    if (moreFilters) {
        document.addEventListener("pointerdown", (event) => {
            if (moreFilters.open && !moreFilters.contains(event.target)) {
                moreFilters.open = false;
            }
        });
        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape" && moreFilters.open) {
                moreFilters.open = false;
                moreFilters.querySelector("summary")?.focus();
            }
        });
    }
})();
