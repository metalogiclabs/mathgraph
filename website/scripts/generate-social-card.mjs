import { createHash } from 'node:crypto';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';

import sharp from 'sharp';

const root = process.cwd();
const catalog = JSON.parse(await readFile(join(root, 'src/data/record-index.json'), 'utf8'));
const expectedPngSha256 = {
  'mg-l4yaml-source-check-20261010': '7269e84d1a81dbe671867bfc3f6effdde233c5ddffabfad35e665d1a9508844c',
  'mg-living-warrant-openai-jpl-20261010': '82f8bd0fdc14df7d0f4e12fe6ba3e9aea7944d36ffc13a3634e7b147440ee5f1',
};

function sha256(bytes) {
  return createHash('sha256').update(bytes).digest('hex');
}

function escapeXml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&apos;');
}

function sourceCheckSvg(entry, record) {
  const digest = `${record.content_sha256.slice(0, 16)}…${record.content_sha256.slice(-8)}`;
  const matched = record.axes.finite_executable.matched_external_labels;
  const total = record.axes.finite_executable.source_cases;
  return `
<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
  <rect width="1200" height="630" fill="#f8f7f3"/>
  <rect x="0" y="0" width="12" height="630" fill="#3d5fd2"/>
  <text x="72" y="86" font-family="Arial, Helvetica, sans-serif" font-size="28" font-weight="700" fill="#10131a">MathGraph<tspan fill="#3d5fd2">.</tspan></text>
  <text x="72" y="164" font-family="Arial, Helvetica, sans-serif" font-size="19" font-weight="700" letter-spacing="2.4" fill="#515a6b">WARRANTED · BOUNDED</text>
  <text x="72" y="252" font-family="Georgia, Times, serif" font-size="58" fill="#10131a">Source-pinned evidence.</text>
  <text x="72" y="332" font-family="Georgia, Times, serif" font-size="58" fill="#10131a">Edges included.</text>
  <line x1="72" y1="392" x2="1128" y2="392" stroke="#bec4c8"/>
  <text x="72" y="465" font-family="Georgia, Times, serif" font-size="52" fill="#10131a">${matched}/${total}</text>
  <text x="270" y="458" font-family="Arial, Helvetica, sans-serif" font-size="21" font-weight="700" fill="#10131a">decoded cases matched source labels</text>
  <text x="270" y="490" font-family="Arial, Helvetica, sans-serif" font-size="18" fill="#75520e">UNKNOWN · whole-language correctness</text>
  <text x="72" y="560" font-family="monospace" font-size="17" fill="#515a6b">${escapeXml(entry.id)}</text>
  <text x="72" y="590" font-family="monospace" font-size="16" fill="#727b8d">sha256:${escapeXml(digest)}</text>
</svg>`;
}

function resolveSnapshotSvg(entry) {
  const digest = `${entry.record_content_sha256.slice(0, 16)}…${entry.record_content_sha256.slice(-8)}`;
  return `
<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
  <rect width="1200" height="630" fill="#f8f7f3"/>
  <rect x="0" y="0" width="12" height="630" fill="#3d5fd2"/>
  <text x="72" y="82" font-family="Arial, Helvetica, sans-serif" font-size="28" font-weight="700" fill="#10131a">MathGraph<tspan fill="#3d5fd2">.</tspan> Resolve</text>
  <text x="72" y="142" font-family="Arial, Helvetica, sans-serif" font-size="18" font-weight="700" letter-spacing="2" fill="#515a6b">HISTORIC SNAPSHOT · SCOPED_MIXED</text>
  <text x="72" y="222" font-family="Georgia, Times, serif" font-size="48" fill="#10131a">Evidence changed.</text>
  <text x="72" y="282" font-family="Georgia, Times, serif" font-size="48" fill="#10131a">Truth was not inferred.</text>
  <line x1="72" y1="330" x2="1128" y2="330" stroke="#bec4c8"/>
  <text x="72" y="388" font-family="Arial, Helvetica, sans-serif" font-size="22" fill="#10131a">3 stale documentary paths</text>
  <text x="72" y="430" font-family="Arial, Helvetica, sans-serif" font-size="22" fill="#75520e">3 UNKNOWN propositions</text>
  <text x="72" y="472" font-family="Arial, Helvetica, sans-serif" font-size="22" fill="#10131a">1 exactly scoped WARRANTED_BOUNDED observation retained</text>
  <text x="72" y="522" font-family="Arial, Helvetica, sans-serif" font-size="17" font-weight="700" fill="#75520e">CURRENT APPLICABILITY · UNKNOWN</text>
  <text x="1128" y="522" text-anchor="end" font-family="Arial, Helvetica, sans-serif" font-size="17" fill="#515a6b">Presentation only · authority NONE</text>
  <text x="72" y="568" font-family="monospace" font-size="17" fill="#515a6b">${escapeXml(entry.id)}</text>
  <text x="72" y="598" font-family="monospace" font-size="16" fill="#727b8d">sha256:${escapeXml(digest)}</text>
</svg>`;
}

const cards = await Promise.all(catalog.records.map(async (entry) => {
  const record = JSON.parse(await readFile(join(root, 'public', new URL(entry.record_json_url).pathname), 'utf8'));
  const svg = entry.record_kind === 'SOURCE_CHECK' ? sourceCheckSvg(entry, record) : resolveSnapshotSvg(entry);
  return {
    entry,
    svg,
    output: join(root, 'public/social/records', `${entry.id}-${entry.version_slug}.png`),
    sourceOutput: join(root, 'public/social/records', `${entry.id}-${entry.version_slug}.source.svg`),
  };
}));

if (process.argv.includes('--check')) {
  for (const card of cards) {
    const [committedSource, committedPng] = await Promise.all([
      readFile(card.sourceOutput, 'utf8').catch(() => null),
      readFile(card.output).catch(() => null),
    ]);
    if (committedSource !== card.svg) throw new Error(`SOCIAL_CARD_SOURCE_OUT_OF_DATE:${card.entry.id}`);
    const expected = expectedPngSha256[card.entry.id];
    if (!committedPng || sha256(committedPng) !== expected) throw new Error(`SOCIAL_CARD_PNG_DIGEST_MISMATCH:${card.entry.id}`);
    const metadata = await sharp(committedPng).metadata();
    if (metadata.width !== 1200 || metadata.height !== 630 || metadata.format !== 'png') {
      throw new Error(`SOCIAL_CARD_PNG_FORMAT_INVALID:${card.entry.id}`);
    }
    console.log(`SOCIAL_CARD_GREEN ${card.entry.id} ${committedPng.length} bytes sha256=${expected}`);
  }
} else {
  for (const card of cards) {
    const generated = await sharp(Buffer.from(card.svg)).png({ compressionLevel: 9, palette: false }).toBuffer();
    await mkdir(dirname(card.output), { recursive: true });
    await Promise.all([writeFile(card.sourceOutput, card.svg), writeFile(card.output, generated)]);
    console.log(`SOCIAL_CARD_WRITTEN ${card.output} ${generated.length} bytes sha256=${sha256(generated)}`);
  }
}
