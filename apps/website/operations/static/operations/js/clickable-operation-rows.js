(() => {
    const interactiveSelector = "a, button, input, select, textarea, label";

    const recordLink = (row) => row.querySelector("th a[href], td a[href]");

    const openRecord = (row) => {
        const link = recordLink(row);
        if (link) {
            window.location.assign(link.href);
        }
    };

    document.querySelectorAll("#result_list tbody tr").forEach((row) => {
        const link = recordLink(row);
        if (!link) {
            return;
        }
        if (row.dataset.adminRowLinkReady === "true") {
            return;
        }

        row.classList.add("operation-row-link");
        row.dataset.adminRowLinkReady = "true";
        row.tabIndex = 0;
        row.setAttribute("role", "link");
        row.setAttribute("aria-label", `Open ${link.textContent.trim()}`);

        row.addEventListener("click", (event) => {
            if (!event.target.closest(interactiveSelector)) {
                openRecord(row);
            }
        });

        row.addEventListener("keydown", (event) => {
            if (event.target !== row || !["Enter", " "].includes(event.key)) {
                return;
            }
            event.preventDefault();
            openRecord(row);
        });
    });
})();
