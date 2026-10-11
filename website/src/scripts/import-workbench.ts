import qualifiedResult from '../../../conformance/import_v1/fixtures/result.json';

const MAX_BYTES = 65_536;
const RECORD_BYTES = 4_321;
const TRANSPORT_SHA256 = '7b59ee76a39995f35a0feb0f4d91a3c6ab1234393143480c4f3e361a79fee703';
const RECORD_PATH = '/records/mg-l4yaml-source-check-20261010/v1/';

type RecognizedRecord = {
  id: string;
  version: 1;
  schema: string;
  transport_sha256: string;
  content_sha256: string;
  source: typeof qualifiedResult.source;
  scope: typeof qualifiedResult.scope;
  evidence: typeof qualifiedResult.evidence;
  unknowns: typeof qualifiedResult.unknowns;
};
type Handoff = { status: 'UNKNOWN'; reason: 'NOT_SELECTED' | 'UNSUPPORTED_ROUTE' | 'UNRECOGNIZED_INPUT' }
  | { status: 'QUALIFIED_RECORD_HANDOFF'; historical_result: 'WARRANTED_BOUNDED'; goal: 'finite_parser_acceptance'; href: string };
export interface BrowserRecognition {
  schema: 'mathgraph.browser-recognition.v1';
  result_kind: 'READ_ONLY_PRESENTATION';
  processing_mode: 'LOCAL_BROWSER_EXACT_BYTE_RECOGNITION';
  authority: 'NONE';
  status: 'UNKNOWN' | 'EXACT_BYTES_RECOGNIZED';
  reason: string;
  proof_replay: 'NOT_PERFORMED';
  kernel_replay: 'NOT_PERFORMED';
  source_suite_replay: 'NOT_PERFORMED';
  freshness: 'UNKNOWN';
  current_applicability: 'UNKNOWN';
  authorization: 'READ_ONLY_NO_AUTOMATIC_AUTHORIZATION';
  record: RecognizedRecord | null;
  handoff: Handoff;
}

function unknown(reason: string): BrowserRecognition {
  return {
    schema: 'mathgraph.browser-recognition.v1', result_kind: 'READ_ONLY_PRESENTATION',
    processing_mode: 'LOCAL_BROWSER_EXACT_BYTE_RECOGNITION', authority: 'NONE',
    status: 'UNKNOWN', reason, proof_replay: 'NOT_PERFORMED', kernel_replay: 'NOT_PERFORMED',
    source_suite_replay: 'NOT_PERFORMED', freshness: 'UNKNOWN', current_applicability: 'UNKNOWN',
    authorization: 'READ_ONLY_NO_AUTOMATIC_AUTHORIZATION', record: null,
    handoff: { status: 'UNKNOWN', reason: 'UNRECOGNIZED_INPUT' },
  };
}

/** Local transport recognition only. No input JSON is parsed or executed. */
export async function recognizeLocalFile(input: unknown): Promise<BrowserRecognition> {
  if (!(input instanceof File)) return unknown('LOCAL_FILE_REQUIRED');
  if (input.size > MAX_BYTES) return unknown('INPUT_TOO_LARGE');
  if (input.size !== RECORD_BYTES) return unknown('UNSUPPORTED_BYTES');
  try {
    const bytes = await input.arrayBuffer();
    if (bytes.byteLength !== RECORD_BYTES) return unknown('UNSUPPORTED_BYTES');
    const digest = await crypto.subtle.digest('SHA-256', bytes);
    const hexadecimal = [...new Uint8Array(digest)].map(byte => byte.toString(16).padStart(2, '0')).join('');
    if (hexadecimal !== TRANSPORT_SHA256) return unknown('UNSUPPORTED_BYTES');
    // The exact immutable bytes are recognized before using committed known data.
    // This is deliberately not a second JSON parser or an independent importer.
    return {
      ...unknown('EXACT_TRANSPORT_MATCH'), status: 'EXACT_BYTES_RECOGNIZED',
      record: structuredClone({
        id: qualifiedResult.record_id, version: 1, schema: qualifiedResult.record_schema,
        transport_sha256: TRANSPORT_SHA256, content_sha256: qualifiedResult.content_sha256,
        source: qualifiedResult.source, scope: qualifiedResult.scope,
        evidence: qualifiedResult.evidence, unknowns: qualifiedResult.unknowns,
      }),
      handoff: { status: 'UNKNOWN', reason: 'NOT_SELECTED' },
    };
  } catch {
    return unknown('LOCAL_RECOGNITION_UNAVAILABLE');
  }
}

/** Select an existing record-bound reference. Never perform resolution in the browser. */
export function selectQualifiedHandoff(preview: BrowserRecognition, goal: string): BrowserRecognition {
  const result = structuredClone(preview);
  result.handoff = result.status !== 'EXACT_BYTES_RECOGNIZED' || !result.record
    ? { status: 'UNKNOWN', reason: 'UNRECOGNIZED_INPUT' }
    : goal !== 'finite_parser_acceptance'
      ? { status: 'UNKNOWN', reason: 'UNSUPPORTED_ROUTE' }
      : { status: 'QUALIFIED_RECORD_HANDOFF', historical_result: 'WARRANTED_BOUNDED', goal: 'finite_parser_acceptance', href: RECORD_PATH };
  return result;
}

const stageDescriptions = {
  import: 'Import — exact published bytes recognized locally. Integrity recognition supplies no authority.',
  interpret: 'Interpret — display the committed record fields at their declared finite scope. Statement fidelity and generalization remain UNKNOWN.',
  check: 'Check — Web Crypto SHA-256 matched the pinned transport digest. No proof, kernel, or source-suite execution occurred. This is not independent receipt or policy validation.',
  explore: 'Explore — inspect the same pinned record, source, finite scope, and evidence below. The permanent record link preserves this context; no equivalence or new graph relationship is inferred.',
  export: 'Export — download this read-only presentation with its exact record reference and UNKNOWNs. It is not mathgraph.import-result.v1 and is not an input to the Python importer.',
};
type Stage = keyof typeof stageDescriptions | 'resolve';

