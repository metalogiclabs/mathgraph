"""Public demo, release checks, and optional real local Mathlib revision demos."""
from __future__ import annotations
import json,shutil,subprocess,sys
from dataclasses import MISSING,dataclass,field
from datetime import datetime,timezone
from enum import Enum
from pathlib import Path
from typing import Any,Mapping
from mathgraph.agent_biography import AgentExperience,AgentExperienceOutcome
from mathgraph.alchemy import AlchemicalPhase,AlchemicalStatus,AlchemicalTrace,make_alchemical_trace_id
from mathgraph.api_service import ApiRequest,ApiRoute,ApiSafetyLevel,ApiTruthStatus,make_api_request_id,route_result_from_artifacts
from mathgraph.certificates import TerminalForm
from mathgraph.discovery_value import DiscoveryValueObjectKind,DiscoveryValueScore,DiscoveryValueSignal,DiscoveryValueSignalKind
from mathgraph.e2e_testdrive import run_e2e_testdrive
from mathgraph.epistemic_status import build_epistemic_status_view
from mathgraph.hardening import build_hardening_report
from mathgraph.hashing import content_id
from mathgraph.mathlib_declaration_discovery import MathlibDiscoveryRequest,MathlibDiscoverySourceKind,mathlib_discovery_report_to_reference_graph,run_mathlib_declaration_discovery
from mathgraph.mathlib_local_allowlist import MathlibLocalFailureKind,mathlib_local_report_to_dependency_graph
from mathgraph.process_memory import ProcessContextItem,ProcessContextKind,ProcessContextRole,ProcessEpisodeRecord,ProcessEpisodeStatus,make_process_episode_id
from mathgraph.proof_library_demo import proof_library_demo_report_to_markdown,run_proof_library_demo
from mathgraph.version import get_version_info
def _enum(n,v): return Enum(n,{x:x for x in v.split()},type=str)
DemoReleaseKind=_enum("DemoReleaseKind","PUBLIC_SYNTHETIC_PROOF_LIBRARY REAL_LOCAL_MATHLIB_REVISION RELEASE_CHECK UNKNOWN")
DemoReleaseStatus=_enum("DemoReleaseStatus","NOT_RUN COMPLETED COMPLETED_WITH_WARNINGS SKIPPED_ENVIRONMENT FAILED ERROR UNKNOWN")
DemoReleaseTruthStatus=_enum("DemoReleaseTruthStatus","ADVISORY_ONLY BOUNDARY_EVIDENCE_PRESENT KNOWN_SKIP_AVAILABLE SKIPPED_NO_VERIFIER SKIPPED_NO_ENVIRONMENT UNKNOWN")
DemoReleaseCheckKind=_enum("DemoReleaseCheckKind","IMPORTS FOCUSED_TESTS PUBLIC_TERMS CLI_HELP PROOF_LIBRARY_DEMO E2E_TESTDRIVE HARDENING ROADMAP_ALIGNMENT DOCS_PRESENT EXAMPLES_PRESENT NOTEBOOK_PRESENT ARTIFACT_CONVENTIONS BOUNDARY_LANGUAGE REAL_MATHLIB_ENVIRONMENT UNKNOWN")
DemoReleaseCheckStatus=_enum("DemoReleaseCheckStatus","PASS WARN FAIL SKIP UNKNOWN")
RealMathlibRevisionStatus=_enum("RealMathlibRevisionStatus","READY MISSING_PROJECT_ROOT MISSING_GIT MISSING_REVISION REVISION_MISMATCH_WARNING MISSING_TOOLCHAIN TOOLCHAIN_MISMATCH_WARNING MISSING_MATHLIB_MARKER SKIPPED UNKNOWN")
def _serial(cls,enums=()):
 def td(self):
  d=dict(self.__dict__)
  for k in enums:
   if isinstance(d.get(k),Enum): d[k]=d[k].value
  for k,v in list(d.items()):
   if isinstance(v,tuple): d[k]=list(v)
   elif hasattr(v,"to_dict"): d[k]=v.to_dict()
   elif isinstance(v,list): d[k]=[x.to_dict() if hasattr(x,"to_dict") else x for x in v]
  return d
 @classmethod
 def fd(c,d):
  vals=[]
  for f in c.__dataclass_fields__.values():
   v=d[f.name] if f.name in d else f.default if f.default is not MISSING else f.default_factory() if f.default_factory is not MISSING else None
   if f.name in enums and v is not None and not isinstance(v,Enum): v=globals()[str(f.type)](str(v))
   if getattr(f.type,"__origin__",None) is tuple and v is not None: v=tuple(v)
   vals.append(v)
  return c(*vals)
 cls.to_dict=td; cls.from_dict=fd; cls.to_json=lambda self:_j(self.to_dict()); cls.from_json=classmethod(lambda c,t:c.from_dict(json.loads(t))); return cls
@_serial
@dataclass
class PublicDemoConfig:
 demo_id:str; name:str; version:str="0.1"; demo_kind:DemoReleaseKind=DemoReleaseKind.PUBLIC_SYNTHETIC_PROOF_LIBRARY; use_synthetic:bool=True; run_proof_library_demo:bool=True; run_e2e:bool=True; run_hardening:bool=True; run_roadmap_alignment:bool=True; allow_execution_default:bool=False; accept_verified_entries_in_memory:bool=True; metadata:dict[str,Any]=field(default_factory=dict); advisory:bool=True
 def write_json(self,p): _w(p,self.to_json())
 @classmethod
 def read_json(c,p): return c.from_json(Path(p).read_text())
@_serial
@dataclass
class RealMathlibRevisionDemoConfig:
 demo_id:str; name:str; version:str="0.1"; demo_kind:DemoReleaseKind=DemoReleaseKind.REAL_LOCAL_MATHLIB_REVISION; project_root:str|None=None; expected_revision:str|None=None; expected_lean_toolchain:str|None=None; module_files:list[dict[str,Any]]=field(default_factory=list); selection_policy:dict[str,Any]=field(default_factory=dict); build_manifest:bool=True; run_allowlist_ingestion:bool=False; accept_verified_entries_in_memory:bool=False; allow_execution_default:bool=False; metadata:dict[str,Any]=field(default_factory=dict); advisory:bool=True
 def write_json(self,p): _w(p,self.to_json())
 @classmethod
 def read_json(c,p): return c.from_json(Path(p).read_text())
