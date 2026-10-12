import { sha256Hex } from './integrity';
import type { ObjectProjection } from './object-projections';
import { artifactUrl, moduleArtifactPaths } from './modules';

/** Link only known mirrored artifacts; never rewrite the canonical source pin. */
export function sourceHref(locator: string): string {
  return moduleArtifactPaths.some(path => path === locator) ? artifactUrl(locator) : locator;
}

/** Presentation locator only; the complete source-qualified ID remains the identity. */
export function objectSlug(value: string | ObjectProjection): string {
  if (typeof value !== 'string' && value.kind === 'SOURCE_DECLARATION' && /^object-[a-f0-9]{64}$/.test(value.source_id)) return value.source_id;
  return `object-${sha256Hex(typeof value === 'string' ? value : value.id)}`;
}

export function objectRoutes(objects: ObjectProjection[]) {
  const slugs = new Set<string>();
  return objects.map(object => {
    const slug = objectSlug(object);
    if (slugs.has(slug)) throw new Error('OBJECT_LOCATOR_COLLISION');
    slugs.add(slug);
    return { slug, object };
  });
}