function attachWorkbench(root: HTMLElement): void {
  const input = root.querySelector<HTMLInputElement>('[data-import-file]')!;
  const status = root.querySelector<HTMLElement>('[data-import-status]')!;
  const context = root.querySelector<HTMLElement>('[data-import-context]')!;
  const output = root.querySelector<HTMLElement>('[data-import-stage-output]')!;
  const goal = root.querySelector<HTMLSelectElement>('[data-import-goal]')!;
  const download = root.querySelector<HTMLAnchorElement>('[data-import-download]')!;
  const handoffLink = root.querySelector<HTMLAnchorElement>('[data-import-handoff]')!;
  const controls = [...root.querySelectorAll<HTMLButtonElement>('[data-import-step]')];
  let current = unknown('LOCAL_FILE_REQUIRED');
  let generation = 0;
  let downloadUrl: string | undefined;

  function clearDownload(): void {
    if (downloadUrl) URL.revokeObjectURL(downloadUrl);
    downloadUrl = undefined;
    download.hidden = true;
    download.removeAttribute('href');
    download.removeAttribute('download');
  }
  function setText(selector: string, text: string): void {
    root.querySelector<HTMLElement>(selector)!.textContent = text;
  }
  function showStage(stage: Stage): void {
    clearDownload();
    root.dataset.stage = stage;
    controls.forEach(button => {
      if (button.dataset.importStep === stage) button.setAttribute('aria-current', 'step');
      else button.removeAttribute('aria-current');
    });
    handoffLink.hidden = true;
    if (stage === 'resolve') {
      current = selectQualifiedHandoff(current, goal.value);
      const handoff = current.handoff;
      output.textContent = handoff.status === 'UNKNOWN'
        ? `Resolve — UNKNOWN: ${handoff.reason}. No qualified record-bound route is selected.`
        : 'Resolve — qualified record handoff only. Historical result: WARRANTED_BOUNDED for finite_parser_acceptance at these exact pins. No browser resolution was performed.';
      handoffLink.hidden = handoff.status !== 'QUALIFIED_RECORD_HANDOFF';
    } else {
      output.textContent = stageDescriptions[stage];
    }
    if (stage === 'export') {
      downloadUrl = URL.createObjectURL(new Blob([`${JSON.stringify(current, null, 2)}\n`], { type: 'application/json' }));
      download.href = downloadUrl;
      download.download = 'mathgraph-browser-recognition.json';
      download.hidden = false;
    }
    status.textContent = `${current.status} — ${stage}. Authority NONE; current applicability and freshness UNKNOWN.`;
  }

  input.addEventListener('change', async () => {
    const request = ++generation;
    current = unknown('LOCAL_FILE_REQUIRED');
    clearDownload();
    root.dataset.stage = 'pending';
    context.hidden = true;
    handoffLink.hidden = true;
    controls.forEach(button => { button.disabled = true; button.removeAttribute('aria-current'); });
    goal.disabled = true;
    output.textContent = '';
    status.textContent = 'UNKNOWN — reading bounded local file.';
    const result = await recognizeLocalFile(input.files?.[0]);
    // A slow earlier read must never restore a stale recognized record.
    if (request !== generation) return;
    current = result;
    if (!result.record) {
      root.dataset.stage = 'unknown';
      status.textContent = `UNKNOWN — ${result.reason}. Unsupported input; choose the exact supported local record.json.`;
      return;
    }
    const record = result.record;
    setText('[data-import-identity]', `${record.id} · version ${record.version}\n${record.schema}\nTransport SHA-256: ${record.transport_sha256}\nContent SHA-256: ${record.content_sha256}`);
    setText('[data-import-source]', `${record.source.repo}@${record.source.commit}\n${record.source.external_suite_repo}@${record.source.external_suite_commit}\n${record.source.lean_toolchain}`);
    setText('[data-import-scope]', `${record.scope.identity}\n${record.scope.case_scope}\n${record.scope.matched_external_labels}/${record.scope.source_cases} source cases: ${record.scope.expected_accept} expected acceptances, ${record.scope.expected_reject} expected rejections; ${record.scope.extra_controls} extra controls; ${record.scope.total_lean_guards} Lean guards.\nNormalization: ${record.scope.normalization}`);
    setText('[data-import-evidence]', `${record.evidence.receipt_id}\nDeclared historical authority: ${record.evidence.authority}\nArchive SHA-256: ${record.evidence.archive_sha256}\nLean source SHA-256: ${record.evidence.lean_source_sha256}\nTest commit: ${record.evidence.test_commit}`);
    setText('[data-import-unknowns]', Object.entries(record.unknowns).map(([key, value]) => `${key}: ${value}`).join('\n'));
    context.hidden = false;
    controls.forEach(button => { button.disabled = false; });
    goal.disabled = false;
    showStage('import');
  });
  goal.addEventListener('change', () => {
    current = { ...current, handoff: { status: 'UNKNOWN', reason: 'NOT_SELECTED' } };
    showStage('check');
  });
  controls.forEach(button => button.addEventListener('click', () => showStage(button.dataset.importStep as Stage)));
  if (globalThis.crypto?.subtle) input.disabled = false;
  else status.textContent = 'UNKNOWN — local Web Crypto is unavailable. Use the documented offline import command.';
}

if (typeof document !== 'undefined') document.querySelectorAll<HTMLElement>('[data-import-workbench]').forEach(attachWorkbench);