@_serial
@dataclass
class ReleaseCheckResult:
 check_id:str; check_kind:DemoReleaseCheckKind; status:DemoReleaseCheckStatus; name:str; summary:dict[str,Any]=field(default_factory=dict); artifact_paths:tuple[str,...]=(); warnings:tuple[str,...]=(); criticals:tuple[str,...]=(); metadata:dict[str,Any]=field(default_factory=dict); advisory:bool=True
 def ok(self): return self.status in {DemoReleaseCheckStatus.PASS,DemoReleaseCheckStatus.WARN,DemoReleaseCheckStatus.SKIP} and not self.criticals
@dataclass
class PublicDemoReport:
 report_id:str; demo_id:str; config:PublicDemoConfig|None=None; proof_library_demo_report:Any|None=None; e2e_report:Any|None=None; hardening_report:Any|None=None; roadmap_alignment_report:Any|None=None; release_checks:list[ReleaseCheckResult]=field(default_factory=list); created_at:str=field(default_factory=lambda:_now()); status:DemoReleaseStatus=DemoReleaseStatus.UNKNOWN; truth_status:DemoReleaseTruthStatus=DemoReleaseTruthStatus.UNKNOWN; summary:dict[str,Any]=field(default_factory=dict); warnings:tuple[str,...]=(); criticals:tuple[str,...]=(); metadata:dict[str,Any]=field(default_factory=dict); advisory:bool=True
 def check_count(self): return len(self.release_checks)
 def pass_count(self): return sum(x.status==DemoReleaseCheckStatus.PASS for x in self.release_checks)
 def warning_count(self): return len(self.warnings)+sum(x.status==DemoReleaseCheckStatus.WARN for x in self.release_checks)
 def critical_count(self): return len(self.criticals)+sum(len(x.criticals) for x in self.release_checks)
 def boundary_evidence_count(self): return self.proof_library_demo_report.boundary_evidence_count() if self.proof_library_demo_report else 0
 def known_skip_count(self): return self.proof_library_demo_report.known_skip_count() if self.proof_library_demo_report else 0
 def summarize(self):
  p=self.proof_library_demo_report.summary if self.proof_library_demo_report else {}
  version=get_version_info(); self.summary={"version":version["version"],"release_stage":version["release_stage"],"check_total":len(self.release_checks),"pass_total":self.pass_count(),"warning_total":self.warning_count(),"critical_total":self.critical_count(),"module_total":p.get("module_total",0),"declaration_total":p.get("declaration_total",0),"selected_total":p.get("selected_total",0),"verified_total":p.get("downstream_verified_total",0),"known_skip_total":self.known_skip_count(),"boundary_evidence_total":self.boundary_evidence_count(),"hardening_critical_total":self.hardening_report.critical_count() if self.hardening_report else 0,"alignment_critical_total":self.roadmap_alignment_report.critical_count() if self.roadmap_alignment_report else 0}; return self.summary
 def ok(self): return self.critical_count()==0 and self.status not in {DemoReleaseStatus.FAILED,DemoReleaseStatus.ERROR}
 def to_dict(self): return {**self.__dict__,"config":self.config.to_dict() if self.config else None,"proof_library_demo_report":self.proof_library_demo_report.to_dict() if self.proof_library_demo_report else None,"e2e_report":self.e2e_report.to_dict() if self.e2e_report else None,"hardening_report":self.hardening_report.to_dict() if self.hardening_report else None,"roadmap_alignment_report":self.roadmap_alignment_report.to_dict() if self.roadmap_alignment_report else None,"release_checks":[x.to_dict() for x in self.release_checks],"status":self.status.value,"truth_status":self.truth_status.value,"warnings":list(self.warnings),"criticals":list(self.criticals)}
 @classmethod
 def from_dict(c,d):
  from mathgraph.e2e_testdrive import E2ETestDriveReport
  from mathgraph.hardening import HardeningReport
  from mathgraph.proof_library_demo import ProofLibraryDemoReport
  from mathgraph.roadmap_alignment import RoadmapAlignmentReport,RoadmapAlignmentFinding
  a=d.get("roadmap_alignment_report")
  align=RoadmapAlignmentReport(str(a["checked_at"]),dict(a["summary"]),[RoadmapAlignmentFinding(**x) for x in a.get("findings",())]) if a else None
  return c(str(d["report_id"]),str(d["demo_id"]),PublicDemoConfig.from_dict(d["config"]) if d.get("config") else None,ProofLibraryDemoReport.from_dict(d["proof_library_demo_report"]) if d.get("proof_library_demo_report") else None,E2ETestDriveReport.from_dict(d["e2e_report"]) if d.get("e2e_report") else None,HardeningReport.from_dict(d["hardening_report"]) if d.get("hardening_report") else None,align,[ReleaseCheckResult.from_dict(x) for x in d.get("release_checks",())],str(d.get("created_at",_now())),DemoReleaseStatus(str(d.get("status","UNKNOWN"))),DemoReleaseTruthStatus(str(d.get("truth_status","UNKNOWN"))),dict(d.get("summary",{})),tuple(d.get("warnings",())),tuple(d.get("criticals",())),dict(d.get("metadata",{})),bool(d.get("advisory",True)))
 def to_json(self): return _j(self.to_dict())
 @classmethod
 def from_json(c,t): return c.from_dict(json.loads(t))
 def write_json(self,p): _w(p,self.to_json())
 @classmethod
 def read_json(c,p): return c.from_json(Path(p).read_text())
 def write_jsonl(self,p): _w(p,self.to_json()+"\n")
 @classmethod
 def read_jsonl(c,p): return [c.from_json(x) for x in Path(p).read_text().splitlines() if x.strip()]
