document.addEventListener("DOMContentLoaded", () => {
  const rationaleField = document.getElementById("id_public_rationale");
  const rulingField = document.getElementById("id_ruling");
  if (!rationaleField) return;

  document.querySelectorAll("[data-public-rationale]").forEach((button) => {
    button.addEventListener("click", () => {
      rationaleField.value = button.dataset.publicRationale || "";
      rationaleField.dispatchEvent(new Event("input", { bubbles: true }));
      rationaleField.dispatchEvent(new Event("change", { bubbles: true }));
      if (rulingField && button.dataset.ruling) {
        rulingField.value = button.dataset.ruling;
        rulingField.dispatchEvent(new Event("input", { bubbles: true }));
        rulingField.dispatchEvent(new Event("change", { bubbles: true }));
      }
      rationaleField.focus();
    });
  });
});
