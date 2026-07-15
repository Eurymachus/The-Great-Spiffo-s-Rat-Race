(() => {
    "use strict";

    const form = document.querySelector("form[id$='_form']");
    const submitRow = form?.querySelector(".submit-row");
    if (!form || !submitRow) return;

    let dirty = false;
    const markDirty = (event) => {
        if (event.target.name !== "csrfmiddlewaretoken") dirty = true;
    };
    form.addEventListener("input", markDirty);
    form.addEventListener("change", markDirty);
    form.addEventListener("submit", () => {
        dirty = false;
    });

    const closeButton = document.createElement("button");
    closeButton.type = "button";
    closeButton.className = "admin-close-button";
    closeButton.textContent = "Close";
    const breadcrumbLinks = [...document.querySelectorAll(".breadcrumbs a")];
    const isBrandingSingleton = document.body.classList.contains("model-sitebranding");
    const targetIndex = isBrandingSingleton ? -2 : -1;
    const closeTarget = breadcrumbLinks.at(targetIndex)?.href || "/admin/";

    const dialog = document.createElement("dialog");
    dialog.className = "admin-close-dialog";
    dialog.innerHTML = `
        <form method="dialog">
            <h2>Unsaved changes</h2>
            <p>Your changes have not been saved and will be lost if you close this page.</p>
            <div class="admin-close-dialog-actions">
                <button value="cancel">Keep editing</button>
                <button value="discard" class="admin-discard-button">Close without saving</button>
            </div>
        </form>
    `;
    dialog.addEventListener("close", () => {
        if (dialog.returnValue === "discard") window.location.assign(closeTarget);
    });
    document.body.append(dialog);

    closeButton.addEventListener("click", () => {
        if (dirty) {
            dialog.showModal();
            return;
        }
        window.location.assign(closeTarget);
    });
    submitRow.prepend(closeButton);
})();
