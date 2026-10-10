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
      basis: 'CLIENT_FETCH_TIME',
      max_age_seconds: 300,
      meaning: 'generated_at is publication time; set fetched_at when received and re-fetch before max_age_seconds elapse.',
      records_are_immutable: true,
    },
    records: packages.map(({ entry }) => entry),
  };
  return new Response(`${JSON.stringify(index, null, 2)}\n`, {
    headers: { 'content-type': 'application/json; charset=utf-8' },
  });
};
