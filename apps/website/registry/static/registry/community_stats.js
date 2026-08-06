document.addEventListener("DOMContentLoaded", () => {
    const mobileLayout = window.matchMedia("(max-width: 700px)");
    const disclosures = document.querySelectorAll(".community-stats-disclosure");

    const syncDisclosureLayout = () => {
        disclosures.forEach((disclosure) => {
            disclosure.open = !mobileLayout.matches;
        });
    };

    syncDisclosureLayout();
    mobileLayout.addEventListener("change", syncDisclosureLayout);
});
