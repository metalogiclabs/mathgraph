import {assert} from 'chai';
import Map from '../../../../../../src/ol/Map.js';
import View from '../../../../../../src/ol/View.js';
import TileLayer from '../../../../../../src/ol/layer/Tile.js';
import XYZ from '../../../../../../src/ol/source/XYZ.js';

// Adversarial application-defined tile load function. Its URL identity is
// unchanged, but the produced image depends on externally changing context.
// This is an allowed custom loader API path, not evidence of production use.
describe('MathGraph selective-cache counterexample: same URL, changed load effect', function () {
  it('does not equate URL equality with complete tile-behavior equivalence', function () {
    let contextRatio = 1;
    const observedLoads = [];
    const source = new XYZ({
      transition: 0,
      tileUrlFunction(coord) {
        return 'mathgraph-invariant-url://' + coord.join('/');
      },
      tileLoadFunction(tile) {
        observedLoads.push(contextRatio);
        const image = document.createElement('canvas');
        image.width = 1;
        image.height = 1;
        const ctx = image.getContext('2d');
        ctx.fillStyle = contextRatio === 1 ? '#ff0000' : '#0000ff';
        ctx.fillRect(0, 0, 1, 1);
        tile.setImage(image);
      },
    });
    const layer = new TileLayer({source});
    const map = new Map({
      target: createMapDiv(128, 128),
      pixelRatio: 1,
      layers: [layer],
      view: new View({center: [0, 0], zoom: 2}),
    });
    function tileColors() {
      const cache = layer.getRenderer().getTileCache();
      return cache.getKeys().map((key) => {
        const image = cache.get(key).getImage();
        const pixels = image.getContext('2d').getImageData(0, 0, 1, 1).data;
        return [pixels[0], pixels[1], pixels[2], pixels[3]];
      });
    }
    try {
      map.renderSync();
      const before = tileColors();
      assert.isAbove(before.length, 0);
      assert.isTrue(before.every((c) => c[0] === 255 && c[2] === 0),
        'RED_PRECONDITION_NOT_MET: ' + JSON.stringify(before));
      const originalLoadCount = observedLoads.length;
      contextRatio = 2;
      map.setPixelRatio(2);
      map.renderSync();
      const after = tileColors();
      const extraLoads = observedLoads.length - originalLoadCount;
      const evidence = {before, after, extraLoads, observedLoads};
      assert.isTrue(after.every((c) => c[0] === 0 && c[2] === 255),
        'MATHGRAPH_SAME_URL_LOADER_STATE_STALE: ' + JSON.stringify(evidence));
    } finally {
      disposeMap(map);
    }
  });
});
