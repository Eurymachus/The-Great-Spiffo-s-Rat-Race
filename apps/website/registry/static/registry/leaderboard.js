(() => {
    "use strict";

    let activeTrigger = null;
    const openDialog = (dialog, trigger) => {
        if (!dialog || typeof dialog.showModal !== "function") return;
        activeTrigger = trigger;
        dialog.showModal();
    };
    const prepareDialog = (dialog, closeSelector) => {
        dialog.querySelector(closeSelector)?.addEventListener("click", () => dialog.close());
        dialog.addEventListener("click", (event) => {
            if (event.target === dialog) dialog.close();
        });
        dialog.addEventListener("close", () => activeTrigger?.focus());
    };

    const initialSortKeys = {
        weighted_completion: "progress",
        kills: "kills",
        outposts: "outposts",
        skills: "skills",
        verified_at: "verified",
        source_rank: "rank",
    };
    const textCollator = new Intl.Collator(undefined, {
        numeric: true,
        sensitivity: "base",
    });

    document.querySelectorAll("[data-sortable-ranking]").forEach((table) => {
        const tbody = table.tBodies[0];
        const headers = [...table.querySelectorAll("thead th[data-sort-key]")];
        if (!tbody || !headers.length) return;

        const rows = [...tbody.rows];
        rows.forEach((row, index) => {
            row.dataset.originalIndex = String(index);
        });

        let activeKey = initialSortKeys[table.dataset.initialSort] || "rank";
        let activeDirection = table.dataset.initialSort === "source_rank" ? "ascending" : "descending";

        const updateHeaderState = () => {
            headers.forEach((header) => {
                const isActive = header.dataset.sortKey === activeKey;
                header.setAttribute("aria-sort", isActive ? activeDirection : "none");
                const button = header.querySelector(".managed-ranking-sort");
                if (button) {
                    const directionLabel = isActive && activeDirection === "ascending"
                        ? "descending"
                        : "ascending";
                    button.title = `Sort ${directionLabel}`;
                }
            });
        };

        const sortRows = (header) => {
            const key = header.dataset.sortKey;
            const type = header.dataset.sortType;
            if (activeKey === key) {
                activeDirection = activeDirection === "ascending" ? "descending" : "ascending";
            } else {
                activeKey = key;
                activeDirection = type === "text" ? "ascending" : "descending";
            }

            const columnIndex = header.cellIndex;
            const direction = activeDirection === "ascending" ? 1 : -1;
            rows.sort((leftRow, rightRow) => {
                const leftValue = leftRow.cells[columnIndex]?.dataset.sortValue || "";
                const rightValue = rightRow.cells[columnIndex]?.dataset.sortValue || "";
                const comparison = type === "number"
                    ? (Number(leftValue) || 0) - (Number(rightValue) || 0)
                    : textCollator.compare(leftValue, rightValue);
                if (comparison !== 0) return comparison * direction;
                return Number(leftRow.dataset.originalIndex) - Number(rightRow.dataset.originalIndex);
            });

            rows.forEach((row) => {
                tbody.append(row);
            });
            updateHeaderState();
        };

        headers.forEach((header) => {
            header.querySelector(".managed-ranking-sort")?.addEventListener("click", () => sortRows(header));
        });
        updateHeaderState();
    });

    document.querySelectorAll("[data-build-open]").forEach((button) => {
        const dialog = document.getElementById(button.dataset.buildOpen);
        if (dialog) {
            button.addEventListener("click", () => openDialog(dialog, button));
            prepareDialog(dialog, "[data-build-close]");
        } else {
            const accessDialog = document.querySelector("[data-access-prompt]");
            button.addEventListener("click", () => openDialog(accessDialog, button));
        }
    });

    const accessDialog = document.querySelector("[data-access-prompt]");
    if (accessDialog) {
        const accessTitle = accessDialog.querySelector("#leaderboard-access-title");
        const accessMessage = accessDialog.querySelector("[data-access-message]");
        const signInLink = accessDialog.querySelector("[data-access-sign-in]");
        const prepareAccessDialog = (button) => {
            if (button.dataset.accessTitle) accessTitle.textContent = button.dataset.accessTitle;
            if (button.dataset.accessMessage) accessMessage.textContent = button.dataset.accessMessage;
            if (button.dataset.accessDestination && signInLink) {
                const url = new URL(signInLink.href);
                url.searchParams.set("next", button.dataset.accessDestination);
                signInLink.href = url.toString();
            }
        };
        prepareDialog(accessDialog, "[data-access-prompt-close]");
        document.querySelectorAll("[data-access-prompt-open]").forEach((button) => {
            button.addEventListener("click", () => {
                prepareAccessDialog(button);
                openDialog(accessDialog, button);
            });
        });

        document.querySelectorAll("[data-build-open]").forEach((button) => {
            if (document.getElementById(button.dataset.buildOpen)) return;
            button.addEventListener("click", () => prepareAccessDialog(button));
        });
    }
})();
