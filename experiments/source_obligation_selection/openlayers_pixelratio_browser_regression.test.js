import {assert} from 'chai';
import Map from '../../../../../../src/ol/Map.js';
import View from '../../../../../../src/ol/View.js';
import TileLayer from '../../../../../../src/ol/layer/Tile.js';
import XYZ from '../../../../../../src/ol/source/XYZ.js';

const URL_PREFIX = 'mathgraph-pixel-ratio://';

function newMap(pixelRatio) {
  const requestedRatios = [];
  const source = new XYZ({
    transition: 0,
    tileUrlFunction(tileCoord, requestedRatio) {
      requestedRatios.push(requestedRatio);
      return URL_PREFIX + requestedRatio + '/' + tileCoord.join('/');
    },
    tileLoadFunction(tile) {
      // Avoid external HTTP and make this a deterministic real-browser render.
      const canvas = document.createElement('canvas');
      canvas.width = 1;
      canvas.height = 1;
      tile.setImage(canvas);
    },
  });
  const layer = new TileLayer({source});
  const map = new Map({
    target: createMapDiv(128, 128),
    pixelRatio,
    layers: [layer],
    view: new View({center: [0, 0], zoom: 2}),
  });
  return {map, layer, requestedRatios};
}

function cachedUrls(layer) {
  const renderer = layer.getRenderer();
  const cache = renderer.getTileCache();
  return cache.getKeys()
    .map((key) => cache.get(key)?.src_)
    .filter((url) => typeof url === 'string' && url.startsWith(URL_PREFIX));
}

describe('MathGraph source-pinned pixel-ratio cache qualification', function () {
  it('positive control: a fresh ratio-two map produces ratio-two tiles', function () {
    const {map, layer} = newMap(2);
    try {
      map.renderSync();
      const urls = cachedUrls(layer);
      assert.isAbove(urls.length, 0, 'POSITIVE_CONTROL_NO_TILES');
      assert.isTrue(
        urls.every((url) => url.startsWith(URL_PREFIX + '2/')),
        'POSITIVE_CONTROL_WRONG_RATIO: ' + JSON.stringify(urls),
      );
    } finally {
      disposeMap(map);
    }
  });

  it('positive control: a repeated frame at the same ratio reuses its tiles', function () {
    const {map, layer} = newMap(1);
    try {
      map.renderSync();
      const cache = layer.getRenderer().getTileCache();
      const keys = cache.getKeys();
      assert.isAbove(keys.length, 0, 'REUSE_CONTROL_NO_TILES');
      const prior = keys.map((key) => cache.get(key));
      map.renderSync();
      assert.deepEqual(cache.getKeys().sort(), keys.slice().sort(), 'REUSE_CONTROL_KEYS_CHANGED');
      for (let i = 0; i < keys.length; ++i) {
        assert.strictEqual(cache.get(keys[i]), prior[i], 'REUSE_CONTROL_OBJECT_CHANGED');
      }
    } finally {
      disposeMap(map);
    }
  });

  it('Map.setPixelRatio(1 to 2) rebuilds ratio-dependent cached URLs', function () {
    const {map, layer, requestedRatios} = newMap(1);
    try {
      map.renderSync();
      const before = cachedUrls(layer);
      assert.isAbove(before.length, 0, 'TRANSITION_CONTROL_NO_TILES');
      assert.isTrue(
        before.every((url) => url.startsWith(URL_PREFIX + '1/')),
        'TRANSITION_CONTROL_BASELINE_WRONG_RATIO: ' + JSON.stringify(before),
      );
      const firstRequests = requestedRatios.length;
      map.setPixelRatio(2);
      assert.strictEqual(map.getPixelRatio(), 2, 'TRANSITION_CONTROL_RATIO_UNCHANGED');
      map.renderSync();
      const after = cachedUrls(layer);
      assert.isAbove(after.length, 0, 'TRANSITION_CONTROL_NO_REBUILT_TILES');
      assert.isTrue(
        after.every((url) => url.startsWith(URL_PREFIX + '2/')),
        'MATHGRAPH_RATIO_STALE_CACHE_EVIDENCE: ' + JSON.stringify({before, after, firstRequests, requestedRatios}),
      );
    } finally {
      disposeMap(map);
    }
  });
});
