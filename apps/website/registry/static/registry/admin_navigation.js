(() => {
    "use strict";

    // App index screens keep their existing section navigation.
    if (/^\/admin\/[^/]+\/$/.test(window.location.pathname)) return;

    const content = document.querySelector("main#content-start");
    const breadcrumbLinks = [...document.querySelectorAll(".breadcrumbs a")];
    const parentLink = breadcrumbLinks.at(-1);
    if (!content || !parentLink) return;

    const backLink = parentLink;
    const explicitReturn = document.querySelector("[data-admin-return-url]");
    const requestedReturn = new URLSearchParams(window.location.search).get('return_to');
    const returnUrl = requestedReturn ? new URL(requestedReturn, window.location.href) : null;
    const fromRun = returnUrl && returnUrl.origin === window.location.origin &&
        /^\/admin\/registry\/(challengerun|runsubmission)\/[^/]+\/change\/$/.test(returnUrl.pathname);
    const parentUrl = new URL(
        (fromRun ? returnUrl.href : null) || explicitReturn?.dataset.adminReturnUrl || parentLink.href,
        window.location.href
    );
    const preservedFilters = new URLSearchParams(window.location.search).get(
        "_changelist_filters"
    );
    if (preservedFilters && !fromRun) {
        parentUrl.search = preservedFilters;
    }
    backLink.href = parentUrl.href;
    if (fromRun) backLink.textContent = "Run";
    const parentName = fromRun ? "run" : parentLink.textContent.trim();
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

})();
