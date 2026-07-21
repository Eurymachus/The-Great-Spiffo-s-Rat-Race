document.addEventListener("DOMContentLoaded", () => {
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    document.querySelectorAll("[data-gallery]").forEach((gallery) => {
        const slides = [...gallery.querySelectorAll("[data-gallery-slide]")];
        if (!slides.length) return;
        const count = gallery.querySelector("[data-gallery-count]");
        let index = 0;
        let timer = null;
        let expanded = false;
        const loop = gallery.dataset.loop === "true";
        const delay = Number(gallery.dataset.scrollSpeed || 5) * 1000;
        const show = (next) => {
            if (loop) index = (next + slides.length) % slides.length;
            else index = Math.max(0, Math.min(slides.length - 1, next));
            slides.forEach((slide, slideIndex) => {
                const active = slideIndex === index;
                slide.hidden = !active;
                slide.classList.toggle("is-active", active);
            });
            if (count) count.textContent = `${index + 1} of ${slides.length}`;
            const previous = gallery.querySelector("[data-gallery-previous]");
            const nextButton = gallery.querySelector("[data-gallery-next]");
            if (previous) previous.disabled = !loop && index === 0;
            if (nextButton) nextButton.disabled = !loop && index === slides.length - 1;
        };
        const stop = () => {
            if (timer) window.clearTimeout(timer);
            timer = null;
        };
        const start = () => {
            if (timer || expanded || reducedMotion || gallery.dataset.autoScroll !== "true" || slides.length < 2) return;
            if (!loop && index === slides.length - 1) return;
            timer = window.setTimeout(() => {
                timer = null;
                show(index + 1);
                start();
            }, delay);
        };
        const move = (offset) => {
            stop();
            show(index + offset);
            start();
        };
        gallery.querySelector("[data-gallery-previous]")?.addEventListener("click", (event) => {
            move(-1);
            if (event.detail > 0) event.currentTarget.blur();
        });
        gallery.querySelector("[data-gallery-next]")?.addEventListener("click", (event) => {
            move(1);
            if (event.detail > 0) event.currentTarget.blur();
        });
        gallery.addEventListener("mouseenter", stop);
        gallery.addEventListener("mouseleave", start);
        gallery.addEventListener("focusin", stop);
        gallery.addEventListener("focusout", (event) => { if (!gallery.contains(event.relatedTarget)) start(); });
        const expandButton = gallery.querySelector("[data-gallery-expand]");
        expandButton?.addEventListener("click", () => {
            stop();
            expanded = true;
            const dialog = document.createElement("dialog");
            dialog.className = "managed-gallery-dialog";
            dialog.innerHTML = `<div class="managed-gallery-dialog-viewer">
                <button type="button" class="managed-gallery-dialog-close" aria-label="Close expanded gallery">&times;</button>
                <button type="button" class="managed-gallery-dialog-nav is-previous" aria-label="Previous expanded image">&#8249;</button>
                <figure><img><figcaption></figcaption></figure>
                <button type="button" class="managed-gallery-dialog-nav is-next" aria-label="Next expanded image">&#8250;</button>
                <output aria-live="polite"></output>
            </div>`;
            let expandedIndex = index;
            const expandedImage = dialog.querySelector("img");
            const expandedCaption = dialog.querySelector("figcaption");
            const expandedCount = dialog.querySelector("output");
            const expandedPrevious = dialog.querySelector(".managed-gallery-dialog-nav.is-previous");
            const expandedNext = dialog.querySelector(".managed-gallery-dialog-nav.is-next");
            const showExpanded = (next) => {
                expandedIndex = loop
                    ? (next + slides.length) % slides.length
                    : Math.max(0, Math.min(slides.length - 1, next));
                const source = slides[expandedIndex];
                expandedImage.src = source.querySelector("img").src;
                expandedImage.alt = source.querySelector("img").alt;
                const caption = source.querySelector("figcaption")?.textContent || "";
                expandedCaption.textContent = caption;
                expandedCaption.hidden = !caption;
                expandedCount.textContent = `${expandedIndex + 1} of ${slides.length}`;
                expandedPrevious.disabled = !loop && expandedIndex === 0;
                expandedNext.disabled = !loop && expandedIndex === slides.length - 1;
            };
            dialog.querySelector(".managed-gallery-dialog-close").addEventListener("click", () => dialog.close());
            expandedPrevious.addEventListener("click", () => showExpanded(expandedIndex - 1));
            expandedNext.addEventListener("click", () => showExpanded(expandedIndex + 1));
            dialog.addEventListener("keydown", (event) => {
                if (event.key === "ArrowLeft") { event.preventDefault(); showExpanded(expandedIndex - 1); }
                if (event.key === "ArrowRight") { event.preventDefault(); showExpanded(expandedIndex + 1); }
            });
            dialog.addEventListener("click", (event) => { if (event.target === dialog) dialog.close(); });
            dialog.addEventListener("close", () => {
                expanded = false;
                show(expandedIndex);
                dialog.remove();
                start();
                requestAnimationFrame(() => expandButton.blur());
            });
            document.body.append(dialog);
            showExpanded(expandedIndex);
            dialog.showModal();
        });
        show(0);
        start();
    });
});
