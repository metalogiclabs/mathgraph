import type { APIRoute } from 'astro';

import { loadPublishedRecords } from '../lib/catalog';

export const prerender = true;

function escapeXml(value: string): string {
  return value.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&apos;');
}

export const GET: APIRoute = async () => {
  const packages = await loadPublishedRecords();
  const routes = [
    '/',
    '/check/',
    '/records/',
    '/protocol/',
    '/protocol/profiles/lean/',
    '/developers/',
    '/agents/',
    ...packages.flatMap(({ entry }) => [new URL(entry.latest_page_url).pathname, new URL(entry.record_page_url).pathname]),
  ];
  const uniqueRoutes = [...new Set(routes)];
  const body = `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${uniqueRoutes
    .map((route) => `  <url><loc>${escapeXml(new URL(route, 'https://mathgraph.org').href)}</loc></url>`)
    .join('\n')}\n</urlset>\n`;
  return new Response(body, {
    headers: { 'content-type': 'application/xml; charset=utf-8' },
  });
};
