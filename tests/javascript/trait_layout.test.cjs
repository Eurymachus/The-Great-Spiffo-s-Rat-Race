const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {chromium} = require('playwright');

test('trait columns wrap nine rows without growing on tall viewports', async () => {
    const browser = await chromium.launch({channel: 'msedge', headless: true});
    try {
        const page = await browser.newPage();
        const css = fs.readFileSync('apps/website/registry/static/registry/site.css', 'utf8');
        const rows = Array.from({length: 14}, (_, i) => `<li><span></span><span>Trait ${i + 1}</span><strong>+2</strong></li>`).join('');
        const column = `<section class="leaderboard-trait-column"><h4>Traits</h4><ul>${rows}</ul></section>`;
        await page.setContent(`<style>${css}</style><dialog class="leaderboard-build-modal character-build-traits-dialog"><header>Character build</header><div class="leaderboard-build-content"><section class="leaderboard-profession">Profession</section><div class="build-trait-tabs">Starting traits</div><section class="build-traits-section"><h3>Selected traits</h3><div class="leaderboard-trait-columns">${column}${column}</div></section><section class="build-traits-section" hidden>Hidden traits</section></div></dialog>`);
        await page.evaluate(() => document.querySelector('dialog').showModal());
        for (const height of [1100, 2100, 650]) {
            await page.setViewportSize({width: 1440, height});
            const result = await page.evaluate(() => {
                const list = document.querySelector('.leaderboard-trait-column ul');
                const column = list.parentElement.getBoundingClientRect();
                const bounds = list.getBoundingClientRect();
                const ninth = list.children[8].getBoundingClientRect();
                const dialog = document.querySelector('dialog').getBoundingClientRect();
                return {height: bounds.height, blank: column.bottom - bounds.bottom, ninth: ninth.bottom - bounds.top, dialog: dialog.height, bottomGap: dialog.bottom - column.bottom};
            });
            assert.ok(result.blank <= 2, JSON.stringify(result));
            assert.ok(result.dialog <= height - 30, JSON.stringify(result));
            assert.ok(result.bottomGap < 25, JSON.stringify(result));
            if (height >= 1100) {
                assert.ok(Math.abs(result.height - 440) < 1, JSON.stringify(result));
                assert.ok(Math.abs(result.height - result.ninth - 8) < 1, JSON.stringify(result));
            }
            if (height === 1100 && process.env.TRAIT_LAYOUT_SCREENSHOT) {
                await page.screenshot({path: process.env.TRAIT_LAYOUT_SCREENSHOT});
            }
        }
    } finally {
        await browser.close();
    }
});
