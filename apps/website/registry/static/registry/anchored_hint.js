// Shared floating helpers. Keep dialog helpers inside their modal's top layer.
window.RatRaceHint = {
    create({anchor, element, placement = "top", type = "info", container = anchor.closest("dialog") || document.body,
        signal, onDismiss = () => {}, onVisibility = () => {}}) {
        if (!["top", "bottom", "left", "right"].includes(placement)) throw new Error("Invalid hint placement");
        if (!["info", "error", "success", "warning"].includes(type)) throw new Error("Invalid hint type");
        element.classList.add("anchored-hint");
        element.dataset.type = type;
        container.append(element);
        const controller = new AbortController();
        let active = false;
        let destroyed = false;
        const clamp = (value, min, max) => Math.max(min, Math.min(value, Math.max(min, max)));
        const position = () => {
            if (!active || destroyed) return;
            const target = anchor.getBoundingClientRect();
            const viewport = {left: 0, top: 0, right: window.innerWidth, bottom: window.innerHeight};
            const bounds = container.tagName === "DIALOG" ? container.getBoundingClientRect() : viewport;
            const leftEdge = Math.max(8, bounds.left + 8);
            const rightEdge = Math.min(viewport.right, bounds.right) - 8;
            const topEdge = Math.max(8, bounds.top + 8);
            const bottomEdge = Math.min(viewport.bottom, bounds.bottom) - 8;
            // Closed details can retain their descendants' old layout bounds.
            const collapsed = anchor.closest("details:not([open])");
            const inSummary = collapsed?.querySelector(":scope > summary")?.contains(anchor);
            element.hidden = !anchor.isConnected || (collapsed && !inSummary) ||
                !anchor.getClientRects().length || target.bottom <= topEdge || target.top >= bottomEdge ||
                target.right <= leftEdge || target.left >= rightEdge;
            onVisibility(!element.hidden);
            if (element.hidden) return;
            element.style.maxWidth = `${Math.max(0, rightEdge - leftEdge)}px`;
            const width = element.offsetWidth;
            const height = element.offsetHeight;
            const x = target.left + target.width / 2;
            const y = target.top + target.height / 2;
            const available = {top: target.top - topEdge, bottom: bottomEdge - target.bottom,
                left: target.left - leftEdge, right: rightEdge - target.right};
            const opposite = {top: "bottom", bottom: "top", left: "right", right: "left"};
            const needed = ["top", "bottom"].includes(placement) ? height + 10 : width + 10;
            const side = available[placement] < needed && available[opposite[placement]] > available[placement]
                ? opposite[placement] : placement;
            let left = x - width / 2;
            let top = y - height / 2;
            if (side === "top") top = target.top - height - 10;
            if (side === "bottom") top = target.bottom + 10;
            if (side === "left") left = target.left - width - 10;
            if (side === "right") left = target.right + 10;
            left = clamp(left, leftEdge, rightEdge - width);
            top = clamp(top, topEdge, bottomEdge - height);
            element.dataset.placement = side;
            element.style.left = `${left}px`;
            element.style.top = `${top}px`;
            element.style.setProperty("--hint-arrow-x", `${clamp(x - left, 12, width - 12)}px`);
            element.style.setProperty("--hint-arrow-y", `${clamp(y - top, 12, height - 12)}px`);
        };
        const hide = () => { active = false; element.hidden = true; onVisibility(false); };
        const destroy = () => {
            if (destroyed) return;
            hide(); destroyed = true; controller.abort(); observer.disconnect(); element.remove();
            signal?.removeEventListener("abort", destroy);
        };
        const observer = new ResizeObserver(position);
        observer.observe(anchor);
        observer.observe(element);
        window.addEventListener("resize", position, {signal: controller.signal});
        document.addEventListener("scroll", position, {capture: true, signal: controller.signal});
        document.addEventListener("toggle", position, {capture: true, signal: controller.signal});
        container.addEventListener("close", destroy, {signal: controller.signal});
        document.addEventListener("page:before-change", destroy, {signal: controller.signal});
        element.querySelector("[data-hint-close]")?.addEventListener("click", () => {
            hide(); onDismiss(); anchor.focus({preventScroll: true});
        }, {signal: controller.signal});
        signal?.addEventListener("abort", destroy, {once: true});
        hide();
        return {show() { if (!destroyed) { active = true; position(); } }, hide, destroy, position};
    },
};
