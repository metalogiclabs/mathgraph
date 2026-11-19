"""Credibility tests runnable without FRET/R2U2 installations or private ZIP."""
from __future__ import annotations
import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

import native_replay as native
import qualify_native as qual


class NativeContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def mock_manifest(self):
        files={}
        for variant in ('source','challenger'):
            binary=self.root/(variant+'.bin');binary.write_bytes(b'compiled-'+variant.encode())
            spec=self.root/(variant+'.c2po');spec.write_bytes((
                '-- C2PO Specification Valid with C2PO/R2U2 v4.0 or greater\r\n'
                'INPUT\r\n\tBOOST: bool;\r\n\tCOAST: bool;\r\nFTSPEC\r\n'
                f'\tROCKET_RESPONSE: (BOOST -> (F[{0 if variant == "source" else 1},7] COAST));\r\n'
            ).encode())
            mapping=self.root/(variant+'.map');mapping.write_bytes(b'BOOST:0\r\nCOAST:1\r\n')
            files[variant]=native.sha(binary)
        result={
            'schema':'mathgraph.check.rocket-native-replay.v1',
            'source_pins':{'fret':native.FRET_SHA,'r2u2':native.R2U2_SHA},
            'source_sha256':dict(qual.SPECS),'map_sha256':qual.MAP,
            'binary_sha256':files,'monitor_executable_sha256':'0'*64,
            'native_oracle_positions':64,'overall':'UNKNOWN',
            'repair_authority':'UNKNOWN','auto_repair':'DENIED','permission':'ADVISORY_ONLY'}
        (self.root/'native-result.json').write_text(json.dumps(result))
        return result

    def test_finite_oracle_has_essential_simultaneous_separator(self):
        x=[{'BOOST':int(i==0),'COAST':int(i==0)} for i in range(8)]
        self.assertIs(native.oracle_at(x,0,0),True)
        self.assertIs(native.oracle_at(x,0,1),False)

    def test_next_tick_positive_control(self):
        x=[{'BOOST':int(i==0),'COAST':int(i==1)} for i in range(8)]
        self.assertIs(native.oracle_at(x,0,0),True)
        self.assertIs(native.oracle_at(x,0,1),True)

    def test_aggregation_decodes_last_timestamp_not_first(self):
        self.assertEqual(native.decode_aggregated('0:1,T\n0:7,F\n'),[True]*2+[False]*6)

    def test_incomplete_output_does_not_pass(self):
        with self.assertRaisesRegex(ValueError,'INCOMPLETE_NATIVE_VERDICTS'):
            native.decode_aggregated('0:6,T')

    def test_overlapping_or_malformed_verdict_refused(self):
        for stream in ('0:2,T\n0:1,F', '0:7,B', '1:7,T'):
            with self.subTest(stream=stream), self.assertRaises(ValueError):
                native.decode_aggregated(stream)

    def test_forged_binary_rebinding_refused(self):
        source=self.root/'source.c2po';source.write_bytes(b'x')
        mapping=self.root/'source.map';mapping.write_bytes(b'x')
        binary=self.root/'source.bin';binary.write_bytes(b'original')
        trace=self.root/'trace.csv';trace.write_text('# BOOST, COAST\n1,1\n')
        with patch.dict(native.SPEC_DIGESTS,{'source':native.sha(source)}),patch.object(native,'MAP_DIGEST',native.sha(mapping)):
            self.assertEqual(native.admitted_binding(source,mapping,binary,trace,'a'*64),'UNKNOWN_BINARY_CHANGED')

    def test_changed_map_and_name_order_refused(self):
        source=self.root/'source.c2po';source.write_bytes(b'x')
        mapping=self.root/'source.map';mapping.write_bytes(b'map')
        binary=self.root/'source.bin';binary.write_bytes(b'binary')
        trace=self.root/'trace.csv';trace.write_text('# COAST, BOOST\n1,1\n')
        with patch.dict(native.SPEC_DIGESTS,{'source':native.sha(source)}):
            self.assertEqual(native.admitted_binding(source,mapping,binary,trace,native.sha(binary)),'UNKNOWN_SIGNAL_MAP_CHANGED')
            with patch.object(native,'MAP_DIGEST',native.sha(mapping)):
                self.assertEqual(native.admitted_binding(source,mapping,binary,trace,native.sha(binary)),'UNKNOWN_SIGNAL_HEADER_CHANGED')

    def test_fake_owner_permission_in_report_rejected(self):
        report=self.mock_manifest()
        report['overall']='WARRANTED'
        (self.root/'native-result.json').write_text(json.dumps(report))
        with self.assertRaisesRegex(ValueError,'EVIDENCE_ATTEMPTS_AUTHORITY_PROMOTION'):
            qual.validate_report(self.root,self.root/'monitor')

    def test_fake_native_outcome_count_refused(self):
        report=self.mock_manifest();report['native_oracle_positions']=63
        (self.root/'native-result.json').write_text(json.dumps(report))
        with self.assertRaisesRegex(ValueError,'UNEXPECTED_CASE_CENSUS'):
            qual.validate_report(self.root,self.root/'monitor')

    def test_altered_digest_claim_refused_before_binary_use(self):
        report=self.mock_manifest();report['binary_sha256']['source']='a'*64
        (self.root/'native-result.json').write_text(json.dumps(report))
        with self.assertRaisesRegex(ValueError,'BINARY_CHANGED'):
            qual.validate_report(self.root,self.root/'monitor')

    def test_receipt_claims_cannot_self_authenticate(self):
        report=self.mock_manifest();report['owner_approved']=True;report['operator']='NASA'
        (self.root/'native-result.json').write_text(json.dumps(report))
        with self.assertRaisesRegex(ValueError,'EVIDENCE_ATTEMPTS_AUTHORITY_PROMOTION'):
            qual.validate_report(self.root,self.root/'monitor')


if __name__=='__main__':unittest.main()
