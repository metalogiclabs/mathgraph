#!/usr/bin/env python3
"""Pure synthetic preflight: no prospective repository source is opened."""
import ast, importlib.util, json, tempfile, pathlib, xml.etree.ElementTree as ET
root = pathlib.Path(__file__).resolve().parent
def load(name, path):
 spec=importlib.util.spec_from_file_location(name, path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
propose=load('preflight_propose',root/'propose.py')
evaluate=load('preflight_evaluate',root/'evaluate.py')
with tempfile.TemporaryDirectory() as d:
 folder=pathlib.Path(d)
 api=folder/'__init__.py';api.write_text('from .writer import dumps, loads\n__all__ = ["dumps", "loads"]\n')
 metadata={'repository':'synthetic/toml','description':'Portable typed mapping interchange','source_sha':'a'*40}
 a=propose.propose(metadata,api,'candidate')
 b=propose.propose(metadata,api,'expert')
 assert a['status']=='CANDIDATE_PENDING_INDEPENDENT_NATIVE_VERIFICATION'
 assert [(x['id'],x['writer']) for x in a['obligations']]==[('external-semantics','dumps'),('native-roundtrip','dumps')]
 assert a['obligations']==b['obligations']
 assert a['api_sha256']==b['api_sha256']
 assert propose.classify('synthetic/opaque','Unrecognized format') is None
 api.write_text('from .writer import obscure\n')
 assert propose.propose(metadata,api,'candidate')['status']=='UNKNOWN_NO_SUPPORTED_RELATION'
 xml=folder/'junit.xml';xml.write_text('<testsuite tests="7" failures="0" errors="0" skipped="1"></testsuite>')
 assert evaluate.native_tests(xml)['passed'] is True
 xml.write_text('<testsuite tests="7" failures="1" errors="0" skipped="0"></testsuite>')
 assert evaluate.native_tests(xml)['passed'] is False
 assert len(evaluate.SAMPLES)==3
print('PRE_EXPOSURE_SYNTHETIC_PREFLIGHT_PASS')
