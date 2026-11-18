import {assert} from 'chai';
import Map from '../../../../../../src/ol/Map.js';
import View from '../../../../../../src/ol/View.js';
import TileLayer from '../../../../../../src/ol/layer/Tile.js';
import XYZ from '../../../../../../src/ol/source/XYZ.js';

describe('MathGraph ratio-independent cache churn diagnostic', function () {
  it('measures cache retention across an allowed pixel-ratio change', function () {
    const requests = [];
    const source = new XYZ({
      transition: 0,
      tileUrlFunction(tileCoord) {
        const url = 'mathgraph-ratio-independent://' + tileCoord.join('/');
        requests.push(url);
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
    try {
      map.renderSync();
      const cache = layer.getRenderer().getTileCache();
      const keysBefore = cache.getKeys();
      assert.isAbove(keysBefore.length, 0, 'CHURN_DIAGNOSTIC_NO_INITIAL_TILES');
      const tilesBefore = keysBefore.map((key) => cache.get(key));
      const firstCallCount = requests.length;
      map.setPixelRatio(2);
      map.renderSync();
      const keysAfter = cache.getKeys();
      const retained = keysBefore.every(
        (key, i) => cache.containsKey(key) && cache.get(key) === tilesBefore[i],
      );
      const result = {
        source_urls_depend_on_ratio: false,
        initial_keys: keysBefore.length,
        final_keys: keysAfter.length,
        tile_url_calls_before: firstCallCount,
        tile_url_calls_after: requests.length,
        extra_calls: requests.length - firstCallCount,
        retained_same_tile_objects: retained,
      };
      console.log('MATHGRAPH_RATIO_INDEPENDENT_CHURN ' + JSON.stringify(result));
      assert.strictEqual(map.getPixelRatio(), 2);
      assert.isAbove(keysAfter.length, 0, 'CHURN_DIAGNOSTIC_NO_FINAL_TILES');
    } finally {
      disposeMap(map);
    }
  });
});
