import {assert} from 'chai';
import Map from '../../../../../../src/ol/Map.js';
import View from '../../../../../../src/ol/View.js';
import TileLayer from '../../../../../../src/ol/layer/Tile.js';
import XYZ from '../../../../../../src/ol/source/XYZ.js';

function makeMap(source) {
  const layer = new TileLayer({source});
  const map = new Map({
    target: createMapDiv(128, 128),
    pixelRatio: 1,
    layers: [layer],
    view: new View({center: [0, 0], zoom: 2}),
  });
  return {map, layer};
}
function getTiles(layer) {
  const cache = layer.getRenderer().getTileCache();
  return cache.getKeys().map((key) => ({key, tile: cache.get(key)}));
}
const inertLoader = (tile) => {
  const canvas = document.createElement('canvas');
  canvas.width = 1;
  canvas.height = 1;
  tile.setImage(canvas);
};

describe('MathGraph source-provenanced ratio cache experiment', function () {
  it('template-owned URL identity retains tile objects across 1 to 2', function () {
    const source = new XYZ({
      url: 'mathgraph-template/{z}/{x}/{y}',
      transition: 0,
      tileLoadFunction: inertLoader,
    });
    const {map, layer} = makeMap(source);
    try {
      assert.isTrue(source.canReuseCachedTilesAcrossPixelRatios(1, 2));
      map.renderSync();
      const before = getTiles(layer);
      assert.isAbove(before.length, 0);
      map.setPixelRatio(2);
      map.renderSync();
      const after = getTiles(layer);
      assert.deepEqual(after.map((x) => x.key).sort(), before.map((x) => x.key).sort());
      for (const old of before) {
        const current = after.find((x) => x.key === old.key);
        assert.strictEqual(current.tile, old.tile, 'TEMPLATE_SHOULD_REUSE_ALL_TILES');
      }
      console.log('MATHGRAPH_TEMPLATE_SELECTIVE_REUSE ' + JSON.stringify({
        before: before.length, after: after.length, all_objects_retained: true,
      }));
    } finally {
      disposeMap(map);
    }
  });

  it('unknown custom URL callback is not automatically treated as invariant', function () {
    const source = new XYZ({
      tileUrlFunction(coord, ratio) {
        return 'mathgraph-custom/' + ratio + '/' + coord.join('/');
      },
      tileLoadFunction: inertLoader,
      transition: 0,
    });
    const {map, layer} = makeMap(source);
    try {
      assert.isFalse(source.canReuseCachedTilesAcrossPixelRatios(1, 2));
      map.renderSync();
      const before = getTiles(layer);
      assert.isAbove(before.length, 0);
      map.setPixelRatio(2);
      map.renderSync();
      const after = getTiles(layer);
      assert.isTrue(after.every((x) => x.tile.src_.includes('mathgraph-custom/2/')),
        'CUSTOM_FUNCTION_MUST_REBUILD_FOR_NEW_RATIO');
      assert.isTrue(before.some((old) => after.find((x) => x.key === old.key)?.tile !== old.tile));
    } finally {
      disposeMap(map);
    }
  });

  it('changing generated URL function invalidates its ratio-independence provenance', function () {
    const source = new XYZ({url: 'mathgraph-template/{z}/{x}/{y}'});
    assert.isTrue(source.canReuseCachedTilesAcrossPixelRatios(1, 2));
    source.setTileUrlFunction((coord, ratio) => 'custom/' + ratio + '/' + coord.join('/'));
    assert.isFalse(source.canReuseCachedTilesAcrossPixelRatios(1, 2));
    source.setUrl('mathgraph-other/{z}/{x}/{y}');
    assert.isTrue(source.canReuseCachedTilesAcrossPixelRatios(1, 2));
    source.tileUrlFunction = (coord, ratio) => 'direct-custom/' + ratio + '/' + coord.join('/');
    assert.isFalse(source.canReuseCachedTilesAcrossPixelRatios(1, 2));
  });

  it('a custom tile creation override cannot borrow template invariance', function () {
    const source = new XYZ({url: 'mathgraph-template/{z}/{x}/{y}'});
    assert.isTrue(source.canReuseCachedTilesAcrossPixelRatios(1, 2));
    const original = source.createTile_;
    source.createTile_ = function (...args) { return original.apply(this, args); };
    assert.isFalse(source.canReuseCachedTilesAcrossPixelRatios(1, 2));
  });
});
