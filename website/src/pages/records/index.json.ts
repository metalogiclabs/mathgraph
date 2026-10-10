import type { APIRoute } from 'astro';

import catalogSource from '../../data/record-index.json';
import { loadPublishedRecords } from '../../lib/catalog';

export const prerender = true;

export const GET: APIRoute = async () => {
  const packages = await loadPublishedRecords();
  const index = {
    ...catalogSource,
    generated_at: new Date().toISOString(),
    lifecycle_freshness: {
      max_age_seconds: 300,
      meaning: 'Lifecycle state is current only as of the fetched index response.',
      records_are_immutable: true,
    },
    records: packages.map(({ entry }) => entry),
  };
  return new Response(`${JSON.stringify(index, null, 2)}\n`, {
    headers: { 'content-type': 'application/json; charset=utf-8' },
  });
};
