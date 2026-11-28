document.addEventListener("DOMContentLoaded", () => {
  const form = document.querySelector("[data-registration-form]");
  if (!form) return;

  const validationUrl = form.dataset.validationUrl;
  const csrfToken = form.querySelector('[name="csrfmiddlewaretoken"]')?.value || "";
  const fields = {
    nickname: form.querySelector('[name="nickname"]'),
    email: form.querySelector('[name="email"]'),
    password: form.querySelector('[name="password"]'),
    password_confirmation: form.querySelector('[name="password_confirmation"]'),
  };
  const requestSequence = new Map();
  const timers = new Map();
  const states = new Map();
  const submitButton = form.querySelector('button[type="submit"]');
  const updateSubmit = () => {
    if (submitButton) submitButton.disabled =
      Object.keys(fields).some((name) => fields[name] && states.get(name) !== "valid") ||
      !form.checkValidity();
  };

  const clearResult = (name) => {
    const input = fields[name];
    const container = form.querySelector(`[data-validation-for="${name}"]`);
    if (!input || !container) return;
    container.replaceChildren();
    container.classList.remove("field-validation-valid", "field-validation-error");
    input.removeAttribute("aria-invalid");
    input.closest(".field")?.classList.remove("field-valid", "field-error");
  };

  const showResult = (name, valid, messages) => {
    states.set(name, valid ? "valid" : "invalid");
    updateSubmit();
    const input = fields[name];
    const container = form.querySelector(`[data-validation-for="${name}"]`);
    if (!input || !container) return;
    container.replaceChildren();
    container.classList.toggle("field-validation-valid", valid);
    container.classList.toggle("field-validation-error", !valid);
    const field = input.closest(".field");
    field?.classList.toggle("field-valid", valid);
    field?.classList.toggle("field-error", !valid);
    input.setAttribute("aria-invalid", valid ? "false" : "true");
    messages.forEach((message) => {
      const item = document.createElement("p");
      item.className = valid ? "validation-success" : "error";
      item.textContent = message;
      container.appendChild(item);
    });
  };

  const validateRemoteField = async (name) => {
    const input = fields[name];
    if (!input) return;
    const value = input.value;
    states.set(name, "pending");
    updateSubmit();
    clearResult(name);
    if (!value) return;

    const sequence = (requestSequence.get(name) || 0) + 1;
    requestSequence.set(name, sequence);
    const body = new URLSearchParams({ field: name, value });
    try {
      const response = await fetch(validationUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
          "X-CSRFToken": csrfToken,
          "X-Requested-With": "XMLHttpRequest",
        },
        body,
      });
      const result = await response.json();
      if (requestSequence.get(name) !== sequence || input.value !== value) return;
      if (!response.ok) {
        showResult(name, false, [result.error || "This field could not be checked."]);
        return;
      }
      showResult(
        name,
        result.valid,
        result.valid ? [result.message] : result.errors
      );
    } catch (_error) {
      if (requestSequence.get(name) === sequence && input.value === value) {
        showResult(name, false, ["This field could not be checked. Please try again."]);
      }
    }
  };

  const validateConfirmation = () => {
    const confirmation = fields.password_confirmation;
    if (!confirmation) return;
    clearResult("password_confirmation");
    if (!confirmation.value) {
      states.set("password_confirmation", "invalid");
      updateSubmit();
      return;
    }
    if (confirmation.value !== fields.password?.value) {
      showResult("password_confirmation", false, ["The passwords do not match."]);
    } else {
      showResult("password_confirmation", true, ["The passwords match."]);
    }
  };

  ["nickname", "email", "password"].forEach((name) => {
    fields[name]?.addEventListener("blur", () => {
      clearTimeout(timers.get(name));
      validateRemoteField(name);
    });
  });
  fields.password_confirmation?.addEventListener("blur", validateConfirmation);

  Object.entries(fields).forEach(([name, input]) => {
    input?.addEventListener("input", () => {
      requestSequence.set(name, (requestSequence.get(name) || 0) + 1);
      states.set(name, "pending");
      updateSubmit();
      clearResult(name);
      if (name === "password" || name === "password_confirmation") validateConfirmation();
      input.closest(".field")?.querySelectorAll("[data-server-field-error]").forEach(
        (error) => error.remove()
      );
      if (name !== "password_confirmation") {
        clearTimeout(timers.get(name));
        if (input.value.trim()) {
          timers.set(name, setTimeout(() => validateRemoteField(name), 500));
        }
      }
    });
  });
  form.addEventListener("input", updateSubmit);
  form.addEventListener("change", updateSubmit);
  form.addEventListener("submit", (event) => {
    updateSubmit();
    if (submitButton?.disabled) event.preventDefault();
  });
  updateSubmit();
  ["nickname", "email", "password"].forEach((name) => {
    if (fields[name]?.value) validateRemoteField(name);
  });
  validateConfirmation();
});
