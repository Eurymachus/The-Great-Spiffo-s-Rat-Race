(() => {
    "use strict";
    const button = document.getElementById("admin-menu-trigger");
    const sidebar = document.getElementById("nav-sidebar");
    const main = document.getElementById("main");
    if (!button || !sidebar || !main) return;
    const pageScroll = document.getElementById("admin-page-scroll");
    if (pageScroll) {
        const probe = document.createElement("div");
        probe.style.cssText = "position:absolute;visibility:hidden;width:100px;height:100px;overflow:scroll;pointer-events:none";
        document.body.append(probe);
        const scrollbarWidth = probe.offsetWidth - probe.clientWidth;
        probe.remove();
        const syncContentInset = () => {
            const occupied = pageScroll.offsetWidth - pageScroll.clientWidth;
            pageScroll.style.setProperty("--admin-scrollbar-reserve", `${Math.max(0, scrollbarWidth - occupied)}px`);
            pageScroll.style.setProperty("--admin-scrollbar-occupied", `${occupied}px`);
        };
        const observer = new ResizeObserver(syncContentInset);
        observer.observe(pageScroll);
        observer.observe(main);
        syncContentInset();
    }
    const themeOptions = document.querySelectorAll('[name="admin-display-theme"]');
    const syncThemeOptions = () => {
        const current = document.documentElement.dataset.theme || "auto";
        themeOptions.forEach((option) => { option.checked = option.value === current; });
    };
    syncThemeOptions();
    themeOptions.forEach((option) => option.addEventListener("change", () => {
        if (!option.checked) return;
        document.documentElement.dataset.theme = option.value;
        try { localStorage.setItem("theme", option.value); }
        catch { /* The selected theme still applies when storage is unavailable. */ }
    }));
    window.addEventListener("storage", (event) => {
        if (event.key !== "theme") return;
        document.documentElement.dataset.theme = ["auto", "light", "dark"].includes(event.newValue)
            ? event.newValue : "auto";
        syncThemeOptions();
    });
    const sectionKey = `rat-race-admin-menu-v1:${sidebar.dataset.menuUser}:`;
    sidebar.querySelectorAll("[data-menu-section]").forEach((section) => {
        const key = sectionKey + section.dataset.menuSection;
        try {
            const saved = localStorage.getItem(key);
            if (saved === "true" || saved === "false") section.open = saved === "true";
        } catch { /* Use the server defaults when storage is unavailable. */ }
        section.addEventListener("toggle", () => {
            try { localStorage.setItem(key, String(section.open)); }
            catch { /* Sections remain usable without saved preferences. */ }
        });
    });
    const backdrop = document.querySelector(".admin-menu-backdrop");
    const closeButton = document.getElementById("admin-menu-close");
    let open = false;
    let returnFocus = button;
    const render = () => {
        main.classList.remove("shifted");
        document.body.classList.toggle("admin-menu-open", open);
        button.setAttribute("aria-expanded", String(open));
        button.setAttribute("aria-label", open ? "Close navigation" : "Open navigation");
        sidebar.inert = !open;
        if (backdrop) backdrop.hidden = !open;
        document.getElementById("content-start").inert = open;
    };
    render();
    const close = () => {
        open = false;
        render();
        returnFocus.focus();
    };
    let activeDropdown = null;
    let leaveTimer;
    let dropdownMode = "pointer";
    const closeDropdown = (restoreFocus = false) => {
        clearTimeout(leaveTimer);
        if (!activeDropdown) return;
        const trigger = activeDropdown.querySelector("[data-menu-dropdown]");
        activeDropdown.querySelector(".admin-top-dropdown").hidden = true;
        trigger.setAttribute("aria-expanded", "false");
        activeDropdown = null;
        if (restoreFocus) trigger.focus();
    };
    button.addEventListener("click", () => {
        closeDropdown();
        returnFocus = button;
        open = !open;
        render();
        if (open) closeButton.focus();
    });
    closeButton?.addEventListener("click", close);
    backdrop?.addEventListener("click", close);
    document.querySelectorAll("[data-menu-dropdown]").forEach((trigger) => {
        const section = trigger.closest(".admin-top-section");
        const panel = section.querySelector(".admin-top-dropdown");
        const hoverMenu = Boolean(section.closest(".admin-top-links"));
        let pointerInside = false;
        const show = () => {
            clearTimeout(leaveTimer);
            if (activeDropdown === section) return;
            closeDropdown();
            activeDropdown = section;
            panel.hidden = false;
            trigger.setAttribute("aria-expanded", "true");
            panel.style.left = "0px";
            const overflow = panel.getBoundingClientRect().right - document.documentElement.clientWidth + 12;
            if (overflow > 0) panel.style.left = `${-overflow}px`;
        };
        // Icon menus open on hover; the profile menu remains click-operated.
        if (hoverMenu) {
            section.addEventListener("pointerenter", (event) => {
                if (event.pointerType !== "mouse") return;
                pointerInside = true;
                dropdownMode = "pointer";
                clearTimeout(leaveTimer);
                show();
            });
            section.addEventListener("pointerleave", (event) => {
                if (event.pointerType !== "mouse") return;
                pointerInside = false;
                clearTimeout(leaveTimer);
                leaveTimer = setTimeout(() => {
                    if (activeDropdown === section && !pointerInside && dropdownMode === "pointer") {
                        closeDropdown();
                    }
                }, 180);
            });
        }
        trigger.addEventListener("click", (event) => {
            // A mouse click after hover confirms the open menu instead of toggling it shut.
            if (hoverMenu && pointerInside && event.detail > 0) {
                dropdownMode = "pointer";
                show();
                return;
            }
            dropdownMode = "keyboard";
            if (activeDropdown === section) closeDropdown();
            else show();
        });
        section.addEventListener("keydown", (event) => {
            dropdownMode = "keyboard";
            clearTimeout(leaveTimer);
            if (event.target.matches('input[type="radio"]')) {
                if (event.key === "Escape") { event.preventDefault(); closeDropdown(true); }
                return;
            }
            const links = [...panel.querySelectorAll("a, button")];
            if (event.key === "Escape") {
                event.preventDefault(); closeDropdown(true);
            } else if (event.key === "ArrowDown" || event.key === "ArrowUp") {
                event.preventDefault();
                if (panel.hidden) show();
                const index = links.indexOf(document.activeElement);
                const next = index < 0 ? (event.key === "ArrowDown" ? 0 : links.length - 1)
                    : (index + (event.key === "ArrowDown" ? 1 : -1) + links.length) % links.length;
                links[next]?.focus();
            }
        });
    });
    document.addEventListener("click", (event) => {
        if (activeDropdown && !activeDropdown.contains(event.target)) closeDropdown();
    });
    document.addEventListener("focusin", (event) => {
        if (dropdownMode === "keyboard" && activeDropdown && !activeDropdown.contains(event.target)) closeDropdown();
    });
    document.addEventListener("keydown", (event) => {
        if (event.key === "Tab") dropdownMode = "keyboard";
    });
    window.addEventListener("resize", () => closeDropdown());
    sidebar.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && open) {
            event.preventDefault();
            close();
        }
        if (event.key === "Tab" && open) {
            const stops = [...sidebar.querySelectorAll("a, button, summary")].filter(
                (element) => element.getClientRects().length
            );
            const first = stops[0], last = stops.at(-1);
            if (event.shiftKey && document.activeElement === first) {
                event.preventDefault(); last.focus();
            } else if (!event.shiftKey && document.activeElement === last) {
                event.preventDefault(); first.focus();
            }
        }
    });
    document.documentElement.classList.remove("admin-nav-sidebar-open");
    document.getElementById("admin-sidebar-prepaint")?.remove();
})();
