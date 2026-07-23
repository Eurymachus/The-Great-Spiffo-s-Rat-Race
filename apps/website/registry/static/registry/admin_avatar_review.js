document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-avatar-review-action]").forEach((button) => {
        button.addEventListener("click", () => {
            const csrf = document.querySelector('input[name="csrfmiddlewaretoken"]');
            if (!csrf) return;
            document.querySelectorAll("[data-avatar-review-action]").forEach((control) => {
                control.disabled = true;
            });
            const form = document.createElement("form");
            form.method = "post";
            form.action = button.dataset.avatarReviewAction;
            const token = document.createElement("input");
            token.type = "hidden";
            token.name = "csrfmiddlewaretoken";
            token.value = csrf.value;
            form.append(token);
            document.body.append(form);
            form.submit();
        });
    });
});
