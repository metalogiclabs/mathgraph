import {createHash} from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {mkdir, writeFile} from 'node:fs/promises';
import {resolve, join} from 'node:path';

export const AXIOM_CASES = ['kernel', 'permitted', 'native', 'private'];
const id = 'capstone-axiom-admission-v1';
const sourcePath = 'L4YAML/CapstoneAttr.lean';
const acceptedSources = new Set([
  '40db6218a9eb955739604a3540faaf9a9e70bfde09fee6ad91b83b43139a602d',
  '8ec732423ed9a7db9997de9aeb18d3661154ab14fc396301bf596cd3bf7fbc59',
]);
const positive = `import L4YAML.CapstoneAttr

@[capstone] theorem kernelControl : True := True.intro
@[capstone] theorem permittedControl (p q : Prop) (h : p ↔ q) : p = q := propext h
@[capstone] theorem nativeControl : (List.range 40).length = 40 := by native_decide
#assert_capstone_axioms
`;
const negative = `import L4YAML.CapstoneAttr

private axiom privateAssumption : False
@[capstone] theorem privateClaim : False := privateAssumption
#assert_capstone_axioms
`;
const digest = bytes => createHash('sha256').update(bytes).digest('hex');

export async function runAxiomAdmission({repo, base, head, out, lean, timeout}) {
  out = resolve(out);
  await mkdir(out);
  const method = {id, source_path: sourcePath, source_sha256: [...acceptedSources],
    positive_sha256: digest(positive), negative_sha256: digest(negative)};
  const subjects = {base: {revision: base}, head: {revision: head}};
  const executable = lean.includes('/') ? resolve(lean) : lean;
  const probe = spawnSync(executable, ['--version'], {encoding: 'utf8', timeout: timeout * 1000});
  const result = {method, subjects, runtime: {lean: probe.stdout?.trim() ?? null},
    status: 'UNKNOWN', reason: null, cost: {model_calls: 0}};

  async function replay(side) {
    const raw = spawnSync('git', ['-C', repo, 'show', subjects[side].revision + ':' + sourcePath],
      {timeout: 30000, maxBuffer: 1024 * 1024});
    if (raw.status !== 0 || raw.error) return {complete: false, reason: 'CAPSTONE_SOURCE_UNAVAILABLE'};
    const sha = digest(raw.stdout);
    subjects[side].source_sha256 = sha;
    if (!acceptedSources.has(sha)) return {complete: false, reason: 'CAPSTONE_SOURCE_UNSUPPORTED'};
    const cwd = join(out, side);
    await mkdir(join(cwd, 'L4YAML'), {recursive: true});
    await writeFile(join(cwd, sourcePath), raw.stdout);
    await writeFile(join(cwd, 'Positive.lean'), positive);
    await writeFile(join(cwd, 'Private.lean'), negative);
    const deadline = Date.now() + timeout * 1000;
    async function run(label, args) {
      const execution = spawnSync(executable, args, {
        cwd, env: {...process.env, LEAN_PATH: cwd}, encoding: 'utf8',
        timeout: Math.max(1, deadline - Date.now()), maxBuffer: 1024 * 1024,
      });
      const observation = {exit_code: execution.status, signal: execution.signal,
        error: execution.error?.code ?? null, stdout: execution.stdout ?? '', stderr: execution.stderr ?? ''};
      await writeFile(join(cwd, label + '.json'), JSON.stringify(observation, null, 2) + '\n');
      return observation;
    }
    const build = await run('build', ['-o', 'L4YAML/CapstoneAttr.olean', sourcePath]);
    if (build.exit_code !== 0 || build.error) return {complete: false, reason: 'CAPSTONE_BUILD_UNAVAILABLE'};
    const pass = await run('positive', ['Positive.lean']);
    const reject = await run('private', ['Private.lean']);
    const reports = pass.stdout.split(/\r?\n/);
    const accepted = reject.exit_code === 0 && reject.stdout.split(/\r?\n/).includes('privateClaim: native');
    const errors = (reject.stdout + reject.stderr).split(/\r?\n/).filter(line => line.includes('error:'));
    const refused = reject.exit_code === 1 && errors.length === 1 &&
      /^Private\.lean:5:0: error: capstone privateClaim depends on non-allowed axioms: \[_private\.Private\.\d+\.privateAssumption\]$/.test(errors[0]);
    if (pass.error || pass.exit_code !== 0 || reject.error || (!accepted && !refused))
      return {complete: false, reason: 'CAPSTONE_EXECUTION_EVIDENCE_UNAVAILABLE'};
    const observations = [
      {id: 'kernel', passed: reports.includes('kernelControl: pure')},
      {id: 'permitted', passed: reports.includes('permittedControl: pure')},
      {id: 'native', passed: reports.includes('nativeControl: native')},
      {id: 'private', passed: refused},
    ];
    return {complete: true, observations, mismatches: observations.filter(check => !check.passed)};
  }

  if (probe.status !== 0 || probe.error || !/^Lean \(version 4\.35\.0, /.test(probe.stdout ?? '')) {
    result.reason = 'LEAN_4_35_0_UNAVAILABLE';
  } else {
    result.base = await replay('base');
    result.head = await replay('head');
    if (!result.base.complete || !result.head.complete) {
      result.reason = [result.base.reason, result.head.reason].filter(Boolean).join(', ');
    } else {
      result.status = result.head.mismatches.length ? 'OBSERVED_MISMATCH' : 'OBSERVED_AGREEMENT';
    }
  }
  await writeFile(join(out, 'result.json'), JSON.stringify(result, null, 2) + '\n');
  return {result};
}
