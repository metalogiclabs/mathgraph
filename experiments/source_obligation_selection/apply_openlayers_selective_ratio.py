#!/usr/bin/env python3
"""Exact-source experimental selective pixel-ratio cache invalidation.

This is an unmerged experimental patcher, NOT a general semantic proof. It
recognizes a narrow, source-owned URL factory with a stable function identity;
all other sources retain conservative invalidation.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()

def edit(path, edits):
    target = root / path
    data = target.read_text()
    for before, after in edits:
        n = data.count(before)
        if n != 1:
            raise SystemExit(f"SOURCE_PIN_MISMATCH: {path}: expected 1 occurrence, got {n}: {before[:100]!r}")
        data = data.replace(before, after)
    target.write_text(data)

edit("src/ol/source/UrlTile.js", [
    ("""    this.generateTileUrlFunction_ =
      this.tileUrlFunction === UrlTile.prototype.tileUrlFunction;
""",
     """    this.generateTileUrlFunction_ =
      this.tileUrlFunction === UrlTile.prototype.tileUrlFunction;

    // Only the built-in URL-template factory may provide this provenance.
    // A later custom URL-function assignment invalidates the evidence.
    this.generatedRatioInvariantTileUrlFunction_ = null;
"""),
    ("""  setTileUrlFunction(tileUrlFunction, key) {
    this.tileUrlFunction = tileUrlFunction;
""",
     """  setTileUrlFunction(tileUrlFunction, key) {
    this.generatedRatioInvariantTileUrlFunction_ = null;
    this.tileUrlFunction = tileUrlFunction;
"""),
    ("""        key,
      );
    } else {
      this.setKey(key);
    }
  }

  /**
   * @param {import("../tilecoord.js").TileCoord} tileCoord Tile coordinate.
""",
     """        key,
      );
      // createFromTemplates is independent of pixelRatio and projection.
      this.generatedRatioInvariantTileUrlFunction_ = this.tileUrlFunction;
    } else {
      this.setKey(key);
    }
  }

  /**
   * @param {import("../tilecoord.js").TileCoord} tileCoord Tile coordinate.
""")
])

edit("src/ol/source/Tile.js", [
    ("""  getTilePixelRatio(pixelRatio) {
    return this.tilePixelRatio_;
  }
""",
     """  getTilePixelRatio(pixelRatio) {
    return this.tilePixelRatio_;
  }

  /**
   * Whether the source warrants reusing cached tiles after a map pixel-ratio change.
   * The conservative default applies to unknown source implementations.
   * @return {boolean} Reuse is justified for the source.
   */
  canReuseCachedTilesAcrossPixelRatios(beforePixelRatio, afterPixelRatio) {
    return false;
  }
""")
])

edit("src/ol/source/TileImage.js", [
    ("""  getTileInternal(z, x, y, pixelRatio, projection, tileCache) {
    const key = this.getKey();
""",
     """  getTileInternal(z, x, y, pixelRatio, projection, tileCache) {
    const key = this.getKey();
"""),
    ("""  /**
   * @param {number} z Tile coordinate z.
   * @param {number} x Tile coordinate x.
   * @param {number} y Tile coordinate y.
   * @param {number} pixelRatio Pixel ratio.
   * @param {!import("../proj/Projection.js").default} projection Projection.
   * @param {import("../structs/LRUCache.js").default<import("../Tile.js").default>} [tileCache] Tile cache.
   * @return {!ImageTile} Tile.
   * @protected
   */
  getTileInternal(z, x, y, pixelRatio, projection, tileCache) {
""",
     """  /**
   * Conservatively authorize cross-ratio tile reuse only when the built-in
   * template-generated URL function and original tile construction remain
   * unchanged, and the source's tile-pixel ratio is equal in both contexts.
   * A custom URL function or subclass override is NOT assumed invariant.
   * @param {number} beforePixelRatio Earlier map pixel ratio.
   * @param {number} afterPixelRatio New map pixel ratio.
   * @return {boolean} Whether this bounded source relationship is established.
   * @override
   */
  canReuseCachedTilesAcrossPixelRatios(beforePixelRatio, afterPixelRatio) {
    return (
      typeof this.generatedRatioInvariantTileUrlFunction_ === 'function' &&
      this.tileUrlFunction === this.generatedRatioInvariantTileUrlFunction_ &&
      this.createTile_ === TileImage.prototype.createTile_ &&
      this.getTileInternal === TileImage.prototype.getTileInternal &&
      this.getTile === TileImage.prototype.getTile &&
      this.tileClass === ImageTile &&
      this.tileLoadFunction === defaultTileLoadFunction &&
      this.getTileCoordForTileUrlFunction ===
        TileImage.prototype.getTileCoordForTileUrlFunction &&
      this.getTileGridForProjection ===
        TileImage.prototype.getTileGridForProjection &&
      this.getTilePixelRatio === TileImage.prototype.getTilePixelRatio &&
      this.getTilePixelRatio(beforePixelRatio) ===
        this.getTilePixelRatio(afterPixelRatio)
    );
  }

  /**
   * @param {number} z Tile coordinate z.
   * @param {number} x Tile coordinate x.
   * @param {number} y Tile coordinate y.
   * @param {number} pixelRatio Pixel ratio.
   * @param {!import("../proj/Projection.js").default} projection Projection.
   * @param {import("../structs/LRUCache.js").default<import("../Tile.js").default>} [tileCache] Tile cache.
   * @return {!ImageTile} Tile.
   * @protected
   */
  getTileInternal(z, x, y, pixelRatio, projection, tileCache) {
""")
])

edit("src/ol/renderer/canvas/TileLayer.js", [
    ("""    const source = this.getLayer().getSource();
    if (!source) {
      return false;
    }
    const sourceRevision = source.getRevision();
""",
     """    const source = this.getLayer().getSource();
    if (!source) {
      return false;
    }
    // A pixel-ratio change can alter tiles while leaving the coordinate
    // cache key unchanged. Preserve cached work only with source provenance.
    if (
      this.renderedPixelRatio !== undefined &&
      this.renderedPixelRatio !== frameState.pixelRatio &&
      !source.canReuseCachedTilesAcrossPixelRatios(
        this.renderedPixelRatio,
        frameState.pixelRatio,
      )
    ) {
      this.tileCache_.clear();
      this.sourceTileCache_?.clear();
    }
    const sourceRevision = source.getRevision();
""")
])

print("SELECTIVE_SOURCE_PATCH_APPLIED_EXACTLY")
