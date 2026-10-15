(() => {
    "use strict";
    const ranges = {day: [7, 28, 0], week: [12, 52, 0], month: [12, 0]};
    const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    const number = new Intl.NumberFormat(undefined, {maximumFractionDigits: 3});

    // Group the full history before selecting the most recent periods.
    const groupRows = (rows, mode, metric = "weight") => {
        const buckets = new Map();
        for (const row of rows) {
            if (mode === "month" && (!row.year || !row.month)) continue;
            const index = mode === "day" ? row.day : mode === "week"
                ? Math.floor((row.day - 1) / 7) + 1 : row.year * 12 + row.month - 1;
            if (!buckets.has(index)) {
                const axis = mode === "month" ? months[row.month - 1] : String(index);
                const label = mode === "month" ? `${axis} ${row.year}` : `${mode === "week" ? "Week" : "Day"} ${index}`;
                buckets.set(index, {index, axis, label, total: 0, count: 0, minimum: Infinity, maximum: -Infinity, inProgress: false});
            }
            const bucket = buckets.get(index);
            bucket.total += row[metric];
            bucket.count += 1;
            bucket.minimum = Math.min(bucket.minimum, row[metric]);
            bucket.maximum = Math.max(bucket.maximum, row[metric]);
            bucket.inProgress ||= row.inProgress;
        }
        return [...buckets.values()].sort((a, b) => a.index - b.index).map((bucket) => ({
            ...bucket, value: metric === "kills" ? bucket.total : bucket.total / bucket.count,
            axis: bucket.axis + (bucket.inProgress ? "*" : ""),
        }));
    };

    const weightBounds = (data) => ({
        minimum: Math.min(...data.map((point) => point.minimum)) - 1,
        maximum: Math.max(...data.map((point) => point.maximum)) + 1,
    });

    const initialise = (root = document) => {
        root.querySelectorAll("[data-weight-chart]").forEach((chart) => {
            if (chart.dataset.ready) return;
            chart.dataset.ready = "true";
            const isKills = chart.dataset.chartMetric === "kills";
            const rows = JSON.parse(document.getElementById(chart.dataset.weightChart).textContent);
            const group = chart.querySelector("[data-weight-group]");
            const range = chart.querySelector("[data-weight-range]");
            const plot = chart.querySelector("[data-weight-plot]");
            const svg = chart.querySelector("svg");
            const tooltip = chart.querySelector("[data-weight-tooltip]");
            const progress = chart.querySelector("[data-weight-progress]");
            const description = chart.querySelector("[data-weight-description]");
            let points = [], selection = 0, marker;
            const node = (tag, attrs, text) => {
                const element = document.createElementNS("http://www.w3.org/2000/svg", tag);
                for (const [key, value] of Object.entries(attrs)) element.setAttribute(key, value);
                if (text !== undefined) element.textContent = text;
                svg.append(element);
                return element;
            };
            const hide = () => {
                tooltip.hidden = true;
                if (marker) marker.style.visibility = "hidden";
            };
            const select = (index) => {
                if (!points.length) return;
                selection = Math.max(0, Math.min(points.length - 1, index));
                const point = points[selection];
                const text = `${point.label}: ${number.format(point.value)} ${isKills ? "kills" : "kg"}${point.inProgress ? " (In Progress)" : ""}`;
                plot.setAttribute("aria-valuenow", selection);
                plot.setAttribute("aria-valuetext", text);
                tooltip.textContent = text;
                tooltip.hidden = false;
                tooltip.style.left = `${Math.max(8, Math.min(point.x + 12, plot.clientWidth - tooltip.offsetWidth - 8))}px`;
                tooltip.style.top = `${point.y < 90 ? point.y + 22 : point.y - tooltip.offsetHeight - 14}px`;
                marker.setAttribute("x", point.x - 5);
                marker.setAttribute("y", point.y - 5);
                marker.style.visibility = "visible";
            };
            const render = () => {
                const width = Math.max(260, plot.clientWidth);
                const height = width < 480 ? 270 : 320;
                svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
                svg.style.height = `${height}px`;
                svg.replaceChildren();
                tooltip.hidden = true;
                let data = groupRows(rows, group.value, isKills ? "kills" : "weight");
                const limit = Number(range.value);
                if (limit && data.length) data = data.filter(p => p.index > data[data.length - 1].index - limit);
                plot.setAttribute("aria-valuemax", Math.max(0, data.length - 1));
                progress.hidden = !data.some((point) => point.inProgress);
                description.textContent = isKills ? "Kills gained per " + group.value : group.value === "day" ? "Daily weight" : "Average daily weight per " + group.value;
                if (!data.length) {
                    points = [];
                    node("text", {x: width / 2, y: height / 2, "text-anchor": "middle"}, "No recorded dates for this range.");
                    return;
                }
                const left = 52, right = width - 22, top = 20, bottom = height - 36;
                const {minimum, maximum} = isKills ? {minimum: 0, maximum: Math.max(1, ...data.map(p => p.value)) * 1.1} : weightBounds(data);
                const weightSpan = maximum - minimum;
                for (let tick = 0; tick <= 5; tick += 1) {
                    const y = bottom - (bottom - top) * tick / 5;
                    node("line", {x1: left, x2: right, y1: y, y2: y, class: "weight-grid"});
                    node("text", {x: left - 10, y, "text-anchor": "end", "dominant-baseline": "middle"}, number.format(minimum + weightSpan * tick / 5));
                }
                const first = data[0].index, span = data[data.length - 1].index - first;
                points = data.map((point) => ({...point,
                    x: span ? left + (point.index - first) / span * (right - left) : (left + right) / 2,
                    y: bottom - (point.value - minimum) / weightSpan * (bottom - top),
                }));
                let segment = [];
                const flush = () => { node("polyline", {points: segment.join(" "), class: "weight-line"}); segment = []; };
                points.forEach((point, index) => {
                    if (index && point.index !== points[index - 1].index + 1) flush();
                    segment.push(`${point.x},${point.y}`);
                });
                flush();
                const size = points.length > 100 ? 2 : 4;
                points.forEach((point) => node("rect", {
                    x: point.x - size / 2, y: point.y - size / 2, width: size, height: size,
                    class: "weight-point" + (point.inProgress ? " is-active" : ""),
                }));
                let lastLabelX = -Infinity;
                points.forEach((point, index) => {
                    const last = index === points.length - 1;
                    if (!index || last || (point.x - lastLabelX >= 100 && right - point.x >= 100)) {
                        node("text", {x: point.x, y: height - 10, "text-anchor": !index ? "start" : last ? "end" : "middle"}, point.axis);
                        lastLabelX = point.x;
                    }
                });
                marker = node("rect", {width: 10, height: 10, class: "weight-selected"});
                select(points.length - 1);
                if (document.activeElement !== plot) hide();
            };
            const updateRanges = () => {
                const old = Number(range.value);
                range.replaceChildren(...ranges[group.value].map((value) => new Option(value ? `Last ${value}` : "All Time", value)));
                range.value = ranges[group.value].includes(old) ? String(old) : String(ranges[group.value][0]);
                render();
            };
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
    if (typeof module !== "undefined") module.exports = {groupRows, ranges, weightBounds};
    if (typeof document !== "undefined") {
        document.addEventListener("page:loaded", () => initialise());
        initialise();
    }
})();
