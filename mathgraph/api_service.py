"""Stable local API contracts and advisory route handlers for MathGraph."""
from __future__ import annotations
import json
from dataclasses import MISSING,dataclass,field
from datetime import datetime,timezone
from enum import Enum
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from typing import Any,Mapping,Sequence
from mathgraph.hashing import content_id
from mathgraph.epistemic_status import build_epistemic_status_view
from mathgraph.lawbook import LawbookEntry,LawbookEntryStatus
from mathgraph.semantic_intake import *
from mathgraph.formal_world_adapters import build_formal_world_adapter_report
from mathgraph.proof_system_integration import ProofBoundaryEvidence,build_proof_system_integration_report
from mathgraph.continuation_curriculum import build_continuation_curriculum
from mathgraph.discovery_value import DiscoveryValueObjectKind,DiscoveryValueScore,DiscoveryValueSignal,DiscoveryValueSignalKind
from mathgraph.process_memory import ProcessMemoryReport,ProcessEpisodeRecord,ProcessEpisodeStatus,make_process_memory_report_id
from mathgraph.structure_registry import build_structure_registry_report
from mathgraph.role_objects import build_role_object_report
from mathgraph.structural_analogy import build_structural_analogy_report
from mathgraph.reason_compression import build_reason_compression_report
from mathgraph.habit_rules import build_habit_formation_report
from mathgraph.version import __version__
def _enum(n,v): return Enum(n,{x:x for x in v.split()},type=str)
ApiRoute=_enum("ApiRoute","HEALTH AUDIT QUERY SUBMIT SEMANTIC_INTAKE FORMAL_WORLD_ADAPTERS PROOF_SYSTEM_INTEGRATION VERIFIER_EXECUTION VERIFIER_FIXTURES VERIFIED_CORPUS LEAN_PROJECT_SUBSET MATHLIB_MICRO_SUBSET MATHLIB_LOCAL_ALLOWLIST MATHLIB_DECLARATION_DISCOVERY MATHLIB_MODULE_VERIFICATION PROOF_LIBRARY_DEMO PUBLIC_DEMO REAL_MATHLIB_REVISION_DEMO REAL_MATHLIB_DEMO RELEASE_CHECK E2E_TESTDRIVE SCHEDULE PROJECT EXPLAIN PROCESS_MEMORY DISCOVERY_VALUE LAWBOOK_ACCEPTANCE_REVIEW STRUCTURAL_IDENTITY HABITS REASONS STRUCTURES ROLES ANALOGIES UNKNOWN")
ApiRequestKind=_enum("ApiRequestKind","READ_ONLY ADVISORY_BUILD QUERY SUBMIT AUDIT SCHEDULE PROJECT EXPLAIN REVIEW UNKNOWN")
ApiResponseStatus=_enum("ApiResponseStatus","OK ACCEPTED_ADVISORY FOUND NOT_FOUND AMBIGUOUS BAD_REQUEST UNSUPPORTED_ROUTE VALIDATION_ERROR HAS_WARNINGS HAS_CRITICALS INTERNAL_ERROR UNKNOWN")
ApiTruthStatus=_enum("ApiTruthStatus","NO_CLAIM ADVISORY_ONLY ACCEPTED_MEMORY VERIFIED_PROOF FINITE_COUNTERMODEL NAMED_OBSTRUCTION BOUNDARY_EVIDENCE_PRESENT KNOWN_SKIP_AVAILABLE BOUNDARY_REQUIRED BOUNDARY_MISSING UNKNOWN")
ApiSafetyLevel=_enum("ApiSafetyLevel","SAFE_READ_ONLY SAFE_ADVISORY SAFE_REVIEW_REQUIRED BLOCKED_UNSAFE BLOCKED_MUTATION BLOCKED_EXTERNAL_EXECUTION UNKNOWN")
ApiArtifactKind=_enum("ApiArtifactKind","SEMANTIC_REPORT FORMAL_WORLD_ADAPTER_REPORT PROOF_SYSTEM_REPORT VERIFIER_EXECUTION_REPORT LAWBOOK_QUERY_REPORT CONTINUATION_OUTPUT CURRICULUM DISCOVERY_VALUE_REPORT PROCESS_MEMORY_REPORT PROJECTION_CANDIDATE PROOF_DIGESTION_TRACE VERIFIER_FEEDBACK REPAIR_TRACE STRUCTURE_REPORT ROLE_REPORT ANALOGY_REPORT HABIT_REPORT REASON_REPORT ALIEN UNKNOWN")
def now_iso(): return datetime.now(timezone.utc).isoformat()
def _serial(cls,enums=()):
 def td(self):
  d=dict(self.__dict__)
  for k in enums:
   if isinstance(d.get(k),Enum): d[k]=d[k].value
  for k,v in list(d.items()):
   if isinstance(v,tuple): d[k]=list(v)
   elif hasattr(v,"to_dict"): d[k]=v.to_dict()
  return d
 @classmethod
 def fd(c,d):
  vals=[]
  for f in c.__dataclass_fields__.values():
   v=d[f.name] if f.name in d else f.default if f.default is not MISSING else f.default_factory() if f.default_factory is not MISSING else None
   if f.name in enums and v is not None:
    typ=globals()[str(f.type).split("|")[0]] if not isinstance(f.type,type) else f.type; v=typ(str(v))
   if getattr(f.type,"__origin__",None) is tuple and v is not None: v=tuple(v)
   vals.append(v)
  return c(*vals)
 cls.to_dict=td; cls.from_dict=fd; cls.to_json=lambda self:_j(self.to_dict()); cls.from_json=classmethod(lambda c,t:c.from_dict(json.loads(t))); return cls
@dataclass
class ApiRequest:
 request_id:str; route:ApiRoute; request_kind:ApiRequestKind=ApiRequestKind.UNKNOWN; payload:dict[str,Any]=field(default_factory=dict); options:dict[str,Any]=field(default_factory=dict); idempotency_key:str|None=None; created_at:str=field(default_factory=now_iso); metadata:dict[str,Any]=field(default_factory=dict); advisory:bool=True
