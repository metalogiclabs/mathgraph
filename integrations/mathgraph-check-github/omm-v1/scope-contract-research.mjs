// Offline OMM research-only scope comparison. Neither the scope labels nor the
// expected digest pins may be supplied by the candidate/model. An independent
// controller must authenticate the original requirement owner, obtain the
// actual elaborated Lean type, attest the ID-to-type mapping, and hold both
// expected digests. The inputs here are annotations, not native type receipts.
// This module does none of those upstream tasks and is NOT wired to the App.
import {createHash} from 'node:crypto';

const SHA40 = /^[a-f0-9]{40}$/;
const SHA256 = /^[a-f0-9]{64}$/;
const REPOSITORY = /^[a-zA-Z0-9_.-]+\/[a-zA-Z0-9_.-]+$/;
const REQUIREMENT_ID = /^[a-z0-9][a-z0-9-]{0,63}$/;
const DECLARATION = /^[A-Za-z_][A-Za-z0-9_'.]{0,150}$/;
const PATH_SEGMENT = /^[A-Za-z0-9_.-]+$/;

function unknown(reason) {
  return {
    schema: 'mathgraph.omm.declared-scope-assessment.research.v1',
    status: 'UNKNOWN', declared_scope: 'UNKNOWN',
    uncovered_requirement_ids: [], intent_fidelity: 'UNKNOWN',
    proof_status: 'UNKNOWN', reason,
  };
}

function pinnedJson(bytes, expected) {
  if (typeof bytes !== 'string' || bytes.length > 100_000 ||
      !SHA256.test(expected ?? '') ||
      createHash('sha256').update(bytes).digest('hex') !== expected) return null;
  try { return JSON.parse(bytes); } catch { return null; }
}

function validSource(value) {
  const path = value?.source_path;
  return value && REPOSITORY.test(value.repository ?? '') &&
    SHA40.test(value.head_sha ?? '') && SHA256.test(value.source_sha256 ?? '') &&
    typeof path === 'string' && path.length <= 240 && path.split('/').every(
      segment => segment !== '.' && segment !== '..' && PATH_SEGMENT.test(segment));
}

function sameSource(a, b) {
  return a.repository === b.repository && a.head_sha === b.head_sha &&
    a.source_sha256 === b.source_sha256 && a.source_path === b.source_path;
}

function validIds(ids, allowEmpty = false) {
  return Array.isArray(ids) && ids.length <= 32 &&
    (allowEmpty || ids.length > 0) &&
    ids.every(id => typeof id === 'string' && REQUIREMENT_ID.test(id)) &&
    new Set(ids).size === ids.length;
}

/**
 * Report only a syntactic difference between two independently pinned,
 * externally attested ID sets. A no-gap result is never human-intent approval.
 */
export function assessDeclaredScope({currentSource, contractBytes,
  expectedContractSha256, typeAnnotationBytes, expectedTypeAnnotationSha256} = {}) {
  if (!validSource(currentSource)) return unknown('SOURCE_IDENTITY_NOT_AUTHENTICATED');

  const contract = pinnedJson(contractBytes, expectedContractSha256);
  if (!contract || contract.schema !== 'mathgraph.omm.declared-scope-contract.research.v1' ||
      !validSource(contract) || !sameSource(contract, currentSource) ||
      !validIds(contract.requirement_ids))
    return unknown('REQUIREMENT_CONTRACT_MISSING_OR_SOURCE_CHANGED');

  const receipt = pinnedJson(typeAnnotationBytes, expectedTypeAnnotationSha256);
  if (!receipt || receipt.schema !== 'mathgraph.omm.type-scope-annotation.research.v1' ||
      !validSource(receipt) || !sameSource(receipt, currentSource) ||
      !DECLARATION.test(receipt.declaration ?? '') ||
      !SHA256.test(receipt.type_sha256 ?? '') ||
      !validIds(receipt.attested_scope_ids, true) ||
      receipt.attested_scope_ids.some(id => !contract.requirement_ids.includes(id)))
    return unknown('TYPE_SCOPE_ANNOTATION_MISSING_OR_SOURCE_CHANGED');

  const covered = new Set(receipt.attested_scope_ids);
  const uncovered = contract.requirement_ids.filter(id => !covered.has(id));
  return {
    schema: 'mathgraph.omm.declared-scope-assessment.research.v1',
    status: 'PINNED_SCOPE_ANNOTATIONS_COMPARED',
    declared_scope: uncovered.length ? 'DECLARED_GAP' : 'NO_DECLARED_GAP',
    uncovered_requirement_ids: uncovered,
    intent_fidelity: 'UNKNOWN', proof_status: 'UNKNOWN',
    contract_sha256: expectedContractSha256,
    type_annotation_sha256: expectedTypeAnnotationSha256,
    source_sha256: currentSource.source_sha256,
    type_sha256: receipt.type_sha256,
    reason: 'OPERATOR_LABELS_ONLY_NOT_NATIVE_TYPE_OR_SEMANTIC_WARRANT',
  };
}
