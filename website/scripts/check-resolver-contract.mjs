import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const website = join(dirname(fileURLToPath(import.meta.url)), '..');
const repository = join(website, '..');
const request = {
  record_id: 'mg-l4yaml-source-check-20261010',
  source_commit: '62bf7077910e888a0bc8adfc8e08a5f500ff3ca3',
  external_suite_commit: 'da267a5c4782e7361e82889e76c0dc7df0e1e870',
  goal: 'finite_parser_acceptance',
};
const python = String.raw`
import json
from pathlib import Path
from mathgraph_check.public_receipts import resolve
record = json.loads(Path("website/public/evidence/mg-l4yaml-source-check-20261010/record.json").read_text())
query = json.loads(${JSON.stringify(JSON.stringify(request))})
print(json.dumps(resolve(record, query), sort_keys=True))
`;
const execution = spawnSync('python3', ['-c', python], { cwd: repository, encoding: 'utf8' });
assert.equal(execution.status, 0, execution.stderr || 'qualified resolver execution failed');
const response = JSON.parse(execution.stdout);
assert.equal(response.status, 'WARRANTED_BOUNDED');
assert.equal(response.record_id, request.record_id);
assert.equal(response.record_sha256, 'f0d092974d5d710fe9e17fb6759a894f2c28f2d3f5456439c071bd0a71c8d3cb');
assert.deepEqual(response.verified, { matched: 48, total: 48, extra_controls: 4 });
assert.equal(response.whole_language_validity, 'UNKNOWN');
assert.equal(response.truth_promotion, false);

const developerHtml = await readFile(join(website, 'dist/developers/index.html'), 'utf8');
const index = JSON.parse(await readFile(join(website, 'dist/records/index.json'), 'utf8'));
const catalogueEntry = index.records.find((candidate) => candidate.id === request.record_id && candidate.version === 1);
assert(catalogueEntry, 'catalogue omits the qualified resolver record');
assert.deepEqual(catalogueEntry.scope.supported_goals, [request.goal], 'catalogue goal exceeds the qualified resolver contract');
assert.equal(catalogueEntry.historic_status, response.status, 'catalogue historic status disagrees with the qualified resolver');
assert.equal(catalogueEntry.lifecycle, 'CURRENT', 'qualified resolver result may only be reused from a current catalogue entry');
assert(developerHtml.includes(request.goal), 'developer page omits the executable qualified goal');
for (const value of [response.status, response.record_id, response.record_sha256, response.whole_language_validity]) {
  assert(developerHtml.includes(value), `developer page disagrees with resolver value ${value}`);
}
console.log('RESOLVER_DOCUMENTATION_CONTRACT_GREEN actual=finite_parser_acceptance/WARRANTED_BOUNDED');
