import type { APIRoute } from 'astro';
import { artifactBytes, moduleArtifactPaths } from '../../lib/modules';

export const prerender = true;
export const getStaticPaths = () => moduleArtifactPaths.map((path) => ({ params: { path } }));
export const GET: APIRoute = async ({ params }) => {
  const path = params.path!;
  return new Response(new Uint8Array(await artifactBytes(path)), {
    headers: { 'content-type': path.endsWith('.json') ? 'application/json; charset=utf-8' : 'text/plain; charset=utf-8' },
  });
};
