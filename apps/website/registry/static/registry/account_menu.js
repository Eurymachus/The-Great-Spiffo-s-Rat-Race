(() => {
    "use strict";
    const form = document.querySelector("[data-compact-sign-in]");
    if (!form || !window.fetch) return;
    const error = form.querySelector("[data-sign-in-error]");
    const submit = form.querySelector('[type="submit"]');

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        if (submit.disabled) return;
        submit.disabled = true;
        error.hidden = true;
        try {
            const response = await fetch(form.action, {
                method: "POST",
                body: new FormData(form),
                headers: {"X-Requested-With": "XMLHttpRequest"},
                credentials: "same-origin",
            });
            const result = await response.json();
            if (!response.ok || !result.signed_in) throw new Error(result.error || "Sign In was unsuccessful.");
            window.location.assign(result.redirect || window.location.href);
        } catch (failure) {
            error.textContent = failure.message;
            error.hidden = false;
        } finally {
            submit.disabled = false;
        }
    });
})();