@dataclass
class RealMathlibRevisionReport:
 report_id:str; demo_id:str; config:RealMathlibRevisionDemoConfig|None=None; project_root:str|None=None; detected_revision:str|None=None; detected_lean_toolchain:str|None=None; revision_status:RealMathlibRevisionStatus=RealMathlibRevisionStatus.UNKNOWN; discovery_report:Any|None=None; generated_manifest:Any|None=None; allowlist_ingestion_report:Any|None=None; created_at:str=field(default_factory=lambda:_now()); status:DemoReleaseStatus=DemoReleaseStatus.UNKNOWN; truth_status:DemoReleaseTruthStatus=DemoReleaseTruthStatus.UNKNOWN; summary:dict[str,Any]=field(default_factory=dict); warnings:tuple[str,...]=(); criticals:tuple[str,...]=(); metadata:dict[str,Any]=field(default_factory=dict); advisory:bool=True
 def module_count(self): return self.discovery_report.module_count() if self.discovery_report else 0
 def declaration_count(self): return self.discovery_report.declaration_count() if self.discovery_report else 0
 def selected_count(self): return self.discovery_report.selected_declaration_count() if self.discovery_report else 0
 def verified_count(self): return self.allowlist_ingestion_report.verified_entry_count() if self.allowlist_ingestion_report else 0
 def known_skip_count(self): return self.allowlist_ingestion_report.lawbook_replay_summary.get("known_skip_total",0) if self.allowlist_ingestion_report else 0
 def dependency_edge_count(self): return self.allowlist_ingestion_report.dependency_edge_count() if self.allowlist_ingestion_report else len(mathlib_discovery_report_to_reference_graph(self.discovery_report).get("edges",())) if self.discovery_report else 0
 def summarize(self): self.summary={"module_total":self.module_count(),"declaration_total":self.declaration_count(),"selected_total":self.selected_count(),"verified_total":self.verified_count(),"known_skip_total":self.known_skip_count(),"dependency_edge_total":self.dependency_edge_count(),"warning_total":len(self.warnings),"critical_total":len(self.criticals)}; return self.summary
 def ok(self): return self.critical_count()==0 and self.status not in {DemoReleaseStatus.FAILED,DemoReleaseStatus.ERROR}
 def critical_count(self): return len(self.criticals)
 def to_dict(self): return {**self.__dict__,"config":self.config.to_dict() if self.config else None,"revision_status":self.revision_status.value,"discovery_report":self.discovery_report.to_dict() if self.discovery_report else None,"generated_manifest":self.generated_manifest.to_dict() if self.generated_manifest else None,"allowlist_ingestion_report":self.allowlist_ingestion_report.to_dict() if self.allowlist_ingestion_report else None,"status":self.status.value,"truth_status":self.truth_status.value,"warnings":list(self.warnings),"criticals":list(self.criticals)}
 @classmethod
 def from_dict(c,d):
  from mathgraph.mathlib_declaration_discovery import MathlibDeclarationDiscoveryReport
  from mathgraph.mathlib_local_allowlist import MathlibLocalAllowlistManifest,MathlibLocalIngestionReport
  return c(str(d["report_id"]),str(d["demo_id"]),RealMathlibRevisionDemoConfig.from_dict(d["config"]) if d.get("config") else None,d.get("project_root"),d.get("detected_revision"),d.get("detected_lean_toolchain"),RealMathlibRevisionStatus(str(d.get("revision_status","UNKNOWN"))),MathlibDeclarationDiscoveryReport.from_dict(d["discovery_report"]) if d.get("discovery_report") else None,MathlibLocalAllowlistManifest.from_dict(d["generated_manifest"]) if d.get("generated_manifest") else None,MathlibLocalIngestionReport.from_dict(d["allowlist_ingestion_report"]) if d.get("allowlist_ingestion_report") else None,str(d.get("created_at",_now())),DemoReleaseStatus(str(d.get("status","UNKNOWN"))),DemoReleaseTruthStatus(str(d.get("truth_status","UNKNOWN"))),dict(d.get("summary",{})),tuple(d.get("warnings",())),tuple(d.get("criticals",())),dict(d.get("metadata",{})),bool(d.get("advisory",True)))
 def to_json(self): return _j(self.to_dict())
 @classmethod
 def from_json(c,t): return c.from_dict(json.loads(t))
 def write_json(self,p): _w(p,self.to_json())
 @classmethod
 def read_json(c,p): return c.from_json(Path(p).read_text())
 def write_jsonl(self,p): _w(p,self.to_json()+"\n")
 @classmethod
 def read_jsonl(c,p): return [c.from_json(x) for x in Path(p).read_text().splitlines() if x.strip()]
for _c,_e in [(PublicDemoConfig,("demo_kind",)),(RealMathlibRevisionDemoConfig,("demo_kind",)),(ReleaseCheckResult,("check_kind","status"))]: _serial(_c,_e)
def make_public_demo_config_id(*x): return content_id("public-demo-config",x)
def make_real_mathlib_revision_demo_config_id(*x): return content_id("real-mathlib-revision-demo-config",x)
def make_release_check_id(*x): return content_id("release-check",x)
def make_public_demo_report_id(*x): return content_id("public-demo-report",x)
def make_real_mathlib_revision_report_id(*x): return content_id("real-mathlib-revision-report",x)
def default_public_demo_config_dict(): return {"demo_id":"mathgraph-public-demo","name":"MathGraph Public Demo","version":"0.1","demo_kind":"PUBLIC_SYNTHETIC_PROOF_LIBRARY","use_synthetic":True,"run_proof_library_demo":True,"run_e2e":True,"run_hardening":True,"run_roadmap_alignment":True,"allow_execution_default":False,"accept_verified_entries_in_memory":True,"metadata":{"description":"Public repeatable demo over the synthetic Mathlib-style proof-library pack."}}
def default_real_mathlib_revision_demo_config_dict(): return {"demo_id":"real-mathlib-revision-demo-example","name":"Real Local Mathlib Revision Demo Example","version":"0.1","demo_kind":"REAL_LOCAL_MATHLIB_REVISION","project_root":"/path/to/local/mathlib","expected_revision":None,"expected_lean_toolchain":None,"module_files":[{"path":"Mathlib/Data/Nat/Basic.lean","module_name":"Mathlib.Data.Nat.Basic","max_declarations":5,"include_kinds":["theorem","lemma"],"name_contains":[],"exclude_name_contains":["deprecated","aux"]}],"selection_policy":{"max_total_declarations":5,"prefer_kinds":["theorem","lemma"]},"build_manifest":True,"run_allowlist_ingestion":False,"accept_verified_entries_in_memory":False,"allow_execution_default":False,"metadata":{"description":"Template only. Requires an already-working local Mathlib checkout. No downloads are performed."}}
def ensure_default_demo_release_configs(root,*,overwrite=False):
 root=Path(root); pub=root/"public_demo"/"public_demo_config.json"; real=root/"real_mathlib_revision_demo"/"real_mathlib_revision_demo_config.example.json"; curated=root/"real_mathlib_revision_demo"/"curated_manifest.example.json"
 for p,d in ((pub,default_public_demo_config_dict()),(real,default_real_mathlib_revision_demo_config_dict()),(curated,{"manifest_id":"curated-real-mathlib-template","advisory":True,"files":[],"metadata":{"note":"Template only; no verified theorem names are claimed."}})):
  if overwrite or not p.exists(): _w(p,json.dumps(d,indent=2)+"\n")
 return pub,real,curated
