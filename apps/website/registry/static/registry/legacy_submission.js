(() => {
    "use strict";
    const input = document.querySelector("[data-survival-time]");
    const preview = document.querySelector("[data-survival-preview]");
    if (!input || !preview) return;

    const parse = (raw) => {
        const value = raw.trim().replace(/\s+/g, " ");
        let parts;
        const colon = value.match(/^(\d+):(\d{1,2}):(\d{1,2}):(\d{1,2})$/);
        if (colon) {
            parts = colon.slice(1).map(Number);
        } else {
            const units = {years: 0, months: 0, days: 0, hours: 0};
            const matches = [...value.matchAll(/(\d+)\s*(years?|yrs?|y|months?|mos?|mo|days?|d|hours?|hrs?|h)\b/gi)];
            if (!matches.length) return null;
            const consumed = matches.map((match) => match[0]).join(" ").replace(/,/g, "").replace(/\s+/g, " ");
            if (consumed.toLowerCase() !== value.replace(/,/g, "").toLowerCase()) return null;
            for (const match of matches) {
                const unit = match[2].toLowerCase();
                const key = unit.startsWith("y") ? "years" : unit.startsWith("mo") ? "months" : unit.startsWith("d") ? "days" : "hours";
                units[key] += Number(match[1]);
            }
            parts = [units.years, units.months, units.days, units.hours];
        }
        const totalHours = parts[0] * 8640 + parts[1] * 720 + parts[2] * 24 + parts[3];
        if (!Number.isFinite(totalHours) || totalHours <= 0) return null;
        let remainder = totalHours;
        const years = Math.floor(remainder / 8640); remainder %= 8640;
        const months = Math.floor(remainder / 720); remainder %= 720;
        const days = Math.floor(remainder / 24); const hours = remainder % 24;
        const full = [years, months, days, hours].map((part) => String(part).padStart(2, "0")).join(":");
        return {full, days: totalHours / 24};
    };
    const update = () => {
        const result = parse(input.value);
        preview.hidden = !result;
        preview.textContent = result ? `Full time: ${result.full} · Survival time: ${result.days.toFixed(2)} days` : "";
    };
    input.addEventListener("input", update);
    update();
})();
