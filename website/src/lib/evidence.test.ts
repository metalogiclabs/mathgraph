import { createHash } from 'node:crypto';

import { describe, expect, test } from 'vitest';

import {
  EXPECTED_RECORD_CONTENT_SHA256,
  loadQualifiedRecord,
  validateQualifiedRecord,
} from './evidence';

const RECORD_ID = 'mg-l4yaml-source-check-20261010';
const JPL_COMMIT = '62bf7077910e888a0bc8adfc8e08a5f500ff3ca3';
const SUITE_COMMIT = 'da267a5c4782e7361e82889e76c0dc7df0e1e870';

function canonicalJson(value: unknown): string {
  if (value === null || typeof value !== 'object') {
    return JSON.stringify(value);
  }
  if (Array.isArray(value)) {
    return `[${value.map(canonicalJson).join(',')}]`;
  }
  const entries = Object.entries(value as Record<string, unknown>)
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([key, child]) => `${JSON.stringify(key)}:${canonicalJson(child)}`);
  return `{${entries.join(',')}}`;
}

function contentDigest(record: Record<string, unknown>): string {
  const unsigned = structuredClone(record);
  delete unsigned.content_sha256;
  return createHash('sha256').update(canonicalJson(unsigned)).digest('hex');
}

describe('qualified L4YAML publication boundary', () => {
  test('loads only the exact qualified identity and source pins', () => {
    const record = loadQualifiedRecord();

    expect(record.id).toBe(RECORD_ID);
    expect(record.content_sha256).toBe(EXPECTED_RECORD_CONTENT_SHA256);
    expect(record.content_sha256).toBe(
      'f0d092974d5d710fe9e17fb6759a894f2c28f2d3f5456439c071bd0a71c8d3cb',
    );
    expect(record.source.commit).toBe(JPL_COMMIT);
    expect(record.source.external_suite_commit).toBe(SUITE_COMMIT);
  });

  test('retains the bounded observations and visible unknowns', () => {
    const record = loadQualifiedRecord();
    const executable = record.axes.finite_executable;

    expect(executable.matched_external_labels).toBe(48);
    expect(executable.expected_accept).toBe(31);
    expect(executable.expected_reject).toBe(17);
    expect(executable.extra_controls).toBe(4);
    expect(executable.total_lean_guards).toBe(52);
    expect(record.axes.formal_verification.universal_yaml_correctness).toBe('UNKNOWN');
    expect(record.axes.statement_fidelity.status).toBe('UNKNOWN');
    expect(record.axes.generalization.status).toBe('UNKNOWN');
    expect(record.axes.current_requalification.status).toBe('NOT_CHECKED_AFTER_SNAPSHOT');
    expect(record.axes.global_truth_promotion).toBe(false);
    expect(record.admission.mathematical_theorem_badge_issued).toBe(false);
  });

  test('rejects a forged scope even when its self-hash is recomputed', () => {
    const forged = structuredClone(loadQualifiedRecord()) as unknown as Record<string, unknown>;
    const axes = forged.axes as Record<string, unknown>;
    const executable = axes.finite_executable as Record<string, unknown>;
    executable.matched_external_labels = 4_800;
    forged.content_sha256 = contentDigest(forged);

    expect(() => validateQualifiedRecord(forged)).toThrow(
      'PUBLIC_RECORD_NOT_TRUSTED_SNAPSHOT',
    );
  });
});
