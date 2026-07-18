document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("input.branding-range").forEach((input) => {
        const output = document.createElement("output");
        output.className = "branding-range-value";
        output.htmlFor = input.id;
        const update = () => { output.value = `${input.value}%`; };
        input.insertAdjacentElement("afterend", output);
        input.addEventListener("input", update);
        update();
    });
});
