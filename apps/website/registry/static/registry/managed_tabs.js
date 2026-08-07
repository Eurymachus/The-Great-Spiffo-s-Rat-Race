document.addEventListener("DOMContentLoaded", () => {
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    document.querySelectorAll("[data-managed-tabs]").forEach((group) => {
        const tabs = [...group.querySelectorAll(':scope > [role="tablist"] > [role="tab"]')];
        const panels = [...group.querySelectorAll(":scope > .managed-tab-panels > [role=\"tabpanel\"]")];
        if (!tabs.length || tabs.length !== panels.length) return;

        const panelsContainer = group.querySelector(":scope > .managed-tab-panels");
        const tabList = group.querySelector(':scope > [role="tablist"]');
        const panelFor = (tab) => panels.find((panel) => panel.id === tab.getAttribute("aria-controls"));
        let activeTab = tabs.find((tab) => tab.classList.contains("is-active")) || tabs[0];
        let transitionTimer = null;

        const finishTransition = () => {
            window.clearTimeout(transitionTimer);
            panels.forEach((panel) => {
                const active = panel === panelFor(activeTab);
                panel.hidden = !active;
                panel.style.opacity = "";
                panel.classList.toggle("is-active", active);
                panel.classList.remove("is-entering", "is-leaving", "is-visible");
            });
            panelsContainer.style.minHeight = "";
        };

        const activate = (nextTab, {focus = false, updateHash = true, animate = true} = {}) => {
            if (!nextTab) return;
            const nextPanel = panelFor(nextTab);
            const previousPanel = panelFor(activeTab);
            if (!nextPanel) return;
            if (transitionTimer) finishTransition();

            tabs.forEach((tab) => {
                const selected = tab === nextTab;
                tab.classList.toggle("is-active", selected);
                tab.setAttribute("aria-selected", selected ? "true" : "false");
                tab.tabIndex = selected ? 0 : -1;
            });
            activeTab = nextTab;
            if (focus) nextTab.focus();
            if (tabList.scrollWidth > tabList.clientWidth + 1) {
                const maximumLeft = tabList.scrollWidth - tabList.clientWidth;
                const centredLeft = nextTab.offsetLeft - (tabList.clientWidth - nextTab.offsetWidth) / 2;
                tabList.scrollTo({
                    left: Math.max(0, Math.min(maximumLeft, centredLeft)),
                    behavior: reducedMotion ? "auto" : "smooth",
                });
            }
            if (updateHash) {
                const url = new URL(window.location.href);
                url.hash = nextTab.dataset.tabSlug;
                history.replaceState(null, "", url);
            }

            if (!animate || reducedMotion || !previousPanel || previousPanel === nextPanel) {
                finishTransition();
                return;
            }

            panelsContainer.style.minHeight = `${Math.max(previousPanel.offsetHeight, nextPanel.scrollHeight)}px`;
            nextPanel.hidden = false;
            nextPanel.classList.add("is-entering");
            previousPanel.classList.remove("is-active");
            previousPanel.classList.add("is-leaving");
            requestAnimationFrame(() => requestAnimationFrame(() => {
                nextPanel.classList.add("is-visible");
                previousPanel.style.opacity = "0";
            }));
            transitionTimer = window.setTimeout(() => {
                previousPanel.style.opacity = "";
                transitionTimer = null;
                finishTransition();
            }, 210);
        };

        group.classList.add("is-enhanced");
        panels.forEach((panel) => { panel.hidden = panel !== panelFor(activeTab); });

        const hashSlug = decodeURIComponent(window.location.hash.slice(1));
        const hashTab = tabs.find((tab) => tab.dataset.tabSlug === hashSlug);
        activate(hashTab || activeTab, {updateHash: false, animate: false});

        tabs.forEach((tab, index) => {
            tab.addEventListener("click", () => activate(tab));
            tab.addEventListener("keydown", (event) => {
                let nextIndex = null;
                if (event.key === "ArrowRight" || event.key === "ArrowDown") nextIndex = (index + 1) % tabs.length;
                if (event.key === "ArrowLeft" || event.key === "ArrowUp") nextIndex = (index - 1 + tabs.length) % tabs.length;
                if (event.key === "Home") nextIndex = 0;
                if (event.key === "End") nextIndex = tabs.length - 1;
                if (nextIndex === null) return;
                event.preventDefault();
                activate(tabs[nextIndex], {focus: true});
            });
        });

        window.addEventListener("hashchange", () => {
            const slug = decodeURIComponent(window.location.hash.slice(1));
            const matchingTab = tabs.find((tab) => tab.dataset.tabSlug === slug);
            if (matchingTab) activate(matchingTab, {updateHash: false});
        });
    });
});