@dataclass
class ApiHealth:
 service_name:str="mathgraph-local"; version:str|None=None; status:ApiResponseStatus=ApiResponseStatus.OK; implemented_routes:tuple[str,...]=(); read_only:bool=True; external_execution_enabled:bool=False; verifier_execution_enabled:bool=False; boundary_policy:str="Only verifier/importer/finite-validator/chain-audit evidence promotes truth."; module_counts:dict[str,int]=field(default_factory=dict); warnings:tuple[str,...]=(); criticals:tuple[str,...]=(); created_at:str=field(default_factory=now_iso); advisory:bool=True
@dataclass
class ApiAuditResult:
 audit_id:str; status:ApiResponseStatus=ApiResponseStatus.OK; finding_count:int=0; critical_count:int=0; warning_count:int=0; info_count:int=0; findings:tuple[dict[str,Any],...]=(); boundary_ok:bool=True; public_terms_ok:bool|None=None; metadata:dict[str,Any]=field(default_factory=dict); created_at:str=field(default_factory=now_iso); advisory:bool=True
@dataclass
class ApiRouteResult:
 route_result_id:str; route:ApiRoute; status:ApiResponseStatus; truth_status:ApiTruthStatus=ApiTruthStatus.ADVISORY_ONLY; safety_level:ApiSafetyLevel=ApiSafetyLevel.SAFE_ADVISORY; artifacts:list[dict[str,Any]]=field(default_factory=list); artifact_kinds:tuple[str,...]=(); summary:dict[str,Any]=field(default_factory=dict); warnings:tuple[str,...]=(); criticals:tuple[str,...]=(); boundary_evidence:tuple[dict[str,Any],...]=(); verifier_boundary_crossed:bool=False; certificate_ids:tuple[str,...]=(); terminal_forms:tuple[str,...]=(); metadata:dict[str,Any]=field(default_factory=dict); advisory:bool=True
 def has_boundary_evidence(self): return bool(self.verifier_boundary_crossed and self.certificate_ids and self.terminal_forms and self.boundary_evidence)
@dataclass
class ApiResponse:
 response_id:str; request_id:str|None; route:ApiRoute; status:ApiResponseStatus; truth_status:ApiTruthStatus=ApiTruthStatus.ADVISORY_ONLY; safety_level:ApiSafetyLevel=ApiSafetyLevel.SAFE_ADVISORY; result:ApiRouteResult|None=None; health:ApiHealth|None=None; audit:ApiAuditResult|None=None; message:str|None=None; errors:tuple[str,...]=(); warnings:tuple[str,...]=(); criticals:tuple[str,...]=(); boundary_policy:str="API responses do not promote truth; only explicit verifier/importer/finite-validator/chain-audit evidence does."; created_at:str=field(default_factory=now_iso); metadata:dict[str,Any]=field(default_factory=dict); advisory:bool=True
 def has_boundary_evidence(self): return bool(self.result and self.result.has_boundary_evidence())
 def ok(self): return self.status in {ApiResponseStatus.OK,ApiResponseStatus.FOUND,ApiResponseStatus.ACCEPTED_ADVISORY}
 def to_dict(self):
  d=dict(self.__dict__); d.update({"route":self.route.value,"status":self.status.value,"truth_status":self.truth_status.value,"safety_level":self.safety_level.value,"result":self.result.to_dict() if self.result else None,"health":self.health.to_dict() if self.health else None,"audit":self.audit.to_dict() if self.audit else None,"errors":list(self.errors),"warnings":list(self.warnings),"criticals":list(self.criticals)}); return d
 @classmethod
 def from_dict(c,d): return c(str(d["response_id"]),d.get("request_id"),ApiRoute(str(d.get("route","UNKNOWN"))),ApiResponseStatus(str(d.get("status","UNKNOWN"))),ApiTruthStatus(str(d.get("truth_status","ADVISORY_ONLY"))),ApiSafetyLevel(str(d.get("safety_level","SAFE_ADVISORY"))),ApiRouteResult.from_dict(d["result"]) if d.get("result") else None,ApiHealth.from_dict(d["health"]) if d.get("health") else None,ApiAuditResult.from_dict(d["audit"]) if d.get("audit") else None,d.get("message"),tuple(d.get("errors",())),tuple(d.get("warnings",())),tuple(d.get("criticals",())),str(d.get("boundary_policy","")),str(d.get("created_at",now_iso())),dict(d.get("metadata",{})),bool(d.get("advisory",True)))
 def to_json(self): return _j(self.to_dict())
 @classmethod
 def from_json(c,t): return c.from_dict(json.loads(t))
for _c,_e in [(ApiRequest,("route","request_kind")),(ApiHealth,("status",)),(ApiAuditResult,("status",)),(ApiRouteResult,("route","status","truth_status","safety_level"))]: _serial(_c,_e)
@dataclass
class ApiServiceState:
 accepted_lawbook_entries:list[LawbookEntry]=field(default_factory=list); semantic_reports:list[SemanticIntakeReport]=field(default_factory=list); formal_world_reports:list[Any]=field(default_factory=list); proof_system_reports:list[Any]=field(default_factory=list); process_memory_reports:list[ProcessMemoryReport]=field(default_factory=list); raw_events:list[dict[str,Any]]=field(default_factory=list); read_only:bool=True; external_execution_enabled:bool=False; verifier_execution_enabled:bool=False; metadata:dict[str,Any]=field(default_factory=dict)
 def to_dict(self): return {**self.__dict__,"accepted_lawbook_entries":[x.to_dict() for x in self.accepted_lawbook_entries],"semantic_reports":[x.to_dict() for x in self.semantic_reports],"formal_world_reports":[x.to_dict() for x in self.formal_world_reports],"proof_system_reports":[x.to_dict() for x in self.proof_system_reports],"process_memory_reports":[x.to_dict() for x in self.process_memory_reports]}
 @classmethod
 def from_dict(c,d): return c([LawbookEntry.from_dict(x) for x in d.get("accepted_lawbook_entries",())],[SemanticIntakeReport.from_dict(x) for x in d.get("semantic_reports",())],[],[],[],list(d.get("raw_events",())),bool(d.get("read_only",True)),bool(d.get("external_execution_enabled",False)),bool(d.get("verifier_execution_enabled",False)),dict(d.get("metadata",{})))
 def add_raw_event(self,e): self.raw_events.append(dict(e))
 def accepted_entry_count(self): return len(self.accepted_lawbook_entries)
 def report_counts(self): return {"semantic":len(self.semantic_reports),"formal_world":len(self.formal_world_reports),"proof_system":len(self.proof_system_reports),"process_memory":len(self.process_memory_reports)}
