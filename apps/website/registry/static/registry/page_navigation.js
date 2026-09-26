(() => {
    "use strict";
    const supported = (url) => url.origin === location.origin &&
        !/^\/(admin|static|media|signup|login|logout|password[^/]*)(\/|$)/.test(url.pathname) &&
        !/^\/account\/(data|streaming|connections|dashboard\/fragment)(\/|$)/.test(url.pathname) &&
        !/^\/account\/notifications\/(summary|stream|read)\/$/.test(url.pathname);
    let pending = null;
    let dirty = false;
    const main = () => document.getElementById("main-content");
    const enabled = () => main()?.dataset.softNavigation === "on";
    const saveScroll = () => history.replaceState(
        {...history.state, pageScroll: [scrollX, scrollY]}, "", location.href
    );
    history.scrollRestoration = "manual";
    history.replaceState({...history.state, pageReferrer: document.referrer}, "", location.href);
    saveScroll();
    window.addEventListener("scroll", () => { if (!pending) saveScroll(); }, {passive: true});
    document.addEventListener("input", (event) => {
        if (main()?.contains(event.target) && event.target.closest("form")?.method.toLowerCase() === "post") dirty = true;
    });
    const navigate = async (url, {pop = false, scroll = null, referrer = location.href} = {}) => {
        const openingNotification = /^\/account\/notifications\/[0-9a-f-]{36}\/$/.test(new URL(url).pathname);
        pending?.abort();
        const controller = new AbortController();
        pending = controller;
        const current = main();
        current.setAttribute("aria-busy", "true");
        try {
            const response = await fetch(url, {
                signal: controller.signal, credentials: "same-origin",
                headers: {"Accept": "text/html"}, referrer,
            });
            if (controller.signal.aborted) return;
            if (response.redirected) url = response.url;
            const parsed = new DOMParser().parseFromString(await response.text(), "text/html");
            if (controller.signal.aborted) return;
            const replacement = parsed.getElementById("main-content");
            if (!response.ok || (response.redirected && !supported(new URL(response.url))) || replacement?.dataset.softNavigation !== "on" ||
                replacement.dataset.navigationUser !== current.dataset.navigationUser ||
                replacement.querySelector('script:not([type="application/json"])') ||
                [...parsed.querySelectorAll("script[src]")].some((script) =>
                    ![...document.querySelectorAll("script[src]")].some((loaded) => loaded.src === script.src))) {
                location.assign(response.redirected ? response.url : url);
                return;
            }
            if (controller.signal.aborted) return;
            document.dispatchEvent(new CustomEvent("page:before-change"));
            document.querySelectorAll("dialog[open]").forEach((dialog) => dialog.close());
            if (!pop) {
                saveScroll();
                history.pushState({pageScroll: [0, 0], pageReferrer: referrer}, "", url);
            }
            current.replaceWith(replacement);
            document.title = parsed.title;
            document.querySelectorAll("header a[href], [data-site-menu] a[href]").forEach((link) => {
                const next = [...parsed.querySelectorAll("a[href]")].find((candidate) => candidate.href === link.href);
                if (next?.hasAttribute("aria-current")) link.setAttribute("aria-current", next.getAttribute("aria-current"));
                else link.removeAttribute("aria-current");
            });
            dirty = false;
            document.dispatchEvent(new CustomEvent("page:loaded"));
            if (openingNotification) document.dispatchEvent(new CustomEvent("notification:opened"));
            replacement.tabIndex = -1;
            replacement.focus({preventScroll: true});
            if (scroll) window.scrollTo(...scroll);
            else if (new URL(url).hash) {
                document.getElementById(decodeURIComponent(new URL(url).hash.slice(1)))?.scrollIntoView();
            } else window.scrollTo(0, 0);
            window.dispatchEvent(new Event("resize"));
        } catch (error) {
            if (error.name !== "AbortError") location.assign(url);
        } finally {
            if (pending === controller) {
                pending = null;
                main()?.removeAttribute("aria-busy");
            }
        }
    };
    document.addEventListener("click", (event) => {
        if (event.defaultPrevented || event.button !== 0 || event.ctrlKey || event.metaKey ||
            event.shiftKey || event.altKey || !enabled() || dirty) return;
        const link = event.target.closest("a[href]");
        if (!link || link.hasAttribute("download") || (link.target && link.target !== "_self")) return;
        const url = new URL(link.href);
        if (!supported(url) || (url.pathname === location.pathname && url.search === location.search && url.hash)) return;
        event.preventDefault();
        navigate(url.href);
    });
    document.addEventListener("submit", (event) => {
        const form = event.target;
        if (event.defaultPrevented || !enabled() || dirty || form.method.toLowerCase() !== "get" ||
            (form.target && form.target !== "_self")) return;
        const url = new URL(form.action);
        if (!supported(url)) return;
        url.search = new URLSearchParams(new FormData(form, event.submitter)).toString();
        event.preventDefault();
        navigate(url.href);
    });
    window.addEventListener("popstate", (event) => {
        if (!enabled() || !supported(new URL(location.href)) || dirty) {
            location.reload();
            return;
        }
        navigate(location.href, {pop: true, scroll: event.state?.pageScroll || [0, 0], referrer: event.state?.pageReferrer || ""});
    });
})();
