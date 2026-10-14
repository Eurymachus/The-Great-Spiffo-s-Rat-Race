const {test} = require('node:test');
const assert = require('node:assert/strict');
const {groupRows, ranges, temperatureBounds} = require('../../apps/website/registry/static/registry/temperature_chart.js');

test('periods retain extremes, timestamps, ties and partial coverage', () => {
    const first = {celsius: -13, timeOfDay: 6};
    const points = groupRows([
        {day: 1, minimum: -13, maximum: 0, minimumObservation: first, partial: true},
        {day: 2, minimum: -13, maximum: 5, minimumObservation: {celsius: -13, timeOfDay: 7}},
        {day: 8, minimum: -3, maximum: 8, inProgress: true},
    ], 'week');
    assert.deepEqual(points.map(p => [p.minimum, p.maximum]), [[-13, 5], [-3, 8]]);
    assert.equal(points[0].minimumObservation, first);
    assert.equal(points[0].partial, true);
    assert.equal(points[1].inProgress, true);
    assert.deepEqual(temperatureBounds(points), {minimum: -14, maximum: 9});
});
test('calendar months retain years and daily gaps are not filled', () => {
    const rows = [{day: 1, minimum: 0, maximum: 2, year: 1993, month: 12},
        {day: 3, minimum: -8, maximum: 1, year: 1994, month: 1}];
    assert.deepEqual(groupRows(rows, 'day').map(p => p.index), [1, 3]);
    assert.deepEqual(groupRows(rows, 'month').map(p => p.label), ['Dec 1993', 'Jan 1994']);
    assert.deepEqual(ranges, {day: [7, 28, 0], week: [12, 52, 0], month: [12, 0]});
});