def make_api_request_id(*x): return content_id("api-request",x)
def make_api_response_id(*x): return content_id("api-response",x)
def make_api_audit_id(*x): return content_id("api-audit",x)
def make_api_route_result_id(*x): return content_id("api-route-result",x)
def api_payload_to_objects(p):
 out=[]
 if p.get("text"): out.append(p["text"])
 out+=list(p.get("texts",()))
 if p.get("claim"): out.append(p["claim"])
 out+=list(p.get("claims",()))
 if p.get("source") or p.get("target"): out.append({"source":p.get("source"),"target":p.get("target")})
 out+=list(p.get("objects",()))+list(p.get("raw_events",()))
 for k,cls in (("semantic_report",SemanticIntakeReport),):
  if p.get(k): out.append(cls.from_dict(p[k]) if isinstance(p[k],Mapping) else p[k])
 for k in ("semantic_reports","formal_world_reports","proof_system_reports","lawbook_entries","agent_experiences"):
  out+=list(p.get(k,()))
 return out or ([dict(p)] if p else [])
def extract_boundary_evidence_from_objects(objs):
 cert=[]; terms=[]; ev=[]
 for o in objs:
  d=o.to_dict() if hasattr(o,"to_dict") else o if isinstance(o,Mapping) else {}
  if d.get("certificate_id") and d.get("terminal_form") and d.get("verifier_boundary_crossed"):
   cert.append(str(d["certificate_id"])); terms.append(str(d["terminal_form"])); ev.append(d)
  if isinstance(o,ProofBoundaryEvidence) and o.is_valid_boundary(): ev.append(o.to_dict()); cert.append(o.certificate_id); terms.append(o.terminal_form.value)
 return {"certificate_ids":tuple(dict.fromkeys(cert)),"terminal_forms":tuple(dict.fromkeys(terms)),"boundary_evidence":tuple(ev),"verifier_boundary_crossed":bool(ev)}
def artifact_to_api_dict(o,artifact_kind=None):
 d=o.to_dict() if hasattr(o,"to_dict") else dict(o) if isinstance(o,Mapping) else {"value":str(o)}; b=extract_boundary_evidence_from_objects([o]); kind=artifact_kind.value if isinstance(artifact_kind,Enum) else artifact_kind or _artifact_kind(o).value
 return {"artifact_kind":kind,"object_type":o.__class__.__name__,"data":d,"advisory":bool(d.get("advisory",True)),"truth_boundary":{k:(list(v) if isinstance(v,tuple) else v) for k,v in b.items() if k!="boundary_evidence"},"epistemic_status":build_epistemic_status_view(o)}
def _artifact_kind(o):
 n=o.__class__.__name__
 return {"SemanticIntakeReport":ApiArtifactKind.SEMANTIC_REPORT,"FormalWorldAdapterReport":ApiArtifactKind.FORMAL_WORLD_ADAPTER_REPORT,"ProofSystemIntegrationReport":ApiArtifactKind.PROOF_SYSTEM_REPORT,"VerifierExecutionReport":ApiArtifactKind.VERIFIER_EXECUTION_REPORT,"ProcessMemoryReport":ApiArtifactKind.PROCESS_MEMORY_REPORT}.get(n,ApiArtifactKind.ALIEN)
def route_result_from_artifacts(route,artifacts,status=ApiResponseStatus.ACCEPTED_ADVISORY,truth_status=ApiTruthStatus.ADVISORY_ONLY,safety=ApiSafetyLevel.SAFE_ADVISORY):
 wrapped=[artifact_to_api_dict(x) for x in artifacts]; b=extract_boundary_evidence_from_objects(artifacts)
 return ApiRouteResult(make_api_route_result_id(route.value,[w["object_type"] for w in wrapped]),route,status,truth_status,safety,wrapped,tuple(w["artifact_kind"] for w in wrapped),{"artifact_total":len(wrapped)},boundary_evidence=b["boundary_evidence"],verifier_boundary_crossed=b["verifier_boundary_crossed"],certificate_ids=b["certificate_ids"],terminal_forms=b["terminal_forms"])
def _resp(req,result=None,*,status=None,truth=None,safety=None,message=None,health=None,audit=None):
 return ApiResponse(make_api_response_id(req.request_id,req.route.value),req.request_id,req.route,status or (result.status if result else ApiResponseStatus.OK),truth or (result.truth_status if result else ApiTruthStatus.NO_CLAIM),safety or (result.safety_level if result else ApiSafetyLevel.SAFE_READ_ONLY),result,health,audit,message)
def handle_health(state,req):
 h=ApiHealth(version=__version__,implemented_routes=tuple(x.value for x in ApiRoute if x!=ApiRoute.UNKNOWN),read_only=state.read_only,external_execution_enabled=state.external_execution_enabled,verifier_execution_enabled=state.verifier_execution_enabled,module_counts=state.report_counts())
 return _resp(req,health=h)
def handle_audit(state,req):
 from mathgraph.roadmap_alignment import check_roadmap_alignment
 rep=check_roadmap_alignment(semantic_intake_reports=state.semantic_reports,proof_system_integration_reports=state.proof_system_reports,formal_world_adapter_reports=state.formal_world_reports)
 a=ApiAuditResult(make_api_audit_id(req.request_id),ApiResponseStatus.HAS_CRITICALS if rep.critical_count() else ApiResponseStatus.OK,len(rep.findings),rep.critical_count(),rep.warning_count(),rep.info_count(),tuple(x.to_dict() for x in rep.findings),rep.critical_count()==0)
 return _resp(req,audit=a,status=a.status)
def handle_query(state,req):
 p=req.payload; found=[e for e in state.accepted_lawbook_entries if e.status==LawbookEntryStatus.ACCEPTED and (not p.get("entry_id") or e.entry_id==p["entry_id"]) and (not p.get("claim_id") or e.claim_id==p["claim_id"]) and (not p.get("source") or e.source==p["source"]) and (not p.get("target") or e.target==p["target"])]
 if not found:return _resp(req,route_result_from_artifacts(req.route,[],ApiResponseStatus.NOT_FOUND,ApiTruthStatus.ADVISORY_ONLY,ApiSafetyLevel.SAFE_READ_ONLY))
 e=found[0]; truth=ApiTruthStatus[e.terminal_form.value] if e.terminal_form and e.certificate_id and e.verifier_boundary_crossed else ApiTruthStatus.ACCEPTED_MEMORY
 return _resp(req,route_result_from_artifacts(req.route,found,ApiResponseStatus.FOUND,truth,ApiSafetyLevel.SAFE_READ_ONLY))