def load_public_demo_config(path): return PublicDemoConfig.from_dict(json.loads(Path(path).read_text()))
def load_real_mathlib_revision_demo_config(path): return RealMathlibRevisionDemoConfig.from_dict(json.loads(Path(path).read_text()))
def _check(kind,status,name,summary=None): return ReleaseCheckResult(make_release_check_id(kind.value,name),kind,status,name,dict(summary or {}))
def run_public_demo(config=None,*,out_dir=None,allow_execution=False,allow_missing_verifier=True,accept_verified_entries_in_memory=None,timeout_sec=20.0):
 c=PublicDemoConfig.from_dict(default_public_demo_config_dict()) if config is None else load_public_demo_config(config) if isinstance(config,(str,Path)) else PublicDemoConfig.from_dict(dict(config)) if isinstance(config,Mapping) else config; accept=c.accept_verified_entries_in_memory if accept_verified_entries_in_memory is None else accept_verified_entries_in_memory
 p=run_proof_library_demo(run_allowlist_ingestion=True,allow_execution=allow_execution,allow_missing_verifier=allow_missing_verifier,accept_verified_entries_in_memory=accept,timeout_sec=timeout_sec) if c.run_proof_library_demo else None
 e=run_e2e_testdrive(include_hardening=False) if c.run_e2e else None; h=build_hardening_report() if c.run_hardening else None
 from mathgraph.roadmap_alignment import check_roadmap_alignment
 a=check_roadmap_alignment(proof_library_demo_reports=[p] if p else []) if c.run_roadmap_alignment else None
 root=Path(__file__).resolve().parents[1]; checks=[_check(DemoReleaseCheckKind.IMPORTS,DemoReleaseCheckStatus.PASS,"imports"),_check(DemoReleaseCheckKind.PROOF_LIBRARY_DEMO,DemoReleaseCheckStatus.PASS if p and p.ok() else DemoReleaseCheckStatus.FAIL,"proof library demo"),_check(DemoReleaseCheckKind.E2E_TESTDRIVE,DemoReleaseCheckStatus.PASS if not e or e.ok() else DemoReleaseCheckStatus.FAIL,"e2e"),_check(DemoReleaseCheckKind.HARDENING,DemoReleaseCheckStatus.PASS if not h or h.ok() else DemoReleaseCheckStatus.FAIL,"hardening"),_check(DemoReleaseCheckKind.ROADMAP_ALIGNMENT,DemoReleaseCheckStatus.PASS if not a or not a.critical_count() else DemoReleaseCheckStatus.FAIL,"roadmap"),_check(DemoReleaseCheckKind.DOCS_PRESENT,DemoReleaseCheckStatus.PASS if (root/"docs"/"public_demo.md").exists() else DemoReleaseCheckStatus.WARN,"docs"),_check(DemoReleaseCheckKind.NOTEBOOK_PRESENT,DemoReleaseCheckStatus.PASS if (root/"notebooks"/"mathgraph_public_demo.py").exists() else DemoReleaseCheckStatus.WARN,"notebook")]
 truth=DemoReleaseTruthStatus.KNOWN_SKIP_AVAILABLE if p and p.known_skip_count() else DemoReleaseTruthStatus.BOUNDARY_EVIDENCE_PRESENT if p and p.downstream_verified_count() else DemoReleaseTruthStatus.ADVISORY_ONLY
 rep=PublicDemoReport(make_public_demo_report_id(c.demo_id,allow_execution,accept),c.demo_id,c,p,e,h,a,checks,status=DemoReleaseStatus.COMPLETED,truth_status=truth); rep.summarize()
 if out_dir: write_public_demo_artifacts(rep,out_dir)
 return rep
def detect_real_mathlib_revision_environment(config):
 c=config if isinstance(config,RealMathlibRevisionDemoConfig) else load_real_mathlib_revision_demo_config(config) if isinstance(config,(str,Path)) else RealMathlibRevisionDemoConfig.from_dict(dict(config)); root=Path(c.project_root or ""); meta={}; warns=[]; crit=[]; markers=[x for x in ("Mathlib","lakefile.lean","lakefile.toml","lake-manifest.json","lean-toolchain") if root and (root/x).exists()]
 if not root.exists(): return RealMathlibRevisionStatus.MISSING_PROJECT_ROOT,{"project_root":str(root)},("project root missing",),()
 git=shutil.which("git")
 if not git or not (root/".git").exists(): status=RealMathlibRevisionStatus.MISSING_GIT; warns.append("git metadata missing"); rev=None
 else:
  rev=subprocess.run([git,"-C",str(root),"rev-parse","HEAD"],capture_output=True,text=True,timeout=10).stdout.strip() or None; status=RealMathlibRevisionStatus.READY
 meta["detected_revision"]=rev; tc=(root/"lean-toolchain").read_text().strip() if (root/"lean-toolchain").exists() else None; meta["detected_lean_toolchain"]=tc; meta["markers"]=markers
 if not markers: status=RealMathlibRevisionStatus.MISSING_MATHLIB_MARKER; warns.append("mathlib marker missing")
 elif c.expected_revision and rev and c.expected_revision!=rev: status=RealMathlibRevisionStatus.REVISION_MISMATCH_WARNING; warns.append("revision mismatch")
 elif c.expected_revision and not rev: status=RealMathlibRevisionStatus.MISSING_REVISION; warns.append("revision missing")
 elif c.expected_lean_toolchain and not tc: status=RealMathlibRevisionStatus.MISSING_TOOLCHAIN; warns.append("toolchain missing")
 elif c.expected_lean_toolchain and tc and c.expected_lean_toolchain!=tc: status=RealMathlibRevisionStatus.TOOLCHAIN_MISMATCH_WARNING; warns.append("toolchain mismatch")
 return status,meta,tuple(warns),tuple(crit)
