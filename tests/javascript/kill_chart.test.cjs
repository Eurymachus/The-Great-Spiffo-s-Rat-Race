const {test} = require('node:test');
const assert = require('node:assert/strict');
const {groupRows, killBounds} = require('../../apps/website/registry/static/registry/weight_chart.js');

test('kill axis ticks are whole counts with headroom, including small totals', () => {
 for (const maximum of [0, 1, 2, 1230, 1000000]) {
  const bounds = killBounds([{value: maximum}]);
  assert.ok(bounds.maximum > maximum);
  for (let tick=0; tick<=5; tick++) assert.ok(Number.isInteger(bounds.maximum * tick / 5));
 }
});
test('kill delta periods sum counts and preserve zero days and gaps', () => {
 const rows = [{day:1,kills:12,year:1993,month:11},{day:2,kills:0,year:1993,month:11},{day:8,kills:8,year:1993,month:12,inProgress:true}];
 assert.deepEqual(groupRows(rows,'day','kills').map(p=>p.value),[12,0,8]);
 assert.deepEqual(groupRows(rows,'week','kills').map(p=>p.value),[12,8]);
 assert.deepEqual(groupRows(rows,'month','kills').map(p=>p.value),[12,8]);
 assert.equal(groupRows(rows,'week','kills')[1].inProgress,true);
});
