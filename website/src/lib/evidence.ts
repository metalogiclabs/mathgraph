import frozenRecord from '../data/l4yaml-record.json';
import { canonicalContentDigest } from './integrity';

export const EXPECTED_RECORD_ID = 'mg-l4yaml-source-check-20261010';
export const EXPECTED_RECORD_CONTENT_SHA256 =
  'f0d092974d5d710fe9e17fb6759a894f2c28f2d3f5456439c071bd0a71c8d3cb';
export const EXPECTED_JPL_COMMIT = '62bf7077910e888a0bc8adfc8e08a5f500ff3ca3';
export const EXPECTED_SUITE_COMMIT = 'da267a5c4782e7361e82889e76c0dc7df0e1e870';

export type QualifiedRecord = typeof frozenRecord;

function requireBoundary(condition: boolean, code: string): asserts condition {
  if (!condition) {
    throw new Error(code);
  }
}

function recordDigest(record: Record<string, unknown>): string {
  return canonicalContentDigest(record);
}

export function validateQualifiedRecord(value: unknown): QualifiedRecord {
  requireBoundary(value !== null && typeof value === 'object' && !Array.isArray(value), 'PUBLIC_RECORD_NOT_AN_OBJECT');
  const record = value as Record<string, any>;
  requireBoundary(record.id === EXPECTED_RECORD_ID, 'RECORD_ID_CHANGED');
  requireBoundary(
    typeof record.content_sha256 === 'string' && record.content_sha256 === recordDigest(record),
    'PUBLIC_RECORD_CONTENT_HASH_INVALID',
  );
  requireBoundary(
    record.content_sha256 === EXPECTED_RECORD_CONTENT_SHA256,
    'PUBLIC_RECORD_NOT_TRUSTED_SNAPSHOT',
  );
  requireBoundary(record.source?.commit === EXPECTED_JPL_COMMIT, 'JPL_SOURCE_COMMIT_MISMATCH');
  requireBoundary(
    record.source?.external_suite_commit === EXPECTED_SUITE_COMMIT,
    'YAML_SUITE_COMMIT_MISMATCH',
  );
  requireBoundary(record.axes?.finite_executable?.matched_external_labels === 48, 'FINITE_CASE_COUNT_CHANGED');
  requireBoundary(record.axes?.finite_executable?.expected_accept === 31, 'EXPECTED_ACCEPT_COUNT_CHANGED');
  requireBoundary(record.axes?.finite_executable?.expected_reject === 17, 'EXPECTED_REJECT_COUNT_CHANGED');
  requireBoundary(record.axes?.finite_executable?.extra_controls === 4, 'EXTRA_CONTROL_COUNT_CHANGED');
  requireBoundary(record.axes?.finite_executable?.total_lean_guards === 52, 'LEAN_GUARD_COUNT_CHANGED');
  requireBoundary(
    record.axes?.formal_verification?.universal_yaml_correctness === 'UNKNOWN' &&
      record.axes?.statement_fidelity?.status === 'UNKNOWN' &&
      record.axes?.generalization?.status === 'UNKNOWN',
    'UNKNOWN_BOUNDARY_CHANGED',
  );
  requireBoundary(
    record.axes?.current_requalification?.status === 'NOT_CHECKED_AFTER_SNAPSHOT',
    'REQUALIFICATION_STATUS_CHANGED',
  );
  requireBoundary(
    record.axes?.global_truth_promotion === false &&
      record.admission?.mathematical_theorem_badge_issued === false &&
      record.admission?.source_fidelity_certified === false,
    'ILLEGAL_AUTHORITY_PROMOTION',
  );
  return record as QualifiedRecord;
}

export function loadQualifiedRecord(): QualifiedRecord {
  return validateQualifiedRecord(frozenRecord);
}
