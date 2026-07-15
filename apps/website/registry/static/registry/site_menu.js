(() => {
    "use strict";
    const toggle = document.querySelector("[data-site-menu-toggle]");
    const menu = document.querySelector("[data-site-menu]");
    if (!toggle || !menu) return;

    const closeMenu = (restoreFocus = false) => {
        menu.classList.remove("is-open");
        toggle.setAttribute("aria-expanded", "false");
        if (restoreFocus) toggle.focus();
    };
    toggle.addEventListener("click", () => {
        const opening = !menu.classList.contains("is-open");
        menu.classList.toggle("is-open", opening);
        toggle.setAttribute("aria-expanded", String(opening));
    });
    document.addEventListener("click", (event) => {
        if (!menu.contains(event.target) && !toggle.contains(event.target)) closeMenu();
    });
    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && menu.classList.contains("is-open")) {
            closeMenu(true);
        }
    });
    window.matchMedia("(min-width: 34.01rem)").addEventListener("change", (event) => {
        if (event.matches) closeMenu();
    });
})();
