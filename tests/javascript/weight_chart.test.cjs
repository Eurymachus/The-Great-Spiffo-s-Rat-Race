const assert = require('node:assert/strict');
const {test} = require('node:test');
const {groupRows, ranges, weightBounds} = require('../../apps/website/registry/static/registry/weight_chart.js');

test('axis pads daily extremes within the selected periods, not their averages', () => {
    const rows = [
        {day: 1, weight: 60}, {day: 8, weight: 77}, {day: 9, weight: 83},
    ];
    const weeks = groupRows(rows, 'week');
    assert.deepEqual(weightBounds(weeks), {minimum: 59, maximum: 84});
    assert.deepEqual(weightBounds(weeks.slice(-1)), {minimum: 76, maximum: 84});
    assert.deepEqual(weightBounds(groupRows([{day: 1, weight: 80}], 'day')), {minimum: 79, maximum: 81});
});

test('weekly weight is the mean, with survival weeks stable across missing days', () => {
    const result = groupRows([
        {day: 6, weight: 80}, {day: 7, weight: 82},
        {day: 9, weight: 79, inProgress: true},
    ], 'week');
    assert.deepEqual(result.map(p => [p.label, p.value, p.axis]), [
        ['Week 1', 81, '1'], ['Week 2', 79, '2*'],
    ]);
});
test('calendar months retain their year and average only available observations', () => {
    const result = groupRows([
        {day: 1, weight: 80, year: 1993, month: 12},
        {day: 2, weight: 78, year: 1993, month: 12},
        {day: 3, weight: 77, year: 1994, month: 1, inProgress: true},
        {day: 4, weight: 76},
    ], 'month');
    assert.deepEqual(result.map(p => [p.label, p.value, p.axis]), [
        ['Dec 1993', 79, 'Dec'], ['Jan 1994', 77, 'Jan*'],
    ]);
    assert.equal(result[1].index - result[0].index, 1);
});
test('daily mode retains exact values and matches Better Daily Reports ranges', () => {
    assert.equal(groupRows([{day: 74, weight: 79.125, inProgress: true}], 'day')[0].value, 79.125);
    assert.deepEqual(ranges, {day: [7, 28, 0], week: [12, 52, 0], month: [12, 0]});
    assert.deepEqual(groupRows([], 'day'), []);
});
