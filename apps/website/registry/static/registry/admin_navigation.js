(() => {
    "use strict";

    // App index screens are the top of this administration hierarchy. The
    // nominal /admin/ parent redirects to a model list, which would create a
    // navigation loop if a Back button were shown here.
    if (/^\/admin\/[^/]+\/$/.test(window.location.pathname)) return;

    const content = document.querySelector("main#content-start");
    const breadcrumbLinks = [...document.querySelectorAll(".breadcrumbs a")];
    const parentLink = breadcrumbLinks.at(-1);
    if (!content || !parentLink) return;

    let bar = content.querySelector(".admin-navigation-bar");
    let backLink = bar?.querySelector(".admin-navigation-back");
    const navigationWasRendered = Boolean(bar && backLink);
    if (!navigationWasRendered) {
        bar = document.createElement("nav");
        bar.className = "admin-navigation-bar";
        bar.setAttribute("aria-label", "Section navigation");
        backLink = document.createElement("a");
        backLink.className = "admin-navigation-back";
    }
    const explicitReturn = document.querySelector("[data-admin-return-url]");
    const parentUrl = new URL(
        explicitReturn?.dataset.adminReturnUrl || parentLink.href,
        window.location.href
    );
    const preservedFilters = new URLSearchParams(window.location.search).get(
        "_changelist_filters"
    );
    if (preservedFilters) {
        parentUrl.search = preservedFilters;
    }
    backLink.href = parentUrl.href;
    backLink.textContent = "Back";
    const parentName = parentLink.textContent.trim();
    if (parentName) {
        backLink.setAttribute("aria-label", `Back to ${parentName}`);
        backLink.title = `Back to ${parentName}`;
    }
    backLink.addEventListener("click", (event) => {
        const navigation = window.ratRaceAdminNavigation;
        if (!navigation?.navigate) return;
        event.preventDefault();
        navigation.navigate(backLink.href);
    });

    if (!navigationWasRendered) {
        bar.append(backLink);
        content.prepend(bar);
    }
})();
