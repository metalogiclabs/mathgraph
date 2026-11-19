import {assert} from 'chai';
import Map from '../../../../../../src/ol/Map.js';
import TileState from '../../../../../../src/ol/TileState.js';
import View from '../../../../../../src/ol/View.js';
import TileLayer from '../../../../../../src/ol/layer/Tile.js';
import XYZ from '../../../../../../src/ol/source/XYZ.js';

function scene(ratio) {
  let map;
  let loaderCalls = 0;
  const source = new XYZ({
    transition: 0,
    // This factory-generated URL is invariant in ratio; the loader is not.
    url: 'data:image/gif;base64,R0lGODlhAQABAIAAAP///wAAACwAAAAAAQABAAACAkQBADs=',
    tileLoadFunction(tile) {
      ++loaderCalls;
      const canvas = document.createElement('canvas');
      canvas.width = 1;
      canvas.height = 1;
      const context = canvas.getContext('2d');
      context.fillStyle = map.getPixelRatio() === 1 ? 'rgb(50,0,0)' : 'rgb(200,0,0)';
      context.fillRect(0, 0, 1, 1);
      tile.setImage(canvas);
    },
  });
  const layer = new TileLayer({source});
  map = new Map({
    target: createMapDiv(128, 128),
    pixelRatio: ratio,
    layers: [layer],
    view: new View({center: [0, 0], zoom: 2}),
  });
  return {map, layer, source, getLoaderCalls: () => loaderCalls};
}

function snapshot(layer) {
  const cache = layer.getRenderer().getTileCache();
  const tiles = cache.getKeys().map((key) => ({key, tile: cache.get(key)}));
  assert.isAbove(tiles.length, 0, 'NO_CACHED_TILES_FOR_LOADER_CONTROL');
  for (const entry of tiles) {
    if (entry.tile.getState() === TileState.IDLE) {
      entry.tile.load();
    }
  }
  return tiles.map((entry) => {
    const image = entry.tile.getImage();
    assert.instanceOf(image, HTMLCanvasElement, 'CUSTOM_LOADER_NOT_EXECUTED');
    const channel = image.getContext('2d').getImageData(0, 0, 1, 1).data[0];
    return {key: entry.key, tile: entry.tile, channel};
  });
}

describe('MathGraph full-observation cache-reuse adversary', function () {
  it('fresh ratio-two custom loader yields channel 200', function () {
    const {map, layer} = scene(2);
    try {
      map.renderSync();
      assert.isTrue(snapshot(layer).every((x) => x.channel === 200));
    } finally {
      disposeMap(map);
    }
  });

  it('repeated same-ratio frame preserves cached tile objects', function () {
    const {map, layer} = scene(1);
    try {
      map.renderSync();
      const prior = snapshot(layer);
      map.renderSync();
      const later = snapshot(layer);
      assert.strictEqual(prior.length, later.length);
      for (const old of prior) {
        assert.strictEqual(later.find((x) => x.key === old.key)?.tile, old.tile);
        assert.strictEqual(old.channel, 50);
      }
    } finally {
      disposeMap(map);
    }
  });

  it('changing pixel ratio 1 to 2 must update the actual loaded image', function () {
    const {map, layer, getLoaderCalls} = scene(1);
    try {
      map.renderSync();
      const prior = snapshot(layer);
      assert.isTrue(prior.every((x) => x.channel === 50));
      const callsBefore = getLoaderCalls();
      map.setPixelRatio(2);
      map.renderSync();
      const later = snapshot(layer);
      assert.isAbove(later.length, 0);
      const observed = later.map((x) => x.channel);
      assert.isTrue(
        later.every((x) => x.channel === 200),
        'CUSTOM_LOADER_STALE_AFTER_RATIO: ' +
          JSON.stringify({before: prior.map((x) => x.channel), after: observed, callsBefore, callsAfter: getLoaderCalls()}),
      );
    } finally {
      disposeMap(map);
    }
  });
});