def run_real_mathlib_revision_demo(config,*,out_dir=None,project_root=None,allow_execution=False,allow_missing_verifier=True,run_allowlist_ingestion=None,accept_verified_entries_in_memory=None,timeout_sec=20.0,require_mathlib_marker=True):
 c=load_real_mathlib_revision_demo_config(config) if isinstance(config,(str,Path)) else RealMathlibRevisionDemoConfig.from_dict(dict(config)) if isinstance(config,Mapping) else config
 if project_root:c.project_root=str(Path(project_root).resolve())
 rs,meta,warns,crit=detect_real_mathlib_revision_environment(c); ready=rs in {RealMathlibRevisionStatus.READY,RealMathlibRevisionStatus.REVISION_MISMATCH_WARNING,RealMathlibRevisionStatus.TOOLCHAIN_MISMATCH_WARNING}; dr=None
 if ready:
  req=MathlibDiscoveryRequest(f"{c.demo_id}-discovery",f"{c.name} discovery",source_kind=MathlibDiscoverySourceKind.LOCAL_MATHLIB_PROJECT,project_root=c.project_root,module_files=c.module_files,selection_policy=c.selection_policy)
  dr=run_mathlib_declaration_discovery(req,build_manifest=c.build_manifest,run_allowlist_ingestion=c.run_allowlist_ingestion if run_allowlist_ingestion is None else run_allowlist_ingestion,allow_execution=allow_execution,allow_missing_verifier=allow_missing_verifier,timeout_sec=timeout_sec,accept_verified_entries_in_memory=c.accept_verified_entries_in_memory if accept_verified_entries_in_memory is None else accept_verified_entries_in_memory,require_mathlib_marker=require_mathlib_marker)
 ar=dr.allowlist_ingestion_report if dr else None; truth=DemoReleaseTruthStatus.KNOWN_SKIP_AVAILABLE if ar and ar.lawbook_replay_summary.get("known_skip_total",0) else DemoReleaseTruthStatus.BOUNDARY_EVIDENCE_PRESENT if ar and ar.verified_entry_count() else DemoReleaseTruthStatus.SKIPPED_NO_ENVIRONMENT if not ready else DemoReleaseTruthStatus.ADVISORY_ONLY; status=DemoReleaseStatus.COMPLETED if ready else DemoReleaseStatus.SKIPPED_ENVIRONMENT
 rep=RealMathlibRevisionReport(make_real_mathlib_revision_report_id(c.demo_id,c.project_root,rs.value),c.demo_id,c,c.project_root,meta.get("detected_revision"),meta.get("detected_lean_toolchain"),rs,dr,dr.generated_manifest if dr else None,ar,status=status,truth_status=truth,warnings=warns,criticals=crit,metadata=meta); rep.summarize()
 if out_dir: write_real_mathlib_revision_artifacts(rep,out_dir)
 return rep
def public_demo_report_to_markdown(r):
 s=r.summarize(); p=r.proof_library_demo_report; mode="known-skip replay" if r.known_skip_count() else "verifier-bound" if r.boundary_evidence_count() else "advisory"; cards=public_demo_epistemic_statuses(r); verification=cards[0]["verification"]["status"] if cards else "UNKNOWN"
 return "\n".join(["# MathGraph Public Demo Report","", "## What This Demonstrates","A repeatable synthetic proof-library flow: discovery, allowlist generation, optional verifier-bound checking, and optional in-memory Lawbook replay.","", "## Boundary Discipline","Demo success, reports, graphs, and release checks are advisory. Only explicit verifier/importer/finite-validator/chain-audit evidence promotes truth.","",f"- Mode: {mode}",f"- Truth status: {r.truth_status.value}","", "## Epistemic Status","MathGraph keeps verification, human digestion, statement fidelity, and generalization as independent axes. Digestion, statement fidelity, and generalization do not promote truth.","","| axis | status | truth authority |","| --- | --- | --- |",f"| Verification | {verification} | {'verifier-bound' if cards else 'none'} |","| Human digest | UNKNOWN | none |","| Statement fidelity | UNKNOWN | none |","| Generalization | UNKNOWN | none |",f"| Verified claim cards | {len(cards)} | inherited from each claim's verifier boundary only |","", "## Summary", "| metric | value |","| --- | --- |",f"| declarations | {s['declaration_total']} |",f"| selected | {s['selected_total']} |",f"| verified | {s['verified_total']} |",f"| boundary evidence | {s['boundary_evidence_total']} |",f"| known skips | {s['known_skip_total']} |","", "## Stage Results"]+[f"- {x.name}: {x.status.value}" for x in r.release_checks]+["", "## Proof-Library Demo Summary",f"- Modules: {p.summary.get('module_total',0) if p else 0}",f"- Dependency edges: {p.summary.get('dependency_edge_total',0) if p else 0}","", "## E2E/Hardening/Alignment Summary",f"- E2E present: {bool(r.e2e_report)}",f"- Hardening criticals: {s['hardening_critical_total']}",f"- Alignment criticals: {s['alignment_critical_total']}","", "## What Crossed The Verifier Boundary",f"- Evidence count: {s['boundary_evidence_total']}","", "## What Stayed Advisory","- Discovery, generated manifests, dependency graphs, reports, release checks, digestion, statement-fidelity assessments, and generalization candidates.","", "## Generated Artifacts","- JSON and Markdown artifacts are emitted when `--out-dir` is supplied.","", "## How To Reproduce","`python scripts/run_public_demo.py --allow-execution --allow-missing-verifier --accept-verified-entries-in-memory`","", "## Next Steps","Use the real local revision template only with an already-working explicit local checkout."])+"\n"
def real_mathlib_revision_report_to_markdown(r):
 c=r.config; s=r.summarize(); return "\n".join(["# Real Local Mathlib Revision Demo Report","",f"- Environment status: {r.revision_status.value}",f"- Project root: {r.project_root}",f"- Detected revision: {r.detected_revision}",f"- Expected revision: {c.expected_revision if c else None}",f"- Detected toolchain: {r.detected_lean_toolchain}",f"- Expected toolchain: {c.expected_lean_toolchain if c else None}","", "## Selected Modules",*[f"- {x.get('module_name')}" for x in (c.module_files if c else [])],"", "## Discovered Declarations",f"- Total: {s['declaration_total']}",f"- Selected: {s['selected_total']}","", "## Generated Manifest Summary",f"- Files: {len(r.generated_manifest.files) if r.generated_manifest else 0}","", "## Downstream Verification Summary",f"- Verified: {s['verified_total']}",f"- Known skips: {s['known_skip_total']}","", "## Boundary Discipline","Environment checks, discovery, manifests, and reports are advisory; only verifier/importer/finite-validator/chain-audit evidence promotes truth.","", "## Missing Environment Instructions","Supply an already-working local Mathlib checkout path; no downloads or package-manager commands are performed.","", "## Next Steps","Pin a revision/toolchain expectation, inspect selected declarations, then opt into verification explicitly."])+"\n"