def handle_semantic_intake(state,req):
 r=build_semantic_intake_report(api_payload_to_objects(req.payload)); return _resp(req,route_result_from_artifacts(req.route,[r]))
def handle_formal_world_adapters(state,req):
 r=build_formal_world_adapter_report(api_payload_to_objects(req.payload)); return _resp(req,route_result_from_artifacts(req.route,[r],truth_status=ApiTruthStatus.BOUNDARY_REQUIRED))
def handle_proof_system_integration(state,req):
 r=build_proof_system_integration_report(api_payload_to_objects(req.payload)); truth=ApiTruthStatus.BOUNDARY_EVIDENCE_PRESENT if r.boundary_evidence else ApiTruthStatus.BOUNDARY_REQUIRED; return _resp(req,route_result_from_artifacts(req.route,[r],truth_status=truth))
def handle_verifier_execution(state,req):
 from mathgraph.verifier_execution import build_verifier_execution_report
 r=build_verifier_execution_report(api_payload_to_objects(req.payload),workspace_root=req.options.get("workspace_root"),allow_execution=bool(req.options.get("allow_execution",False))); truth=ApiTruthStatus.BOUNDARY_EVIDENCE_PRESENT if r.boundary_evidence else ApiTruthStatus.BOUNDARY_REQUIRED; return _resp(req,route_result_from_artifacts(req.route,[r,*r.boundary_evidence],truth_status=truth,safety=ApiSafetyLevel.SAFE_REVIEW_REQUIRED if not r.boundary_evidence else ApiSafetyLevel.SAFE_ADVISORY))
def handle_verifier_fixtures(state,req):
 from mathgraph.verifier_fixtures import build_default_lean_fixture_suite,run_verifier_fixture_suite
 suite=build_default_lean_fixture_suite(req.payload.get("fixture_root")); r=run_verifier_fixture_suite(suite,workspace_root=req.options.get("workspace_root") or req.payload.get("workspace_root") or "/tmp/mathgraph_api_fixtures",allow_execution=bool(req.options.get("allow_execution",False)),allow_missing_verifier=bool(req.options.get("allow_missing_verifier",True)),timeout_sec=float(req.options.get("timeout_sec",20.0))); truth=ApiTruthStatus.BOUNDARY_EVIDENCE_PRESENT if r.boundary_evidence_count() else ApiTruthStatus.BOUNDARY_REQUIRED; return _resp(req,route_result_from_artifacts(req.route,[r],truth_status=truth,safety=ApiSafetyLevel.SAFE_REVIEW_REQUIRED))
def handle_verified_corpus(state,req):
 from mathgraph.verified_corpus import build_default_micro_corpus_manifest,ingest_verified_corpus
 manifest=req.payload.get("manifest_json") or req.payload.get("manifest_path") or build_default_micro_corpus_manifest(req.payload.get("corpus_root"))
 r=ingest_verified_corpus(manifest,workspace_root=req.options.get("workspace_root") or req.payload.get("workspace_root") or "/tmp/mathgraph_api_corpus",allow_execution=bool(req.options.get("allow_execution",False)),allow_missing_verifier=bool(req.options.get("allow_missing_verifier",True)),timeout_sec=float(req.options.get("timeout_sec",20.0)),accept_verified_entries_in_memory=bool(req.options.get("accept_verified_entries_in_memory",False)))
 truth=ApiTruthStatus.BOUNDARY_EVIDENCE_PRESENT if r.verified_entry_count() else ApiTruthStatus.BOUNDARY_REQUIRED
 return _resp(req,route_result_from_artifacts(req.route,[r],truth_status=truth,safety=ApiSafetyLevel.SAFE_REVIEW_REQUIRED))
def handle_lean_project_subset(state,req):
 from mathgraph.lean_project_subset import build_default_micro_project_manifest,ingest_lean_project_subset
 manifest=req.payload.get("manifest_json") or req.payload.get("manifest_path") or build_default_micro_project_manifest(req.payload.get("project_root"))
 r=ingest_lean_project_subset(manifest,workspace_root=req.options.get("workspace_root") or req.payload.get("workspace_root") or "/tmp/mathgraph_api_project",allow_execution=bool(req.options.get("allow_execution",False)),allow_missing_verifier=bool(req.options.get("allow_missing_verifier",True)),timeout_sec=float(req.options.get("timeout_sec",20.0)),accept_verified_entries_in_memory=bool(req.options.get("accept_verified_entries_in_memory",False)))
 truth=ApiTruthStatus.BOUNDARY_EVIDENCE_PRESENT if r.verified_entry_count() else ApiTruthStatus.BOUNDARY_REQUIRED
 return _resp(req,route_result_from_artifacts(req.route,[r],truth_status=truth,safety=ApiSafetyLevel.SAFE_REVIEW_REQUIRED))
def handle_mathlib_micro_subset(state,req):
 from mathgraph.mathlib_micro_subset import build_default_mathlib_micro_manifest,ingest_mathlib_micro_subset
 manifest=req.payload.get("manifest_json") or req.payload.get("manifest_path") or build_default_mathlib_micro_manifest(req.payload.get("project_root"))
 r=ingest_mathlib_micro_subset(manifest,project_root=req.payload.get("project_root"),workspace_root=req.options.get("workspace_root") or req.payload.get("workspace_root") or "/tmp/mathgraph_api_mathlib_micro",allow_execution=bool(req.options.get("allow_execution",False)),allow_missing_verifier=bool(req.options.get("allow_missing_verifier",True)),timeout_sec=float(req.options.get("timeout_sec",20.0)),accept_verified_entries_in_memory=bool(req.options.get("accept_verified_entries_in_memory",False)),require_lake=bool(req.options.get("require_lake",False)),require_mathlib_marker=bool(req.options.get("require_mathlib_marker",False)))
 truth=ApiTruthStatus.BOUNDARY_EVIDENCE_PRESENT if r.verified_entry_count() else ApiTruthStatus.BOUNDARY_REQUIRED
 return _resp(req,route_result_from_artifacts(req.route,[r],truth_status=truth,safety=ApiSafetyLevel.SAFE_REVIEW_REQUIRED))
