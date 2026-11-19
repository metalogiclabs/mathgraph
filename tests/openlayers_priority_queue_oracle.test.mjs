/** Native, independent-array-oracle probe for the preregistered OpenLayers
 * PriorityQueue hotspot. Run with OPENLAYERS_SOURCE_ROOT at the pinned checkout.
 * This is a bounded behavioral check, not whole-library verification. */
import assert from 'node:assert/strict';
import test from 'node:test';
import path from 'node:path';
import {pathToFileURL} from 'node:url';

const sourceRoot = process.env.OPENLAYERS_SOURCE_ROOT;
if (!sourceRoot) {
  throw new Error('OPENLAYERS_SOURCE_ROOT must point to the pinned OpenLayers checkout');
}
const {default: PriorityQueue, DROP} = await import(
  pathToFileURL(path.join(sourceRoot, 'src/ol/structs/PriorityQueue.js')).href
);

function shuffledOrder(length, seed) {
  const order = Array.from({length}, (_, i) => i);
  let state = seed >>> 0;
  for (let i = length - 1; i > 0; i--) {
    state = (Math.imul(1664525, state) + 1013904223) >>> 0;
    const j = state % (i + 1);
    [order[i], order[j]] = [order[j], order[i]];
  }
  return order;
}

test('two child indices mapping to one parent retain distinct queue elements', () => {
  const q = new PriorityQueue((x) => x.priority, (x) => x.key);
  assert.equal(q.getParentIndex_(1), 0);
  assert.equal(q.getParentIndex_(2), 0);
  const elements = [
    {key: 'root', priority: 3},
    {key: 'left', priority: 1},
    {key: 'right', priority: 2},
  ];
  for (const item of elements) assert.equal(q.enqueue(item), true);
  assert.equal(q.getCount(), 3);
  for (const item of elements) assert.equal(q.isKeyQueued(item.key), true);
  assert.deepEqual(
    [q.dequeue().key, q.dequeue().key, q.dequeue().key],
    ['left', 'right', 'root'],
  );
  assert.equal(q.getCount(), 0);
});

test('seeded distinct-priority insertions and removals match an independent sort oracle', () => {
  for (let seed = 1; seed <= 24; seed++) {
    const q = new PriorityQueue((x) => x.priority, (x) => x.key);
    const priorities = shuffledOrder(97, seed);
    const reference = [];
    priorities.forEach((priority, i) => {
      const item = {key: `${seed}:${i}`, priority};
      assert.equal(q.enqueue(item), true);
      reference.push(item);
      assert.equal(q.getCount(), reference.length);
    });
    reference.sort((a, b) => a.priority - b.priority);
    for (const item of reference) {
      assert.equal(q.dequeue().key, item.key);
      assert.equal(q.isKeyQueued(item.key), false);
    }
    assert.equal(q.isEmpty(), true);
  }
});

test('reprioritization and DROP preserve the non-dropped distinct elements', () => {
  const q = new PriorityQueue((x) => x.priority, (x) => x.key);
  const elements = shuffledOrder(90, 917).map((n) => ({key: `k${n}`, priority: n}));
  for (const item of elements) q.enqueue(item);
  for (const item of elements) {
    const id = Number(item.key.slice(1));
    item.priority = id % 3 === 0 ? DROP : 1000 - id;
  }
  q.reprioritize();
  const kept = elements.filter((x) => x.priority !== DROP);
  assert.equal(q.getCount(), kept.length);
  for (const item of elements) {
    assert.equal(q.isKeyQueued(item.key), item.priority !== DROP);
  }
  kept.sort((a, b) => a.priority - b.priority);
  for (const item of kept) assert.equal(q.dequeue().key, item.key);
  assert.equal(q.isEmpty(), true);
});
