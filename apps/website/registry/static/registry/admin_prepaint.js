(() => {
    "use strict";

    let navSidebarIsOpen = "true";
    try {
        navSidebarIsOpen =
            localStorage.getItem("django.admin.navSidebarIsOpen") || "true";
    } catch {
        navSidebarIsOpen = "true";
    }
    if (navSidebarIsOpen === "true") {
        document.documentElement.classList.add("admin-nav-sidebar-open");
    }

    let savedSections = {};
    try {
        savedSections = JSON.parse(
            localStorage.getItem("rat-race-admin-sidebar-sections-v1") || "{}"
        );
    } catch {
        savedSections = {};
    }

    const escapeAttribute = (value) =>
        String(value).replaceAll("\\", "\\\\").replaceAll('"', '\\"');
    const expandedRules = Object.entries(savedSections)
        .filter(([, expanded]) => expanded === true)
        .map(([section]) => {
            const selector = `#nav-sidebar .module:has([data-admin-sidebar-section="${escapeAttribute(section)}"])`;
            return `${selector} tbody{display:table-row-group}${selector} .admin-sidebar-section-chevron{transform:rotate(45deg)}`;
        })
        .join("");

    const style = document.createElement("style");
    style.id = "admin-sidebar-prepaint";
    style.textContent = `html.admin-nav-sidebar-open .main>#nav-sidebar{margin-left:0;visibility:visible}html.admin-nav-sidebar-open .main>#nav-sidebar+.content{max-width:calc(100% - 299px)}html.admin-nav-sidebar-open .toggle-nav-sidebar::before{content:'«'}#nav-sidebar .module:not(.current-app) tbody{display:none}#nav-sidebar .module:not(.current-app) .admin-sidebar-section-chevron{transform:rotate(-45deg)}${expandedRules}`;
    document.head.append(style);
})();
