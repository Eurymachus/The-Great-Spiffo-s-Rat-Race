(() => {
    "use strict";
    const toggle = document.querySelector("[data-site-menu-toggle]");
    const menu = document.querySelector("[data-site-menu]");
    if (!toggle || !menu) return;

    const submenuToggles = [...menu.querySelectorAll("[data-nav-submenu-toggle]")];
    const closeSubmenus = () => {
        submenuToggles.forEach((submenuToggle) => {
            submenuToggle.setAttribute("aria-expanded", "false");
            submenuToggle.closest(".site-nav-item")?.classList.remove("is-open");
        });
    };

    const closeMenu = (restoreFocus = false) => {
        menu.classList.remove("is-open");
        toggle.setAttribute("aria-expanded", "false");
        closeSubmenus();
        if (restoreFocus) toggle.focus();
    };

    submenuToggles.forEach((submenuToggle) => {
        submenuToggle.addEventListener("click", (event) => {
            event.stopPropagation();
            const desktopHoverNavigation = window.matchMedia("(hover: hover) and (pointer: fine)").matches
                && getComputedStyle(toggle).display === "none";
            if (desktopHoverNavigation && event.detail !== 0) {
                submenuToggle.blur();
                return;
            }
            const item = submenuToggle.closest(".site-nav-item");
            const opening = submenuToggle.getAttribute("aria-expanded") !== "true";
            item?.parentElement?.querySelectorAll(":scope > .site-nav-item.is-open").forEach((sibling) => {
                if (sibling !== item) {
                    sibling.classList.remove("is-open");
                    sibling.querySelector(":scope > .site-nav-entry [data-nav-submenu-toggle]")?.setAttribute("aria-expanded", "false");
                }
            });
            item?.classList.toggle("is-open", opening);
            submenuToggle.setAttribute("aria-expanded", String(opening));
        });
    });
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
