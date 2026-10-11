import { sha256Hex } from './integrity';
import type { ObjectProjection } from './object-projections';
import { artifactUrl, moduleArtifactPaths } from './modules';

/** Link only known mirrored artifacts; never rewrite the canonical source pin. */
export function sourceHref(locator: string): string {
  return moduleArtifactPaths.some(path => path === locator) ? artifactUrl(locator) : locator;
}

/** Presentation locator only; the complete source-qualified ID remains the identity. */
export function objectSlug(id: string): string {
  return `object-${sha256Hex(id)}`;
}

export function objectRoutes(objects: ObjectProjection[]) {
  const slugs = new Set<string>();
  return objects.map(object => {
    const slug = objectSlug(object.id);
    if (slugs.has(slug)) throw new Error('OBJECT_LOCATOR_COLLISION');
    slugs.add(slug);
    return { slug, object };
  });
}