def write_public_demo_artifacts(r,out):
 out=Path(out); (out/"logs").mkdir(parents=True,exist_ok=True); (out/"raw").mkdir(parents=True,exist_ok=True); paths={"report":out/"public_demo_report.json","markdown":out/"public_demo_report.md","proof_demo":out/"proof_library_demo_report.json","proof_markdown":out/"proof_library_demo_report.md","graph":out/"dependency_graph.json","checks":out/"release_checks.jsonl","api_response":out/"api_response.json"}; r.write_json(paths["report"]); _w(paths["markdown"],public_demo_report_to_markdown(r)); _w(paths["api_response"],public_demo_report_to_api_response(r).to_json())
 if r.proof_library_demo_report:r.proof_library_demo_report.write_json(paths["proof_demo"]); _w(paths["proof_markdown"],proof_library_demo_report_to_markdown(r.proof_library_demo_report)); _w(paths["graph"],_j(r.proof_library_demo_report.dependency_graph))
 _w(paths["checks"],"".join(x.to_json()+"\n" for x in r.release_checks)); return {k:str(v) for k,v in paths.items() if v.exists()}
def concise_public_demo_summary(r,artifact_paths=None):
 s=r.summarize(); p=dict(artifact_paths or {}); return "\n".join(["MathGraph Public Demo",f"status: {r.status.value}",f"truth_status: {r.truth_status.value}",f"declarations: {s['declaration_total']}",f"selected: {s['selected_total']}",f"verified: {s['verified_total']}",f"known_skips: {s['known_skip_total']}",f"boundary_evidence: {s['boundary_evidence_total']}",f"criticals: {s['critical_total']}",f"warnings: {s['warning_total']}",f"markdown: {p.get('markdown','')}",f"json: {p.get('report','')}"])+"\n"
def write_real_mathlib_revision_artifacts(r,out):
 out=Path(out); paths={"report":out/"real_mathlib_revision_report.json","markdown":out/"real_mathlib_revision_report.md","discovery":out/"discovery_report.json","manifest":out/"generated_allowlist_manifest.json","ingestion":out/"allowlist_ingestion_report.json","graph":out/"reference_graph.json"}; r.write_json(paths["report"]); _w(paths["markdown"],real_mathlib_revision_report_to_markdown(r))
 if r.discovery_report:r.discovery_report.write_json(paths["discovery"]); _w(paths["graph"],_j(mathlib_discovery_report_to_reference_graph(r.discovery_report)))
 if r.generated_manifest:r.generated_manifest.write_json(paths["manifest"])
 if r.allowlist_ingestion_report:r.allowlist_ingestion_report.write_json(paths["ingestion"])
 return {k:str(v) for k,v in paths.items() if v.exists()}
def _verified_entries_from_demo(r): return [e for e in (r.proof_library_demo_report.allowlist_ingestion_report.entries if r.proof_library_demo_report and r.proof_library_demo_report.allowlist_ingestion_report else []) if e.has_boundary_evidence()]
def public_demo_epistemic_statuses(r): return [build_epistemic_status_view(e) for e in _verified_entries_from_demo(r)]
def public_demo_report_to_api_response(r):
 resp=_api(r,"public-demo",ApiRoute.PUBLIC_DEMO,r.known_skip_count(),r.boundary_evidence_count())
 if resp.result: resp.result.summary["epistemic_status_cards"]=public_demo_epistemic_statuses(r); resp.result.summary["epistemic_axis_policy"]="Only verification may carry truth authority; digestion, statement fidelity, and generalization remain independently qualified."
 return resp
def real_mathlib_revision_report_to_api_response(r): return _api(r,"real-mathlib-revision",ApiRoute.REAL_MATHLIB_REVISION_DEMO,r.known_skip_count(),r.verified_count())
def _api(r,prefix,route,known,verified):
 from mathgraph.api_service import _resp
 req=ApiRequest(make_api_request_id(prefix,r.report_id),route); truth=ApiTruthStatus.KNOWN_SKIP_AVAILABLE if known else ApiTruthStatus.BOUNDARY_EVIDENCE_PRESENT if verified else ApiTruthStatus.ADVISORY_ONLY; return _resp(req,route_result_from_artifacts(route,[r],truth_status=truth,safety=ApiSafetyLevel.SAFE_REVIEW_REQUIRED))
