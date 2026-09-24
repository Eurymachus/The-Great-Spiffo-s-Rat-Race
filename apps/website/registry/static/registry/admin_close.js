(() => {
    "use strict";

    const form = document.querySelector("form[id$='_form']");
    const submitRow = form?.querySelector(".submit-row");
    if (!form || !submitRow) return;

    let dirty = false;
    const markDirty = (event) => {
        if (event.target.closest("#reference-job")) return;
        if (event.target.name !== "csrfmiddlewaretoken") dirty = true;
    };
    form.addEventListener("input", markDirty);
    form.addEventListener("change", markDirty);
    form.addEventListener("submit", (event) => {
        queueMicrotask(() => {
            if (!event.defaultPrevented) dirty = false;
        });
    });
    form.addEventListener("rat-race:admin-save-success", () => { dirty = false; });
    form.addEventListener("rat-race:admin-editor-ready", () => { dirty = false; });

    const existingClose = submitRow.querySelector("a.closelink");
    const closeButton = existingClose || document.createElement("button");
    if (!existingClose) closeButton.type = "button";
    closeButton.classList.add("admin-close-button");
    closeButton.textContent = "Close";
    const breadcrumbLinks = [...document.querySelectorAll(".breadcrumbs a")];
    const isBrandingSingleton = document.body.classList.contains("model-sitebranding");
    const closeTarget = isBrandingSingleton
        ? "/admin/"
        : existingClose?.href || breadcrumbLinks.at(-1)?.href || "/admin/";
    let navigationTarget = closeTarget;

    const leavePage = () => {
        window.dispatchEvent(new CustomEvent("rat-race:admin-discard-navigation"));
        window.location.assign(navigationTarget);
    };

    const dialog = document.createElement("dialog");
    dialog.className = "admin-close-dialog";
    dialog.innerHTML = `
        <form method="dialog">
            <h2>Unsaved changes</h2>
            <p>Your changes have not been saved and will be lost if you leave this page.</p>
            <div class="admin-close-dialog-actions">
                <button value="cancel">Keep editing</button>
                <button value="discard" class="admin-discard-button">Leave without saving</button>
            </div>
        </form>
    `;
    dialog.addEventListener("close", () => {
        if (dialog.returnValue === "discard") leavePage();
    });
    document.body.append(dialog);

    const navigate = (target) => {
        navigationTarget = target || closeTarget;
        if (dirty) {
            dialog.showModal();
            return;
        }
        leavePage();
    };

    window.ratRaceAdminNavigation = {navigate};

    closeButton.addEventListener("click", (event) => {
        event.preventDefault();
        navigate(closeTarget);
    });
    submitRow.prepend(closeButton);
})();
