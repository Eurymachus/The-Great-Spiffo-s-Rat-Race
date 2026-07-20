document.addEventListener("DOMContentLoaded", () => {
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    document.querySelectorAll("[data-gallery]").forEach((gallery) => {
        const slides = [...gallery.querySelectorAll("[data-gallery-slide]")];
        if (!slides.length) return;
        const count = gallery.querySelector("[data-gallery-count]");
        let index = 0;
        let timer = null;
        const loop = gallery.dataset.loop === "true";
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
        gallery.querySelector("[data-gallery-previous]")?.addEventListener("click", () => show(index - 1));
        gallery.querySelector("[data-gallery-next]")?.addEventListener("click", () => show(index + 1));
        const start = () => {
            if (reducedMotion || gallery.dataset.autoScroll !== "true" || slides.length < 2) return;
            timer = window.setInterval(() => {
                if (!loop && index === slides.length - 1) { window.clearInterval(timer); timer = null; return; }
                show(index + 1);
            }, Number(gallery.dataset.scrollSpeed || 5) * 1000);
        };
        const stop = () => { if (timer) window.clearInterval(timer); timer = null; };
        gallery.addEventListener("mouseenter", stop);
        gallery.addEventListener("mouseleave", start);
        gallery.addEventListener("focusin", stop);
        gallery.addEventListener("focusout", (event) => { if (!gallery.contains(event.relatedTarget)) start(); });
        gallery.querySelector("[data-gallery-expand]")?.addEventListener("click", () => {
            const source = slides[index];
            const dialog = document.createElement("dialog");
            dialog.className = "managed-gallery-dialog";
            dialog.innerHTML = '<button type="button" aria-label="Close expanded image">&times;</button><figure><img><figcaption></figcaption></figure>';
            const image = dialog.querySelector("img");
            image.src = source.querySelector("img").src;
            image.alt = source.querySelector("img").alt;
            const caption = source.querySelector("figcaption")?.textContent || "";
            dialog.querySelector("figcaption").textContent = caption;
            dialog.querySelector("figcaption").hidden = !caption;
            dialog.querySelector("button").addEventListener("click", () => dialog.close());
            dialog.addEventListener("click", (event) => { if (event.target === dialog) dialog.close(); });
            dialog.addEventListener("close", () => dialog.remove());
            document.body.append(dialog);
            dialog.showModal();
        });
        show(0);
        start();
    });
});