def handle_mathlib_local_allowlist(state,req):
 from mathgraph.mathlib_local_allowlist import build_synthetic_external_allowlist_manifest,ingest_mathlib_local_allowlist
 manifest=req.payload.get("manifest_json") or req.payload.get("manifest_path") or build_synthetic_external_allowlist_manifest()
 r=ingest_mathlib_local_allowlist(manifest,project_root=req.payload.get("project_root"),workspace_root=req.options.get("workspace_root") or req.payload.get("workspace_root") or "/tmp/mathgraph_api_mathlib_local",allow_execution=bool(req.options.get("allow_execution",False)),allow_missing_verifier=bool(req.options.get("allow_missing_verifier",True)),timeout_sec=float(req.options.get("timeout_sec",20.0)),accept_verified_entries_in_memory=bool(req.options.get("accept_verified_entries_in_memory",False)),require_lake=bool(req.options.get("require_lake",False)),require_mathlib_marker=bool(req.options.get("require_mathlib_marker",False)))
 truth=ApiTruthStatus.BOUNDARY_EVIDENCE_PRESENT if r.verified_entry_count() else ApiTruthStatus.BOUNDARY_REQUIRED
 return _resp(req,route_result_from_artifacts(req.route,[r],truth_status=truth,safety=ApiSafetyLevel.SAFE_REVIEW_REQUIRED))
def handle_mathlib_declaration_discovery(state,req):
 from mathgraph.mathlib_declaration_discovery import build_synthetic_mathlib_discovery_request,run_mathlib_declaration_discovery
 request=req.payload.get("request_json") or req.payload.get("request_path") or build_synthetic_mathlib_discovery_request()
 r=run_mathlib_declaration_discovery(request,project_root=req.payload.get("project_root"),build_manifest=bool(req.options.get("build_manifest",True)),run_allowlist_ingestion=bool(req.options.get("run_allowlist_ingestion",False)),allow_execution=bool(req.options.get("allow_execution",False)),allow_missing_verifier=bool(req.options.get("allow_missing_verifier",True)),timeout_sec=float(req.options.get("timeout_sec",20.0)),accept_verified_entries_in_memory=bool(req.options.get("accept_verified_entries_in_memory",False)),require_mathlib_marker=bool(req.options.get("require_mathlib_marker",False)))
 truth=ApiTruthStatus.BOUNDARY_EVIDENCE_PRESENT if r.allowlist_ingestion_report and r.allowlist_ingestion_report.verified_entry_count() else ApiTruthStatus.ADVISORY_ONLY
 return _resp(req,route_result_from_artifacts(req.route,[r],truth_status=truth,safety=ApiSafetyLevel.SAFE_REVIEW_REQUIRED))
def handle_proof_library_demo(state,req):
 from mathgraph.proof_library_demo import build_synthetic_proof_library_demo_config,run_proof_library_demo
 config=req.payload.get("config_json") or req.payload.get("config_path") or build_synthetic_proof_library_demo_config()
 r=run_proof_library_demo(config,out_dir=req.options.get("out_dir") or req.payload.get("out_dir"),project_root=req.payload.get("project_root"),use_synthetic_request=req.options.get("use_synthetic_request"),allow_execution=bool(req.options.get("allow_execution",False)),allow_missing_verifier=bool(req.options.get("allow_missing_verifier",True)),run_allowlist_ingestion=bool(req.options.get("run_allowlist_ingestion",False)),accept_verified_entries_in_memory=bool(req.options.get("accept_verified_entries_in_memory",False)),timeout_sec=float(req.options.get("timeout_sec",20.0)),require_mathlib_marker=bool(req.options.get("require_mathlib_marker",False)))
 truth=ApiTruthStatus.KNOWN_SKIP_AVAILABLE if r.known_skip_count() else ApiTruthStatus.BOUNDARY_EVIDENCE_PRESENT if r.downstream_verified_count() else ApiTruthStatus.ADVISORY_ONLY
 return _resp(req,route_result_from_artifacts(req.route,[r],truth_status=truth,safety=ApiSafetyLevel.SAFE_REVIEW_REQUIRED))
def handle_public_demo(state,req):
 from mathgraph.demo_release import run_public_demo
 r=run_public_demo(req.payload.get("config_json") or req.payload.get("config_path"),out_dir=req.options.get("out_dir") or req.payload.get("out_dir"),allow_execution=bool(req.options.get("allow_execution",False)),allow_missing_verifier=bool(req.options.get("allow_missing_verifier",True)),accept_verified_entries_in_memory=req.options.get("accept_verified_entries_in_memory"),timeout_sec=float(req.options.get("timeout_sec",20.0)))
 truth=ApiTruthStatus.KNOWN_SKIP_AVAILABLE if r.known_skip_count() else ApiTruthStatus.BOUNDARY_EVIDENCE_PRESENT if r.boundary_evidence_count() else ApiTruthStatus.ADVISORY_ONLY
 return _resp(req,route_result_from_artifacts(req.route,[r],truth_status=truth,safety=ApiSafetyLevel.SAFE_REVIEW_REQUIRED))
def handle_real_mathlib_revision_demo(state,req):
 from mathgraph.demo_release import RealMathlibRevisionDemoConfig,default_real_mathlib_revision_demo_config_dict,run_real_mathlib_revision_demo
 config=req.payload.get("config_json") or req.payload.get("config_path") or RealMathlibRevisionDemoConfig.from_dict(default_real_mathlib_revision_demo_config_dict())
 r=run_real_mathlib_revision_demo(config,out_dir=req.options.get("out_dir") or req.payload.get("out_dir"),project_root=req.payload.get("project_root") or req.options.get("project_root"),allow_execution=bool(req.options.get("allow_execution",False)),allow_missing_verifier=bool(req.options.get("allow_missing_verifier",True)),run_allowlist_ingestion=req.options.get("run_allowlist_ingestion"),accept_verified_entries_in_memory=req.options.get("accept_verified_entries_in_memory"),timeout_sec=float(req.options.get("timeout_sec",20.0)),require_mathlib_marker=bool(req.options.get("require_mathlib_marker",True)))
 truth=ApiTruthStatus.KNOWN_SKIP_AVAILABLE if r.known_skip_count() else ApiTruthStatus.BOUNDARY_EVIDENCE_PRESENT if r.verified_count() else ApiTruthStatus.ADVISORY_ONLY
 return _resp(req,route_result_from_artifacts(req.route,[r],truth_status=truth,safety=ApiSafetyLevel.SAFE_REVIEW_REQUIRED))