def public_demo_report_to_process_episodes(r): return _episodes(r.proof_library_demo_report.discovery_report.declarations if r.proof_library_demo_report else [],{e.name for e in _verified_entries_from_demo(r)},"public-demo")
def public_demo_report_to_discovery_value_scores(r): return _scores(r.proof_library_demo_report.discovery_report.declarations if r.proof_library_demo_report else [],{e.name for e in _verified_entries_from_demo(r)},"public-demo")
def public_demo_report_to_structural_identity_objects(r): return _objects(r.proof_library_demo_report.discovery_report.declarations if r.proof_library_demo_report else [],{e.name for e in _verified_entries_from_demo(r)})
def public_demo_report_to_route_telemetry_events(r): return _telemetry(r.proof_library_demo_report.discovery_report.declarations if r.proof_library_demo_report else [],{e.name for e in _verified_entries_from_demo(r)},"public_demo")
def public_demo_report_to_alchemical_trace(r): return _trace("public-demo",r.report_id,bool(_verified_entries_from_demo(r)))
def public_demo_report_to_agent_experiences(r): return _experiences(r.proof_library_demo_report.discovery_report.declarations if r.proof_library_demo_report else [],{e.name for e in _verified_entries_from_demo(r)},"public-demo")
def _real_verified(r): return [e for e in (r.allowlist_ingestion_report.entries if r.allowlist_ingestion_report else []) if e.has_boundary_evidence()]
def real_mathlib_revision_report_to_process_episodes(r): return _episodes(r.discovery_report.declarations if r.discovery_report else [],{e.name for e in _real_verified(r)},"real-mathlib")
def real_mathlib_revision_report_to_discovery_value_scores(r): return _scores(r.discovery_report.declarations if r.discovery_report else [],{e.name for e in _real_verified(r)},"real-mathlib")
def real_mathlib_revision_report_to_structural_identity_objects(r): return _objects(r.discovery_report.declarations if r.discovery_report else [],{e.name for e in _real_verified(r)})
def real_mathlib_revision_report_to_route_telemetry_events(r): return _telemetry(r.discovery_report.declarations if r.discovery_report else [],{e.name for e in _real_verified(r)},"real_mathlib")
def real_mathlib_revision_report_to_alchemical_trace(r): return _trace("real-mathlib",r.report_id,bool(_real_verified(r)))
def real_mathlib_revision_report_to_agent_experiences(r): return _experiences(r.discovery_report.declarations if r.discovery_report else [],{e.name for e in _real_verified(r)},"real-mathlib")
def _episodes(ds,names,prefix): return [ProcessEpisodeRecord(make_process_episode_id(prefix,d.declaration_id),ProcessEpisodeStatus.TERMINAL_VERIFIED_PROOF if d.name in names else ProcessEpisodeStatus.ADVISORY_ONLY,contexts=[ProcessContextItem(content_id(prefix+"-ctx",d.declaration_id),ProcessContextKind.RAW_EVENT,ProcessContextRole.ADVISORY_ONLY,d.full_name)],terminal_form=TerminalForm.VERIFIED_PROOF if d.name in names else None,verifier_boundary_crossed=d.name in names) for d in ds]
def _scores(ds,names,prefix):
 out=[]
 for d in ds:
  sig=DiscoveryValueSignal(content_id(prefix+"-sig",d.declaration_id),DiscoveryValueSignalKind.REUSE_VALUE,1.0 if d.name in names else .1,source_object_kind=DiscoveryValueObjectKind.RAW_TASK); s=DiscoveryValueScore(content_id(prefix+"-score",d.declaration_id),d.declaration_id,DiscoveryValueObjectKind.RAW_TASK,signals=[sig]); s.recompute(); out.append(s)
 return out
def _objects(ds,names): return [{"object_id":d.declaration_id,"name":d.full_name,"advisory":d.name not in names} for d in ds]
def _telemetry(ds,names,route): return [{"event_id":content_id(route,d.declaration_id),"route_kind":route,"verifier_boundary_crossed":d.name in names} for d in ds]
def _trace(prefix,id,fix):
 t=AlchemicalTrace(make_alchemical_trace_id(prefix,id))
 for p in (AlchemicalPhase.RAW_MATTER,AlchemicalPhase.CALCINATION,AlchemicalPhase.DESCENSION): t.add_step(phase=p,status=AlchemicalStatus.ADVISORY_ONLY)
 if fix:t.add_step(phase=AlchemicalPhase.FIXATION,status=AlchemicalStatus.PROMOTED_BY_VERIFIER)
 for p in (AlchemicalPhase.DISTILLATION,AlchemicalPhase.COAGULATION): t.add_step(phase=p,status=AlchemicalStatus.ADVISORY_ONLY)
 return t
def _experiences(ds,names,prefix): return [AgentExperience(content_id(prefix+"-exp",d.declaration_id),prefix,None,None,"project",None,AgentExperienceOutcome.VERIFIED_PROOF if d.name in names else AgentExperienceOutcome.ADVISORY_ONLY,terminal_form=TerminalForm.VERIFIED_PROOF if d.name in names else None,verifier_boundary_crossed=d.name in names) for d in ds]
def audit_public_demo_config(x): return [_af("CRITICAL","PUBLIC_DEMO_CONFIG_NON_ADVISORY","config non-advisory",x.demo_id)] if not x.advisory else []
def audit_real_mathlib_revision_demo_config(x): return [_af("CRITICAL","REAL_MATHLIB_CONFIG_NON_ADVISORY","config non-advisory",x.demo_id)] if not x.advisory else []
def audit_release_check_result(x): return [_af("CRITICAL","RELEASE_CHECK_NON_ADVISORY","check non-advisory",x.check_id)] if not x.advisory else []
def audit_public_demo_report(x):
 out=[]
 if not x.advisory: out.append(_af("CRITICAL","PUBLIC_DEMO_REPORT_NON_ADVISORY","report non-advisory",x.report_id))
 if x.truth_status!=DemoReleaseTruthStatus.ADVISORY_ONLY and not x.boundary_evidence_count(): out.append(_af("CRITICAL","PUBLIC_DEMO_PROOF_WITHOUT_BOUNDARY","demo claims proof without boundary",x.report_id))
 if x.known_skip_count() and not x.proof_library_demo_report.lawbook_replay_summary.get("accepted_total",0): out.append(_af("CRITICAL","PUBLIC_DEMO_SKIP_WITHOUT_ACCEPTANCE","known skip without acceptance",x.report_id))
 return out
def audit_real_mathlib_revision_report(x):
 out=[]
 if not x.advisory: out.append(_af("CRITICAL","REAL_MATHLIB_REPORT_NON_ADVISORY","report non-advisory",x.report_id))
 if x.status==DemoReleaseStatus.SKIPPED_ENVIRONMENT and x.truth_status not in {DemoReleaseTruthStatus.SKIPPED_NO_ENVIRONMENT,DemoReleaseTruthStatus.ADVISORY_ONLY}: out.append(_af("CRITICAL","REAL_MATHLIB_SKIP_AS_PROOF","missing env treated as proof",x.report_id))
 return out
