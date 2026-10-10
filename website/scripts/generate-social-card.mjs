import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';

import sharp from 'sharp';

const root = process.cwd();
const catalog = JSON.parse(await readFile(join(root, 'src/data/record-index.json'), 'utf8'));
const entry = catalog.records[0];
const record = JSON.parse(await readFile(join(root, 'public', new URL(entry.record_json_url).pathname), 'utf8'));
const output = join(root, 'public/social/records', `${entry.id}-${entry.version_slug}.png`);

function escapeXml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&apos;');
}

const digest = `${record.content_sha256.slice(0, 16)}…${record.content_sha256.slice(-8)}`;
const matched = record.axes.finite_executable.matched_external_labels;
const total = record.axes.finite_executable.source_cases;
const svg = `
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

const generated = await sharp(Buffer.from(svg)).png({ compressionLevel: 9, palette: false }).toBuffer();

if (process.argv.includes('--check')) {
  const committed = await readFile(output).catch(() => null);
  if (!committed || !committed.equals(generated)) {
    throw new Error('SOCIAL_CARD_OUT_OF_DATE');
  }
  console.log(`SOCIAL_CARD_GREEN ${entry.id} ${generated.length} bytes`);
} else {
  await mkdir(dirname(output), { recursive: true });
  await writeFile(output, generated);
  console.log(`SOCIAL_CARD_WRITTEN ${output} ${generated.length} bytes`);
}
