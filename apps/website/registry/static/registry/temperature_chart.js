(() => {
    "use strict";
    const ranges = {day: [7, 28, 0], week: [12, 52, 0], month: [12, 0]};
    const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    const number = new Intl.NumberFormat(undefined, {maximumFractionDigits: 3});

    // Group the full history before selecting the most recent periods.
    const groupRows = (rows, mode) => {
        const buckets = new Map();
        for (const row of rows) {
            if (mode === "month" && (!row.year || !row.month)) continue;
            const index = mode === "day" ? row.day : mode === "week"
                ? Math.floor((row.day - 1) / 7) + 1 : row.year * 12 + row.month - 1;
            if (!buckets.has(index)) {
                const axis = mode === "month" ? months[row.month - 1] : String(index);
                const label = mode === "month" ? `${axis} ${row.year}` : `${mode === "week" ? "Week" : "Day"} ${index}`;
                buckets.set(index, {index, axis, label, minimum: Infinity, maximum: -Infinity, inProgress: false});
            }
            const bucket = buckets.get(index);
            if (row.minimum < bucket.minimum) {
                bucket.minimum = row.minimum;
                bucket.minimumObservation = row.minimumObservation;
            }
            if (row.maximum > bucket.maximum) {
                bucket.maximum = row.maximum;
                bucket.maximumObservation = row.maximumObservation;
            }
            bucket.partial ||= row.partial;
            bucket.inProgress ||= row.inProgress;
        }
        return [...buckets.values()].sort((a, b) => a.index - b.index).map((bucket) => ({
            ...bucket,
            axis: bucket.axis + (bucket.inProgress ? "*" : ""),
        }));
    };

    const temperatureBounds = (data) => ({
        minimum: Math.min(...data.map((point) => point.minimum)) - 1,
        maximum: Math.max(...data.map((point) => point.maximum)) + 1,
    });

    const initialise = (root = document) => {
        root.querySelectorAll("[data-temperature-chart]").forEach((chart) => {
            if (chart.dataset.ready) return;
            chart.dataset.ready = "true";
            const rows = JSON.parse(document.getElementById(chart.dataset.temperatureChart).textContent);
            const group = chart.querySelector("[data-temperature-group]");
            const range = chart.querySelector("[data-temperature-range]");
            const plot = chart.querySelector("[data-temperature-plot]");
            const svg = chart.querySelector("svg");
            const tooltip = chart.querySelector("[data-temperature-tooltip]");
            const progress = chart.querySelector("[data-temperature-progress]");
            const toggles = [...chart.querySelectorAll("[data-temperature-series]")];
            const description = chart.querySelector("[data-temperature-description]");
            let points = [], selection = 0;
            const node = (tag, attrs, text) => {
                const element = document.createElementNS("http://www.w3.org/2000/svg", tag);
                for (const [key, value] of Object.entries(attrs)) element.setAttribute(key, value);
                if (text !== undefined) element.textContent = text;
                svg.append(element);
                return element;
            };
            const hide = () => {
                tooltip.hidden = true;

            };
            const select = (index) => {
                if (!points.length) return;
                selection = Math.max(0, Math.min(points.length - 1, index));
                const point = points[selection];
                const stamp = (observation) => {
                    if (!observation?.calendar) return "";
                    const c = observation.calendar;
                    const minutes = Math.floor(observation.timeOfDay * 60 + 0.00001);
                    return ` (${c.day} ${months[c.month - 1]} ${c.year}, ${String(Math.floor(minutes / 60)).padStart(2, "0")}:${String(minutes % 60).padStart(2, "0")})`;
                };
                const text = point.label + toggles.filter(t => t.checked).map(t => {
                    const key = t.dataset.temperatureSeries;
                    return ` ${key === "minimum" ? "Lowest" : "Highest"}: ${number.format(point[key])} \u00b0C${stamp(point[key + "Observation"])}`;
                }).join("; ") + (point.inProgress ? " (In Progress)" : "") + (point.partial ? " (Partial history)" : "");
                plot.setAttribute("aria-valuenow", selection);
                plot.setAttribute("aria-valuetext", text);
                const heading = document.createElement("strong");
                heading.textContent = point.label;
                const entries = toggles.filter(t => t.checked).map(t => {
                    const key = t.dataset.temperatureSeries;
                    const row = document.createElement("div");
                    row.className = "temperature-tooltip-entry";
                    const value = document.createElement("span");
                    value.className = key === "minimum" ? "temperature-low" : "temperature-high";
                    value.textContent = `${key === "minimum" ? "Lowest" : "Highest"}: ${number.format(point[key])} \u00b0C`;
                    const time = document.createElement("small");
                    time.textContent = stamp(point[key + "Observation"]).trim().replace(/^\(|\)$/g, "");
                    row.append(value, time);
                    return row;
                });
                const status = document.createElement("small");
                status.textContent = [point.inProgress && "In progress", point.partial && "Partial history"].filter(Boolean).join(" \u00b7 ");
                tooltip.replaceChildren(heading, ...entries, ...(status.textContent ? [status] : []));
                tooltip.hidden = false;
                tooltip.style.left = `${Math.max(8, Math.min(point.x + 12, plot.clientWidth - tooltip.offsetWidth - 8))}px`;
                tooltip.style.top = "8px";
            };
            const render = () => {
                const width = Math.max(260, plot.clientWidth);
                const height = width < 480 ? 270 : 320;
                svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
                svg.style.height = `${height}px`;
                svg.replaceChildren();
                tooltip.hidden = true;
                let data = groupRows(rows, group.value);
                const limit = Number(range.value);
                if (limit && data.length) data = data.filter(p => p.index > data[data.length - 1].index - limit);
                plot.setAttribute("aria-valuemax", Math.max(0, data.length - 1));
                progress.hidden = !data.some((point) => point.inProgress);
                description.textContent = (group.value === "day" ? "Daily" : group.value === "week" ? "Weekly" : "Monthly") + " extremes (\u00b0C)";
                const series = toggles.filter(t => t.checked).map(t => t.dataset.temperatureSeries);
                if (!data.length || !series.length) {
                    points = [];
                    const message = !series.length ? "Select a temperature line." : "No recorded dates for this range.";
                    plot.setAttribute("aria-valuenow", "0");
                    plot.setAttribute("aria-valuetext", message);
                    node("text", {x: width / 2, y: height / 2, "text-anchor": "middle"}, message);
                    return;
                }
                const left = 52, right = width - 22, top = 20, bottom = height - 36;
                const {minimum, maximum} = temperatureBounds(data);
                const temperatureSpan = maximum - minimum;
                for (let tick = 0; tick <= 5; tick += 1) {
                    const y = bottom - (bottom - top) * tick / 5;
                    node("line", {x1: left, x2: right, y1: y, y2: y, class: "weight-grid"});
                    node("text", {x: left - 10, y, "text-anchor": "end", "dominant-baseline": "middle"}, number.format(minimum + temperatureSpan * tick / 5));
                }
                const first = data[0].index, span = data[data.length - 1].index - first;
                points = data.map((point) => ({...point,
                    x: span ? left + (point.index - first) / span * (right - left) : (left + right) / 2,
                }));
                const y = value => bottom - (value - minimum) / temperatureSpan * (bottom - top);
                for (const key of series) {
                    let segment = [];
                    const flush = () => { node("polyline", {points: segment.join(" "), class: "temperature-line temperature-" + key}); segment = []; };
                    points.forEach((point, index) => {
                        if (index && point.index !== points[index - 1].index + 1) flush();
                        segment.push(`${point.x},${y(point[key])}`);
                        node("circle", {cx: point.x, cy: y(point[key]), r: points.length > 100 ? 1.5 : 3, class: "temperature-point temperature-" + key});
                    });
                    flush();
                }
                let lastLabelX = -Infinity;
                points.forEach((point, index) => {
                    const last = index === points.length - 1;
                    if (!index || last || (point.x - lastLabelX >= 100 && right - point.x >= 100)) {
                        node("text", {x: point.x, y: height - 10, "text-anchor": !index ? "start" : last ? "end" : "middle"}, point.axis);
                        lastLabelX = point.x;
                    }
                });
                select(points.length - 1);
                if (document.activeElement !== plot) hide();
            };
            const updateRanges = () => {
                const old = Number(range.value);
                range.replaceChildren(...ranges[group.value].map((value) => new Option(value ? `Last ${value}` : "All Time", value)));
                range.value = ranges[group.value].includes(old) ? String(old) : String(ranges[group.value][0]);
                render();
            };
            toggles.forEach(toggle => toggle.addEventListener("change", render));
            group.addEventListener("change", updateRanges);
            range.addEventListener("change", render);
            plot.addEventListener("pointermove", (event) => {
                const x = event.clientX - plot.getBoundingClientRect().left;
                let closest = 0;
                points.forEach((point, index) => {
                    if (Math.abs(point.x - x) < Math.abs(points[closest].x - x)) closest = index;
                });
                select(closest);
            });
            plot.addEventListener("pointerleave", hide);
            plot.addEventListener("focus", () => select(selection));
            plot.addEventListener("blur", hide);
            plot.addEventListener("keydown", (event) => {
                const indices = {ArrowLeft: selection - 1, ArrowRight: selection + 1, Home: 0, End: points.length - 1};
                if (event.key in indices) { event.preventDefault(); select(indices[event.key]); }
            });
            const observer = new ResizeObserver(render);
            observer.observe(plot);
            chart.closest("dialog").addEventListener("close", hide);
            document.addEventListener("page:before-change", () => observer.disconnect(), {once: true});
            render();
        });
    };
    if (typeof module !== "undefined") module.exports = {groupRows, ranges, temperatureBounds};
    if (typeof document !== "undefined") {
        document.addEventListener("page:loaded", () => initialise());
        initialise();
    }
})();