def handle_real_mathlib_demo(state,req):
 from mathgraph.real_mathlib_demo import run_real_mathlib_demo
 r=run_real_mathlib_demo(req.payload.get("config_json") or req.payload.get("config_path"),out_dir=req.options.get("out_dir") or req.payload.get("out_dir"),project_root=req.payload.get("project_root") or req.options.get("project_root"),allow_execution=bool(req.options.get("allow_execution",False)),allow_missing_verifier=bool(req.options.get("allow_missing_verifier",True)),run_allowlist_ingestion=req.options.get("run_allowlist_ingestion"),run_module_verification=bool(req.options.get("run_module_verification",False)),enable_name_candidate_fallback=bool(req.options.get("enable_name_candidate_fallback",False)),module_verification_execution_mode=req.options.get("execution_mode"),accept_verified_entries_in_memory=req.options.get("accept_verified_entries_in_memory"),timeout_sec=float(req.options.get("timeout_sec",20.0)))
 truth=ApiTruthStatus.KNOWN_SKIP_AVAILABLE if r.known_skip_count() else ApiTruthStatus.BOUNDARY_EVIDENCE_PRESENT if r.verified_count() else ApiTruthStatus.ADVISORY_ONLY
 return _resp(req,route_result_from_artifacts(req.route,[r],truth_status=truth,safety=ApiSafetyLevel.SAFE_REVIEW_REQUIRED))
def handle_mathlib_module_verification(state,req):
 from mathgraph.mathlib_module_verification import MathlibModuleVerificationRequest,run_mathlib_module_verification
 r=run_mathlib_module_verification(req.payload.get("request_json") or req.payload.get("request_path") or MathlibModuleVerificationRequest("api-empty-module-verification"),project_root=req.options.get("project_root") or req.payload.get("project_root"),workspace_root=req.options.get("workspace_root"),allow_execution=bool(req.options.get("allow_execution",False)),allow_missing_verifier=bool(req.options.get("allow_missing_verifier",True)),accept_verified_entries_in_memory=req.options.get("accept_verified_entries_in_memory"),enable_name_candidate_fallback=req.options.get("enable_name_candidate_fallback"),execution_mode=req.options.get("execution_mode"),timeout_sec=float(req.options.get("timeout_sec",20.0)))
 truth=ApiTruthStatus.KNOWN_SKIP_AVAILABLE if r.known_skip_count() else ApiTruthStatus.BOUNDARY_EVIDENCE_PRESENT if r.verified_count() else ApiTruthStatus.ADVISORY_ONLY
 return _resp(req,route_result_from_artifacts(req.route,[r],truth_status=truth,safety=ApiSafetyLevel.SAFE_REVIEW_REQUIRED))
def handle_release_check(state,req):
 from mathgraph.demo_release import run_release_checks
 checks=run_release_checks(include_public_demo=bool(req.options.get("include_public_demo",False)),allow_live_verifier=bool(req.options.get("allow_live_verifier",False)),allow_missing_verifier=bool(req.options.get("allow_missing_verifier",True)))
 return _resp(req,route_result_from_artifacts(req.route,checks,truth_status=ApiTruthStatus.ADVISORY_ONLY,safety=ApiSafetyLevel.SAFE_ADVISORY))
def handle_e2e_testdrive(state,req):
 from mathgraph.e2e_testdrive import E2ETestDriveMode,run_e2e_testdrive
 mode=E2ETestDriveMode[str(req.options.get("mode","ADVISORY_ONLY")).upper().replace("-","_")]; r=run_e2e_testdrive(mode=mode,workspace_root=req.options.get("workspace_root"),allow_execution=bool(req.options.get("allow_execution",False)),allow_missing_verifier=bool(req.options.get("allow_missing_verifier",True)),include_fixture_suite=bool(req.options.get("include_fixture_suite",True)),accept_verified_fixtures_in_memory=bool(req.options.get("accept_verified_fixtures_in_memory",False)),include_verified_corpus=bool(req.options.get("include_verified_corpus",True)),accept_verified_corpus_in_memory=bool(req.options.get("accept_verified_corpus_in_memory",False)),include_lean_project_subset=bool(req.options.get("include_lean_project_subset",True)),accept_lean_project_subset_in_memory=bool(req.options.get("accept_lean_project_subset_in_memory",False)),include_mathlib_micro_subset=bool(req.options.get("include_mathlib_micro_subset",True)),accept_mathlib_micro_subset_in_memory=bool(req.options.get("accept_mathlib_micro_subset_in_memory",False))); truth=ApiTruthStatus.BOUNDARY_EVIDENCE_PRESENT if r.boundary_evidence else ApiTruthStatus.BOUNDARY_REQUIRED; return _resp(req,route_result_from_artifacts(req.route,[r],truth_status=truth,safety=ApiSafetyLevel.SAFE_REVIEW_REQUIRED))
def handle_submit(state,req):
 sem=build_semantic_intake_report(api_payload_to_objects(req.payload)); fw=build_formal_world_adapter_report(semantic_report_to_formal_world_inputs(sem)); ps=build_proof_system_integration_report(semantic_report_to_proof_system_inputs(sem)); cur=semantic_report_to_curriculum(sem); return _resp(req,route_result_from_artifacts(req.route,[sem,fw,ps,cur],truth_status=ApiTruthStatus.BOUNDARY_REQUIRED,safety=ApiSafetyLevel.SAFE_REVIEW_REQUIRED))
def _generic(req,artifacts): return _resp(req,route_result_from_artifacts(req.route,artifacts))
def _objects(req): return api_payload_to_objects(req.payload)
def handle_schedule(state,req):
 sem=build_semantic_intake_report(_objects(req)); return _generic(req,[semantic_report_to_curriculum(sem),*semantic_report_to_continuation_outputs(sem)])
