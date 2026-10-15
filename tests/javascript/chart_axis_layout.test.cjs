const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {chromium} = require('playwright');

test('formatted axis labels remain inside the plot at desktop and mobile widths', async () => {
    const browser = await chromium.launch({channel: 'msedge', headless: true});
    try {
        const page = await browser.newPage();
        const css = fs.readFileSync('apps/website/registry/static/registry/site.css', 'utf8');
        const script = fs.readFileSync('apps/website/registry/static/registry/weight_chart.js', 'utf8');
        for (const width of [360, 900]) {
            for (const value of [1230, 1000000]) {
                await page.setViewportSize({width, height: 700});
                await page.setContent(`<style>${css}</style><dialog open><div data-weight-chart="rows" data-chart-metric="kills"><select data-weight-group><option value="day">Day</option></select><select data-weight-range><option value="0">All</option></select><div data-weight-plot tabindex="0"><svg></svg><span data-weight-tooltip hidden></span></div><span data-weight-progress></span><span data-weight-description></span></div></dialog><script id="rows" type="application/json">[{"day":1,"kills":${value}}]</script>`);
                await page.addScriptTag({content: script});
                const boxes = await page.locator('svg text[dominant-baseline]').evaluateAll(labels => labels.map(label => {
                    const box = label.getBBox();
                    return {x: box.x, text: label.textContent};
                }));
                assert.equal(boxes.length, 6);
                assert.ok(boxes.every(box => box.x >= 7), JSON.stringify(boxes));
                assert.ok(boxes.every(box => !box.text.includes('.')), JSON.stringify(boxes));
            }
        }
    } finally { await browser.close(); }
});
