(() => {
    "use strict";

    const content = document.querySelector("main#content-start");
    const breadcrumbLinks = [...document.querySelectorAll(".breadcrumbs a")];
    const parentLink = breadcrumbLinks.at(-1);
    if (!content || !parentLink) return;

    const bar = document.createElement("nav");
    bar.className = "admin-navigation-bar";
    bar.setAttribute("aria-label", "Section navigation");

    const backLink = document.createElement("a");
    backLink.className = "admin-navigation-back";
    backLink.href = parentLink.href;
    backLink.textContent = "Back";
    const parentName = parentLink.textContent.trim();
    if (parentName) {
        backLink.setAttribute("aria-label", `Back to ${parentName}`);
        backLink.title = `Back to ${parentName}`;
    }

    bar.append(backLink);
    content.prepend(bar);
})();