def handle_project(state,req): return _generic(req,[{"projection_candidates":[],"advisory":True}])
def handle_explain(state,req): return _generic(req,[build_semantic_intake_report(_objects(req))])
def handle_process_memory(state,req): return _generic(req,[ProcessMemoryReport(make_process_memory_report_id("api",req.request_id))])
def handle_discovery_value(state,req):
 sig=DiscoveryValueSignal(content_id("api-signal",req.request_id),DiscoveryValueSignalKind.REUSE_VALUE,.1,source_object_kind=DiscoveryValueObjectKind.RAW_TASK); score=DiscoveryValueScore(content_id("api-score",req.request_id),req.request_id,DiscoveryValueObjectKind.RAW_TASK,signals=[sig]); score.recompute(); return _generic(req,[score])
def handle_review(state,req): return _resp(req,route_result_from_artifacts(req.route,[],truth_status=ApiTruthStatus.ADVISORY_ONLY,safety=ApiSafetyLevel.BLOCKED_MUTATION if state.read_only else ApiSafetyLevel.SAFE_REVIEW_REQUIRED))
def handle_structural_identity(state,req):
 from mathgraph.structural_identity import build_structural_identity_report
 return _generic(req,[build_structural_identity_report(_objects(req))])
def handle_habits(state,req): return _generic(req,[build_habit_formation_report(_objects(req))])
def handle_reasons(state,req): return _generic(req,[build_reason_compression_report(_objects(req))])
def handle_structures(state,req): return _generic(req,[build_structure_registry_report(_objects(req))])
def handle_roles(state,req): return _generic(req,[build_role_object_report(_objects(req))])
def handle_analogies(state,req): return _generic(req,[build_structural_analogy_report(_objects(req))])
_HANDLERS={ApiRoute.HEALTH:handle_health,ApiRoute.AUDIT:handle_audit,ApiRoute.QUERY:handle_query,ApiRoute.SUBMIT:handle_submit,ApiRoute.SEMANTIC_INTAKE:handle_semantic_intake,ApiRoute.FORMAL_WORLD_ADAPTERS:handle_formal_world_adapters,ApiRoute.PROOF_SYSTEM_INTEGRATION:handle_proof_system_integration,ApiRoute.VERIFIER_EXECUTION:handle_verifier_execution,ApiRoute.VERIFIER_FIXTURES:handle_verifier_fixtures,ApiRoute.VERIFIED_CORPUS:handle_verified_corpus,ApiRoute.LEAN_PROJECT_SUBSET:handle_lean_project_subset,ApiRoute.MATHLIB_MICRO_SUBSET:handle_mathlib_micro_subset,ApiRoute.MATHLIB_LOCAL_ALLOWLIST:handle_mathlib_local_allowlist,ApiRoute.MATHLIB_DECLARATION_DISCOVERY:handle_mathlib_declaration_discovery,ApiRoute.MATHLIB_MODULE_VERIFICATION:handle_mathlib_module_verification,ApiRoute.PROOF_LIBRARY_DEMO:handle_proof_library_demo,ApiRoute.PUBLIC_DEMO:handle_public_demo,ApiRoute.REAL_MATHLIB_REVISION_DEMO:handle_real_mathlib_revision_demo,ApiRoute.REAL_MATHLIB_DEMO:handle_real_mathlib_demo,ApiRoute.RELEASE_CHECK:handle_release_check,ApiRoute.E2E_TESTDRIVE:handle_e2e_testdrive,ApiRoute.SCHEDULE:handle_schedule,ApiRoute.PROJECT:handle_project,ApiRoute.EXPLAIN:handle_explain,ApiRoute.PROCESS_MEMORY:handle_process_memory,ApiRoute.DISCOVERY_VALUE:handle_discovery_value,ApiRoute.LAWBOOK_ACCEPTANCE_REVIEW:handle_review,ApiRoute.STRUCTURAL_IDENTITY:handle_structural_identity,ApiRoute.HABITS:handle_habits,ApiRoute.REASONS:handle_reasons,ApiRoute.STRUCTURES:handle_structures,ApiRoute.ROLES:handle_roles,ApiRoute.ANALOGIES:handle_analogies}
class MathGraphLocalClient:
 def __init__(self,state=None): self.state=state or ApiServiceState()
 def request(self,r):
  h=_HANDLERS.get(r.route)
  return h(self.state,r) if h else _resp(r,status=ApiResponseStatus.UNSUPPORTED_ROUTE,safety=ApiSafetyLevel.SAFE_READ_ONLY,message="unsupported route")
 def _call(self,route,payload=None,options=None): return self.request(ApiRequest(make_api_request_id(route.value,payload),route,payload=dict(payload or {}),options=dict(options or {})))
 def health(self): return self._call(ApiRoute.HEALTH)
 def audit(self,payload=None,options=None): return self._call(ApiRoute.AUDIT,payload,options)