def run_release_checks(*,include_public_demo=False,allow_live_verifier=False,allow_missing_verifier=True):
 root=Path(__file__).resolve().parents[1]; docs=[root/"README.md",root/"CHANGELOG.md",root/"RELEASE_NOTES.md",root/"docs"/"quickstart.md",root/"docs"/"public_demo.md",root/"docs"/"release_checklist.md",root/"docs"/"artifact_conventions.md",root/"docs"/"curated_real_mathlib_demo.md",root/"docs"/"mathlib_module_verification.md"]; cli=["run_public_demo.py","run_release_check.py","run_colab_testdrive.py","run_proof_library_demo.py","run_mathlib_declaration_discovery.py","run_mathlib_module_verification.py","run_mathlib_local_allowlist.py","run_mathlib_micro_subset.py","run_real_mathlib_demo.py"]
 try: import mathgraph.demo_release,mathgraph.proof_library_demo,mathgraph.version; imports_ok=True
 except Exception: imports_ok=False
 cli_ok=all(subprocess.run([sys.executable,str(root/"scripts"/x),"--help"],cwd=root,capture_output=True,text=True).returncode==0 for x in cli)
 from mathgraph.hardening import run_public_term_checks
 terms_ok=all(x.status.value=="PASS" for x in run_public_term_checks(root)); docs_ok=all(x.exists() for x in docs); artifact_text=(root/"docs"/"artifact_conventions.md").read_text(); artifact_ok=all(x in artifact_text for x in ("public_demo_report.json","public_demo_report.md","release_check_report.json","artifacts_manifest.json")); boundary_ok="release-check success is a release signal, not proof." in (root/"docs"/"release_process.md").read_text().lower() and "only verifier" in (root/"docs"/"quickstart.md").read_text().lower()
 checks=[_check(DemoReleaseCheckKind.IMPORTS,DemoReleaseCheckStatus.PASS if imports_ok else DemoReleaseCheckStatus.FAIL,"imports"),_check(DemoReleaseCheckKind.PUBLIC_TERMS,DemoReleaseCheckStatus.PASS if terms_ok else DemoReleaseCheckStatus.FAIL,"public terms"),_check(DemoReleaseCheckKind.CLI_HELP,DemoReleaseCheckStatus.PASS if cli_ok else DemoReleaseCheckStatus.FAIL,"cli help"),_check(DemoReleaseCheckKind.DOCS_PRESENT,DemoReleaseCheckStatus.PASS if docs_ok else DemoReleaseCheckStatus.FAIL,"docs"),_check(DemoReleaseCheckKind.EXAMPLES_PRESENT,DemoReleaseCheckStatus.PASS if (root/"examples"/"public_demo"/"public_demo_config.json").exists() and (root/"examples"/"real_mathlib_demo"/"curated_real_mathlib_demo_config.example.json").exists() else DemoReleaseCheckStatus.FAIL,"examples"),_check(DemoReleaseCheckKind.NOTEBOOK_PRESENT,DemoReleaseCheckStatus.PASS if (root/"notebooks"/"mathgraph_public_demo.py").exists() else DemoReleaseCheckStatus.FAIL,"notebook"),_check(DemoReleaseCheckKind.ARTIFACT_CONVENTIONS,DemoReleaseCheckStatus.PASS if artifact_ok else DemoReleaseCheckStatus.FAIL,"artifact conventions"),_check(DemoReleaseCheckKind.BOUNDARY_LANGUAGE,DemoReleaseCheckStatus.PASS if boundary_ok else DemoReleaseCheckStatus.FAIL,"boundary language")]
 if include_public_demo:
  r=run_public_demo(allow_execution=allow_live_verifier,allow_missing_verifier=allow_missing_verifier,accept_verified_entries_in_memory=allow_live_verifier); checks.append(_check(DemoReleaseCheckKind.PROOF_LIBRARY_DEMO,DemoReleaseCheckStatus.PASS if r.ok() else DemoReleaseCheckStatus.FAIL,"public demo",r.summary))
 from mathgraph.roadmap_alignment import check_roadmap_alignment
 a=check_roadmap_alignment(); checks.append(_check(DemoReleaseCheckKind.ROADMAP_ALIGNMENT,DemoReleaseCheckStatus.PASS if not a.critical_count() else DemoReleaseCheckStatus.FAIL,"roadmap",{"critical_total":a.critical_count()})); return checks
def build_release_check_report(checks,*,live_verifier_requested=False):
 v=get_version_info(); demo=next((x.summary for x in checks if x.name=="public demo"),{}); return {"created_at":_now(),"advisory":True,"checks":[x.to_dict() for x in checks],"summary":{"version":v["version"],"release_stage":v["release_stage"],"check_total":len(checks),"pass_total":sum(x.status==DemoReleaseCheckStatus.PASS for x in checks),"warn_total":sum(x.status==DemoReleaseCheckStatus.WARN for x in checks),"fail_total":sum(x.status==DemoReleaseCheckStatus.FAIL for x in checks),"skip_total":sum(x.status==DemoReleaseCheckStatus.SKIP for x in checks),"critical_total":sum(len(x.criticals) for x in checks),"warning_total":sum(len(x.warnings) for x in checks),"lean_available":bool(shutil.which("lean")),"live_verifier_requested":live_verifier_requested,"live_verifier_ran":bool(live_verifier_requested and demo.get("verified_total",0)),"public_demo_verified_total":demo.get("verified_total",0),"public_demo_known_skip_total":demo.get("known_skip_total",0)}}
def release_check_report_to_markdown(r): return "\n".join(["# Release Check","", "Release checks are advisory; success is not proof.","",*[f"- {x['name']}: {x['status']}" for x in r["checks"]]])+"\n"
def write_release_check_artifacts(r,out):
 out=Path(out); out.mkdir(parents=True,exist_ok=True); paths={"report":out/"release_check_report.json","markdown":out/"release_check_report.md","checks":out/"release_checks.jsonl","command_summary":out/"command_summary.json","manifest":out/"artifacts_manifest.json"}; _w(paths["report"],_j(r)); _w(paths["markdown"],release_check_report_to_markdown(r)); _w(paths["checks"],"".join(_j(x)+"\n" for x in r["checks"])); _w(paths["command_summary"],_j(r["summary"])); _w(paths["manifest"],_j({"artifacts":[p.name for p in paths.values()]})); return {k:str(v) for k,v in paths.items()}
def concise_release_check_summary(r,artifact_paths=None):
 s=r["summary"]; status="FAIL" if s["fail_total"] or s["critical_total"] else "WARN" if s["warn_total"] else "PASS"; p=dict(artifact_paths or {}); return "\n".join(["MathGraph Release Check",f"status: {status}",f"checks: pass={s['pass_total']} warn={s['warn_total']} fail={s['fail_total']} skip={s['skip_total']}",f"version: {s['version']}",f"criticals: {s['critical_total']}",f"warnings: {s['warning_total']}",f"markdown: {p.get('markdown','')}",f"json: {p.get('report','')}"])+"\n"
def _af(sev,code,msg,obj): return {"severity":sev,"code":code,"message":msg,"object_id":obj}
def _now(): return datetime.now(timezone.utc).isoformat()
def _j(x): return json.dumps(x,sort_keys=True,separators=(",",":"),default=str)
def _w(p,t): path=Path(p); path.parent.mkdir(parents=True,exist_ok=True); path.write_text(t,encoding="utf-8")
