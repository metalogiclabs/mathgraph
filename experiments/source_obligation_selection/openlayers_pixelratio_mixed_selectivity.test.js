import {assert} from 'chai';
import Map from '../../../../../../src/ol/Map.js';
import View from '../../../../../../src/ol/View.js';
import TileLayer from '../../../../../../src/ol/layer/Tile.js';
import XYZ from '../../../../../../src/ol/source/XYZ.js';

describe('MathGraph mixed pixel-ratio tile identity', function () {
  it('replaces only ratio-dependent tiles in a mixed cache', function () {
    const created = [];
    const source = new XYZ({
      transition: 0,
      tileUrlFunction(tileCoord, ratio) {
        const dependsOnRatio = tileCoord[1] % 2 === 0;
        const url = 'mathgraph-mixed://' + tileCoord.join('/') +
          (dependsOnRatio ? '?ratio=' + ratio : '?ratio-independent');
        created.push(url);
        return url;
      },
      tileLoadFunction(tile) {
        const canvas = document.createElement('canvas');
        canvas.width = 1;
        canvas.height = 1;
        tile.setImage(canvas);
      },
    });
    const layer = new TileLayer({source});
    const map = new Map({
      target: createMapDiv(128, 128),
      layers: [layer],
      pixelRatio: 1,
      view: new View({center: [0, 0], zoom: 2}),
    });

    function snapshot() {
      const cache = layer.getRenderer().getTileCache();
      return new MapCache(cache);
    }

    class MapCache {
      constructor(cache) {
        this.tiles = new globalThis.Map(
          cache.getKeys().map((key) => [key, cache.peek(key)]),
        );
      }
    }

    try {
      map.renderSync();
      const before = snapshot().tiles;
      assert.isAbove(before.size, 1, 'MIXED_CONTROL_NO_INITIAL_TILES');
      const expectedChanged = [...before.values()].filter(
        (tile) => tile.tileCoord[1] % 2 === 0,
      ).length;
      const expectedUnchanged = before.size - expectedChanged;
      assert.isAbove(expectedChanged, 0, 'MIXED_CONTROL_NO_DEPENDENT_TILE');
      assert.isAbove(expectedUnchanged, 0, 'MIXED_CONTROL_NO_INDEPENDENT_TILE');

      map.setPixelRatio(2);
      map.renderSync();
      const after = snapshot().tiles;
      assert.deepEqual([...after.keys()].sort(), [...before.keys()].sort());
      let changed = 0;
      let retained = 0;
      const errors = [];
      for (const [key, prior] of before) {
        const next = after.get(key);
        const dependent = prior.tileCoord[1] % 2 === 0;
        if (dependent) {
          if (next !== prior &&
              next?.src_?.endsWith('?ratio=2')) changed += 1;
          else errors.push({key,expected:'new ratio-2 tile',observed:next?.src_});
        } else {
          if (next === prior &&
              next?.src_?.endsWith('?ratio-independent')) retained += 1;
          else errors.push({key,expected:'same independent tile',observed:next?.src_});
        }
      }
      const result = {
        initial_tiles: before.size,
        changed,
        retained,
        expectedChanged,
        expectedUnchanged,
        url_function_calls: created.length,
        errors,
      };
      console.log('MATHGRAPH_MIXED_TILE_SELECTIVITY ' + JSON.stringify(result));
      assert.deepEqual(errors, [], 'MATHGRAPH_MIXED_SELECTIVITY_MISMATCH');
      assert.strictEqual(changed, expectedChanged);
      assert.strictEqual(retained, expectedUnchanged);
    } finally {
      disposeMap(map);
    }
  });
});
