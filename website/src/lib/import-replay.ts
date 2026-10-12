export const importImplementationCommit = '1204a1d267b6217c45c9b17f093cc3587450cf78';
export const importRepositoryUrl = 'https://github.com/metalogiclabs/mathgraph';
export const importPolicySha256 = '944231afaf9d89e6f7dc77d9efbe80dcbd3fc76f8e8f260b32637a0f261faf65';

const importSourceRoot = importRepositoryUrl + '/blob/' + importImplementationCommit;

export const importConsumerSourceUrl = importSourceRoot + '/conformance/import_v1/consumer.py';
export const importPolicySourceUrl = importSourceRoot + '/conformance/import_v1/fixtures/trust-policy.json';

export const importCheckoutCommand = [
  'git clone ' + importRepositoryUrl + '.git mathgraph-import-v1',
  'cd mathgraph-import-v1',
  'git checkout --detach ' + importImplementationCommit,
].join('\n');

export const importReplayCommand = [
  'python3 -I -S scripts/mathgraph_import_v1.py',
  '  --record conformance/import_v1/fixtures/record.json',
  '  --policy conformance/import_v1/fixtures/trust-policy.json',
  '  --policy-sha256 ' + importPolicySha256,
  '  --goal finite_parser_acceptance',
].join(' \\\n');

export const importCheckoutReplayCommand = importCheckoutCommand + '\n\n' + importReplayCommand;