def _method(route): return lambda self,payload,options=None:self._call(route,payload,options)
for _n,_r in [("query",ApiRoute.QUERY),("submit",ApiRoute.SUBMIT),("semantic_intake",ApiRoute.SEMANTIC_INTAKE),("formal_world_adapters",ApiRoute.FORMAL_WORLD_ADAPTERS),("proof_system_integration",ApiRoute.PROOF_SYSTEM_INTEGRATION),("verifier_execution",ApiRoute.VERIFIER_EXECUTION),("verifier_fixtures",ApiRoute.VERIFIER_FIXTURES),("verified_corpus",ApiRoute.VERIFIED_CORPUS),("lean_project_subset",ApiRoute.LEAN_PROJECT_SUBSET),("mathlib_micro_subset",ApiRoute.MATHLIB_MICRO_SUBSET),("mathlib_local_allowlist",ApiRoute.MATHLIB_LOCAL_ALLOWLIST),("mathlib_declaration_discovery",ApiRoute.MATHLIB_DECLARATION_DISCOVERY),("mathlib_module_verification",ApiRoute.MATHLIB_MODULE_VERIFICATION),("proof_library_demo",ApiRoute.PROOF_LIBRARY_DEMO),("public_demo",ApiRoute.PUBLIC_DEMO),("real_mathlib_revision_demo",ApiRoute.REAL_MATHLIB_REVISION_DEMO),("real_mathlib_demo",ApiRoute.REAL_MATHLIB_DEMO),("release_check",ApiRoute.RELEASE_CHECK),("e2e_testdrive",ApiRoute.E2E_TESTDRIVE),("schedule",ApiRoute.SCHEDULE),("project",ApiRoute.PROJECT),("explain",ApiRoute.EXPLAIN),("process_memory",ApiRoute.PROCESS_MEMORY),("discovery_value",ApiRoute.DISCOVERY_VALUE),("lawbook_acceptance_review",ApiRoute.LAWBOOK_ACCEPTANCE_REVIEW),("structural_identity",ApiRoute.STRUCTURAL_IDENTITY),("habits",ApiRoute.HABITS),("reasons",ApiRoute.REASONS),("structures",ApiRoute.STRUCTURES),("roles",ApiRoute.ROLES),("analogies",ApiRoute.ANALOGIES)]: setattr(MathGraphLocalClient,_n,_method(_r))
def audit_api_request(x): return [_f("CRITICAL","API_REQUEST_NON_ADVISORY","api request non-advisory",x.request_id)] if not x.advisory else []
def audit_api_route_result(x):
 out=[]
 if not x.advisory: out.append(_f("CRITICAL","API_RESULT_NON_ADVISORY","api result non-advisory",x.route_result_id))
 if x.verifier_boundary_crossed and not x.has_boundary_evidence(): out.append(_f("CRITICAL","API_BAD_BOUNDARY_EVIDENCE","route result boundary incomplete",x.route_result_id))
 if x.truth_status in {ApiTruthStatus.VERIFIED_PROOF,ApiTruthStatus.FINITE_COUNTERMODEL,ApiTruthStatus.NAMED_OBSTRUCTION} and not x.has_boundary_evidence(): out.append(_f("CRITICAL","API_TERMINAL_WITHOUT_BOUNDARY","route result terminal without boundary",x.route_result_id))
 return out
def audit_api_response(x):
 out=[]
 if not x.advisory: out.append(_f("CRITICAL","API_RESPONSE_NON_ADVISORY","api response non-advisory",x.response_id))
 if not x.boundary_policy: out.append(_f("CRITICAL","API_MISSING_BOUNDARY_POLICY","response missing boundary policy",x.response_id))
 if x.truth_status in {ApiTruthStatus.VERIFIED_PROOF,ApiTruthStatus.FINITE_COUNTERMODEL,ApiTruthStatus.NAMED_OBSTRUCTION} and not x.has_boundary_evidence(): out.append(_f("CRITICAL","API_TERMINAL_WITHOUT_BOUNDARY","response terminal without boundary",x.response_id))
 if x.status==ApiResponseStatus.OK and x.criticals: out.append(_f("CRITICAL","API_OK_WITH_CRITICALS","OK response has criticals",x.response_id))
 if x.result: out+=audit_api_route_result(x.result)
 return out
def audit_api_health(x):
 return [_f("CRITICAL","API_EXTERNAL_EXECUTION_DEFAULT","external execution enabled",x.service_name)] if x.external_execution_enabled else []
def audit_api_audit_result(x): return []
def audit_api_service_state(x): return [_f("CRITICAL","API_STATE_EXTERNAL_EXECUTION","external execution enabled", "state")] if x.external_execution_enabled else []
class MathGraphRequestHandler(BaseHTTPRequestHandler):
 client=MathGraphLocalClient()
 def _send(self,resp):
  data=resp.to_json().encode(); self.send_response(200); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(data))); self.end_headers(); self.wfile.write(data)
 def do_GET(self):
  self._send(self.client.health() if self.path=="/health" else self.client.request(ApiRequest(make_api_request_id(self.path),ApiRoute.UNKNOWN)))
 def do_POST(self):
  try:
   n=min(int(self.headers.get("Content-Length","0")),2_000_000); p=json.loads(self.rfile.read(n) or b"{}"); route=_path_route(self.path); self._send(self.client.request(ApiRequest(make_api_request_id(route.value,p),route,payload=p)))
  except Exception as e:
   self._send(ApiResponse(make_api_response_id("error"),None,ApiRoute.UNKNOWN,ApiResponseStatus.BAD_REQUEST,errors=(str(e),)))
 def log_message(self,*a): return
def _path_route(p): return {"/audit":ApiRoute.AUDIT,"/query":ApiRoute.QUERY,"/submit":ApiRoute.SUBMIT,"/semantic-intake":ApiRoute.SEMANTIC_INTAKE,"/formal-world-adapters":ApiRoute.FORMAL_WORLD_ADAPTERS,"/proof-system-integration":ApiRoute.PROOF_SYSTEM_INTEGRATION,"/verifier-execution":ApiRoute.VERIFIER_EXECUTION,"/verifier-fixtures":ApiRoute.VERIFIER_FIXTURES,"/verified-corpus":ApiRoute.VERIFIED_CORPUS,"/lean-project-subset":ApiRoute.LEAN_PROJECT_SUBSET,"/mathlib-micro-subset":ApiRoute.MATHLIB_MICRO_SUBSET,"/mathlib-local-allowlist":ApiRoute.MATHLIB_LOCAL_ALLOWLIST,"/mathlib-declaration-discovery":ApiRoute.MATHLIB_DECLARATION_DISCOVERY,"/proof-library-demo":ApiRoute.PROOF_LIBRARY_DEMO,"/public-demo":ApiRoute.PUBLIC_DEMO,"/real-mathlib-revision-demo":ApiRoute.REAL_MATHLIB_REVISION_DEMO,"/release-check":ApiRoute.RELEASE_CHECK,"/e2e-testdrive":ApiRoute.E2E_TESTDRIVE,"/schedule":ApiRoute.SCHEDULE,"/project":ApiRoute.PROJECT,"/explain":ApiRoute.EXPLAIN,"/process-memory":ApiRoute.PROCESS_MEMORY,"/discovery-value":ApiRoute.DISCOVERY_VALUE}.get(p,ApiRoute.UNKNOWN)
def serve_localhost(host="127.0.0.1",port=8765,state=None):
 if host not in {"127.0.0.1","localhost"}: raise ValueError("localhost binding required")
 MathGraphRequestHandler.client=MathGraphLocalClient(state)
 return ThreadingHTTPServer((host,port),MathGraphRequestHandler)
def _j(x): return json.dumps(x,sort_keys=True,separators=(",",":"),default=str)
def _f(sev,code,msg,obj): return {"severity":sev,"code":code,"message":msg,"object_id":obj}
