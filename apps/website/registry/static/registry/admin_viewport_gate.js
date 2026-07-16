(() => {
    "use strict";

    const minimumWidth = 1200;
    const overrideKey = "rat-race-admin-small-screen-override";
    const config = window.ratRaceAdminGate || {};
    let overridden = sessionStorage.getItem(overrideKey) === "true";

    const gate = document.createElement("div");
    gate.className = "admin-viewport-gate";
    gate.setAttribute("role", "dialog");
    gate.setAttribute("aria-modal", "true");
    gate.setAttribute("aria-labelledby", "admin-viewport-gate-title");
    gate.innerHTML = `
        <div class="admin-viewport-gate-panel">
            <h1 id="admin-viewport-gate-title">A larger screen is recommended</h1>
            <p>The Rat Race administration area is designed for a desktop or laptop display. On this screen, controls and records may be difficult to use safely.</p>
            <div class="admin-viewport-gate-actions">
                <a class="button" href="${config.returnUrl || "/account/"}">Return to your account</a>
                <button type="button" class="default" data-admin-gate-continue>Continue anyway</button>
            </div>
        </div>`;
    document.body.appendChild(gate);

    const effectiveViewport = () => {
        const widths = [window.innerWidth, window.visualViewport?.width, window.screen?.width]
            .filter((width) => Number.isFinite(width) && width > 0);
        return widths.length ? Math.round(Math.min(...widths)) : window.innerWidth;
    };

    const effectiveViewportHeight = () => {
        const heights = [window.innerHeight, window.visualViewport?.height, window.screen?.height]
            .filter((height) => Number.isFinite(height) && height > 0);
        return heights.length ? Math.round(Math.min(...heights)) : window.innerHeight;
    };

    const updateGate = () => {
        const width = effectiveViewport();
        const height = effectiveViewportHeight();
        gate.style.width = `${width}px`;
        gate.style.height = `${height}px`;
        gate.style.top = `${Math.round(window.visualViewport?.offsetTop || 0)}px`;
        gate.classList.toggle("is-compact", width < 480);
        gate.classList.toggle("is-visible", !overridden && width < minimumWidth);
    };

    gate.querySelector("[data-admin-gate-continue]").addEventListener("click", () => {
        overridden = true;
        sessionStorage.setItem(overrideKey, "true");
        updateGate();
    });
    window.addEventListener("resize", updateGate);
    window.visualViewport?.addEventListener("resize", updateGate);
    updateGate();
})();
