import { readFile } from 'node:fs/promises';
import { describe, expect, test } from 'vitest';
import sourceRecord from '../data/l4yaml-record.json';
import resolveRecord from '../data/resolve-record.json';
import catalog from '../data/record-index.json';
import contract from '../../../conformance/capability_v1/fixtures/capability-contract.json';
import evaluation from '../../../conformance/capability_v1/evaluation.json';
import policy from '../../../conformance/capability_v1/trust-policy.json';
import registry from '../../public/capabilities/index-v1.json';
import { loadPublishedRecords } from './catalog';
import { canonicalJson, sha256Hex } from './integrity';
import { projectPublishedRecord, projectFiniteCapabilityV1 } from './object-projections';
import { loadObjectProjections, loadFiniteCapabilityArtifacts } from '../data/object-projections';

describe('presentation adapters over two distinct source domains', () => {
  test('preserves record 001 values and separate axes without adding theorem authority', async () => {
    const packages = await loadPublishedRecords();
    const projected = projectPublishedRecord(packages[0]);
    const object = projected.objects[0];
    expect(object.authority).toBe('NONE');
    expect(object.source.id).toBe(sourceRecord.id);
    expect(object.source.content_sha256).toBe(sourceRecord.content_sha256);
    expect(object.source.transport_sha256).toBe(catalog.records[0].record_transport_sha256);
    expect(object.details).toEqual({ axes: sourceRecord.axes, admission: sourceRecord.admission, source: sourceRecord.source, scope: catalog.records[0].scope });
    expect(object.axes).toEqual({ historical_result: catalog.records[0].historic_status, lifecycle: catalog.records[0].lifecycle, research_maturity: 'UNKNOWN', current_applicability: 'UNKNOWN', freshness: sourceRecord.axes.current_requalification.status, action_authorization: 'NONE' });
    expect(object.unknowns).toEqual(catalog.records[0].unknowns);
    expect(projected.relations).toEqual([]);
    object.details.axes = {};
    expect(packages[0].record).toEqual(sourceRecord);
  });

  test('projects Resolve source states and only its declared route and withdrawal relations', async () => {
    const packages = await loadPublishedRecords();
    const projected = projectPublishedRecord(packages[1]);
    expect(projected.objects[0].details).toEqual({ interpretation: resolveRecord.interpretation, sources: resolveRecord.sources, publisher_notice: resolveRecord.publisher_notice });
    for (const claim of resolveRecord.derivation.claims) {
      const object = projected.objects.find(item => item.source_id === claim.id)!;
      expect(object.details).toEqual({ ...claim, resolution: resolveRecord.resolutions[claim.id as keyof typeof resolveRecord.resolutions] });
      expect(object.axes.historical_result).toBe(resolveRecord.resolutions[claim.id as keyof typeof resolveRecord.resolutions].after);
      expect(object.axes.current_applicability).toBe(catalog.records[1].current_applicability);
    }
    expect(projected.relations.map(edge => [edge.type, edge.source_id, edge.target_id])).toEqual([
      ...resolveRecord.derivation.routes.flatMap(route => [
        ...route.evidence.map(id => ['EVIDENCE_FOR', id, route.conclusion]),
        ...route.premises.map(id => ['PREMISE_FOR', id, route.conclusion]),
      ]),
      ...resolveRecord.derivation.withdrawn_evidence.map(id => ['WITHDRAWS', resolveRecord.id, id]),
    ]);
    for (const relation of projected.relations) {
      expect(relation.authority).toBe('NONE');
      expect(relation.directed).toBe(true);
      expect(relation.provenance.source).toEqual(projected.objects[0].source);
      expect(relation.provenance.pointer).toMatch(/^\/derivation\/(routes|withdrawn_evidence)\//);
    }
    expect(projected.relations.some(edge => (edge.type as string).includes('EQUIVALENT'))).toBe(false);
  });

  test('checks the two-domain extension matrix against committed contracts', async () => {
    const { objects } = await loadObjectProjections();
    const record = objects.find(item => item.source_id === sourceRecord.id)!;
    const capability = objects.find(item => item.source_id === contract.id)!;
    const matrix = [
      { object: record, contract: sourceRecord.schema, verifier: [sourceRecord.axes.finite_executable.authority, sourceRecord.axes.formal_verification.authority], assumptions: [sourceRecord.axes.finite_executable.case_scope, sourceRecord.axes.formal_verification.scope], lifecycle: catalog.records[0].lifecycle, replay: [sourceRecord.source.commit, sourceRecord.source.external_suite_commit, sourceRecord.source.lean_toolchain], unknowns: catalog.records[0].unknowns, unsupported: ['whole_language_correctness', 'statement_fidelity', 'generalization', 'current_requalification'] },
      { object: capability, contract: contract.schema_version, verifier: [policy.verifier.id, policy.qualification_basis], assumptions: contract.assumptions, lifecycle: 'UNKNOWN', replay: [contract.boundary.sha256, policy.verifier.sha256], unknowns: ['current_applicability', 'freshness', 'revocation', 'supersession'], unsupported: contract.limitations },
    ];
    for (const row of matrix) {
      expect(row.object.source.contract).toBe(row.contract);
      expect(row.object.verifier_authority).toEqual(row.verifier);
      expect(row.object.assumptions).toEqual(row.assumptions);
      expect(row.object.axes.lifecycle).toBe(row.lifecycle);
      expect(row.object.replay_boundary).toEqual(row.replay);
      expect(row.object.unknowns).toEqual(row.unknowns);
      expect(row.object.unsupported_semantics).toEqual(row.unsupported);
    }
    expect(capability.axes).toEqual({ historical_result: evaluation.qualification, lifecycle: 'UNKNOWN', research_maturity: 'UNKNOWN', current_applicability: evaluation.current_applicability, freshness: evaluation.freshness, action_authorization: evaluation.action_authorization });
    expect(capability.details).toEqual({ claim: contract.claim, preconditions: contract.preconditions, guarantees: contract.guarantees, limitations: contract.limitations, inputs: contract.inputs, outputs: contract.outputs, boundary: contract.boundary, implementation: contract.implementation, evidence: contract.evidence, evaluation });
    expect(capability.source.transport_sha256).toBe(registry.qualified_entries[0].contract.sha256);
  });

  test('does not transfer snapshot lifecycle or qualification to individual Resolve claims', async () => {
    const projected = projectPublishedRecord((await loadPublishedRecords())[1]);
    for (const child of projected.objects.slice(1)) {
      expect(child.axes.research_maturity).toBe('UNKNOWN');
      if (child.kind === 'RESOLVE_CLAIM') {
        expect(child.axes.lifecycle).toBe('UNKNOWN');
        expect(child.verifier_authority).toEqual(['UNKNOWN']);
      }
      if (child.kind === 'RESOLVE_RECEIPT') {
        const receipt = resolveRecord.derivation.receipts.find(item => item.id === child.source_id)!;
        expect(child.verifier_authority).toEqual([resolveRecord.derivation.receipt_admission[receipt.kind as keyof typeof resolveRecord.derivation.receipt_admission]]);
      }
    }
    for (const id of resolveRecord.derivation.withdrawn_evidence) {
      expect(projected.objects.find(object => object.source_id === id)?.axes.lifecycle).toBe('WITHDRAWN');
    }
  });

  test('adding or declining capability support leaves record 001 byte-for-byte unchanged', async () => {
    const before = await loadObjectProjections({ includeCapability: false });
    const withCapability = await loadObjectProjections();
    const after = await loadObjectProjections({ includeCapability: false });
    const pick = (objects: typeof before.objects) => canonicalJson(objects.find(item => item.source_id === sourceRecord.id));
    expect(pick(before.objects)).toBe(pick(withCapability.objects));
    expect(pick(after.objects)).toBe(pick(before.objects));
    expect(before.objects.some(item => item.source_id === contract.id)).toBe(false);
    for (const entry of catalog.records) {
      const bytes = await readFile(new URL(`../../public/evidence/${entry.id}/record.json`, import.meta.url));
      expect(sha256Hex(bytes)).toBe(entry.record_transport_sha256);
      const json = JSON.parse(bytes.toString());
      expect(json.content_sha256 ?? json.snapshot_sha256).toBe(entry.record_content_sha256);
    }
  });

  test('refuses unsupported kinds, versions, tampered pins, and critical capability extensions', async () => {
    const packages = await loadPublishedRecords();
    expect(() => projectPublishedRecord({ ...packages[0], record_kind: 'FUTURE' } as never)).toThrow('UNSUPPORTED_PROJECTION_KIND');
    expect(() => projectPublishedRecord({ ...packages[0], entry: { ...packages[0].entry, version: 2 } } as never)).toThrow('UNSUPPORTED_PROJECTION_VERSION');
    const artifacts = await loadFiniteCapabilityArtifacts();
    const changed = structuredClone(contract);
    (changed.extensions as unknown[]).push({ id: 'urn:unsupported:authority', critical: true, payload: {} });
    expect(() => projectFiniteCapabilityV1({ ...artifacts, contractBytes: new TextEncoder().encode(JSON.stringify(changed)) })).toThrow('UNSUPPORTED_CRITICAL_EXTENSION');
    expect(() => projectFiniteCapabilityV1({ ...artifacts, contractBytes: new TextEncoder().encode(JSON.stringify({ ...contract, version: '2' })) })).toThrow('UNSUPPORTED_PROJECTION_VERSION');
    expect(() => projectFiniteCapabilityV1({ ...artifacts, contractBytes: new TextEncoder().encode(JSON.stringify({ ...contract, guarantees: [] })) })).toThrow('CAPABILITY_SOURCE_PIN_MISMATCH');
  });
});
