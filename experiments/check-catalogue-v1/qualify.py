"""Frozen four-profile replay, partial repair, withdrawal and 104-row accounting.

Synthetic Git children change no subject checkout, index or branch. The candidate
is an experiment, not an upstream change or a whole-repository qualification.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import signal
import subprocess
import tempfile
import time

ROOT=Path(__file__).resolve().parents[2]
CLI_PATH='integrations/mathgraph-check-github/catalogue-check-v1/run.mjs'
QUALIFIER_PATH='experiments/check-catalogue-v1/qualify.py'
VERIFIER_PATHS=('integrations/mathgraph-check-github','experiments/check-catalogue-v1',
                '.github/workflows/check-retained-report-v1.yml')
REPORT_PATH='Tests/SuiteRunner/Reports.lean'
MAIN_PATH='Tests/SuiteRunner/Main.lean'
ORIGINAL='14eb6dbab845d2ac61f171a9ed61906d3f9ffb2f'
OUTCOME_REPAIR='c06ec22e49c139a47a1ef08c96eb6726bb2b32ee'
OUTCOME_REPAIR_TREE='a1d36507b49c60f6734f3450de1e6efe04e9185d'
PRODUCTION_SUBTREE='4197c0b6f2fb369e9806ca486d38aef87b077c81'
REPAIR_REPORT_SHA='7b7df4d80cdfea80db83a4c9ab670a5339e84961b78a1da8233777f43bd7b589'
COMBINED_REPORT_SHA='f9a3e37c8f903787f157a66747291c057a757a9c5c380a014dcc0fe1a197606a'
OLD_CONDITION='else if name == "failure" && isStart && cur.isSome then failed := true'
NEW_CONDITION='else if (name == "failure" || name == "error") && isStart && cur.isSome then failed := true'
XML='junit-report-integrity-v1'; STATUS='junit-status-preservation-v1'
PER_CASE='suite-per-case-agreement-v1'; REFUSAL='suite-refusal-integrity-v1'
PROFILE_CASE_IDS={
 XML:('prefix','suffix','duplicate','attribute_entity','content_entity','closing_content',
      'empty','one','failure','skip','comment_cdata','entities','truncated','mismatch','two_roots',
      'unquoted','open_comment','open_tag','no_root'),
 STATUS:('plain_pass','assertion_failure','skipped_case','error_empty','error_text','error_then_pass',
         'mixed_outcomes','error_text_control'),
 PER_CASE:('identical_outcomes','reordered_same_cases','different_totals',
           'equal_totals_swapped_outcomes','single_preset_swapped_outcomes'),
 REFUSAL:('deliberate_rejection','ordinary_acceptance','unexpected_acceptance','unmarked_rejection',
          'exit_2','exit_127','exit_139','missing_executable','actual_crash','contradictory_rejection',
          'contradictory_acceptance','extra_stdout','stderr_only_marker','unmarked_acceptance',
          'missing_newline','marked_abnormal_exit','timeout_exit','actual_timeout')}
ORIGINAL_MISMATCHES={XML:(),STATUS:('error_empty','error_text','error_then_pass','mixed_outcomes'),
 PER_CASE:('equal_totals_swapped_outcomes','single_preset_swapped_outcomes'),
 REFUSAL:('unmarked_rejection','exit_2','exit_127','exit_139','missing_executable','actual_crash',
          'contradictory_rejection','contradictory_acceptance','extra_stdout','stderr_only_marker',
          'unmarked_acceptance','missing_newline','marked_abnormal_exit')}
PARTIAL_MISMATCHES={**{p:() for p in PROFILE_CASE_IDS},STATUS:ORIGINAL_MISMATCHES[STATUS]}
NO_MISMATCHES={p:() for p in PROFILE_CASE_IDS}
PROFILE_PROMPTS={XML:(28,29,39,59,77),STATUS:(28,39,59,77,78,100),
                 PER_CASE:(28,35,59,61,66,67,70,73,77,90),REFUSAL:(28,55,59,60,77,78,100)}


def digest(data): return hashlib.sha256(data).hexdigest()
def require(ok,reason):
    if not ok: raise RuntimeError(reason)
def write_json(path,value): path.write_text(json.dumps(value,indent=2)+'\n')
def git(repo,*args,data=None,env=None,binary=False,optional=False):
    p=subprocess.run(['git','-C',str(repo),*args],input=data,capture_output=True,timeout=30,env=env)
    if p.returncode:
        if optional: return None
        raise RuntimeError('GIT_COMMAND_FAILED: '+' '.join(args)+': '+p.stderr.decode(errors='replace')[-1000:])
    return p.stdout if binary else p.stdout.decode().strip()


def repository_state(repo):
    index=Path(git(repo,'rev-parse','--git-path','index'))
    if not index.is_absolute(): index=Path(repo)/index
    return {'head':git(repo,'rev-parse','--verify','HEAD',optional=True),
            'symbolic_head':git(repo,'symbolic-ref','--quiet','HEAD',optional=True),
            'refs':git(repo,'for-each-ref','--format=%(refname) %(objectname)'),
            'index_sha256':digest(index.read_bytes()) if index.exists() else None}


def verifier_identity():
    required=(CLI_PATH,QUALIFIER_PATH,'integrations/mathgraph-check-github/retained-suite-v1/per-case.mjs',
              'integrations/mathgraph-check-github/retained-suite-v1/refusal.mjs')
    git(ROOT,'ls-files','--error-unmatch','--',*required)
    require(not git(ROOT,'status','--porcelain','--untracked-files=all','--',*VERIFIER_PATHS),
            'VERIFIER_INPUTS_NOT_COMMITTED_AND_CLEAN')
    files=git(ROOT,'ls-files','--',*VERIFIER_PATHS).splitlines()
    return {'commit':git(ROOT,'rev-parse','HEAD'),'tree':git(ROOT,'rev-parse','HEAD^{tree}'),
            'files':{p:digest((ROOT/p).read_bytes()) for p in files}}


def make_child(repo,parent,changes,message):
    before=repository_state(repo)
    with tempfile.TemporaryDirectory(prefix='mathgraph-catalogue-index-') as temp:
        env={**os.environ,'GIT_INDEX_FILE':str(Path(temp)/'index'),
             'GIT_AUTHOR_NAME':'MathGraph Synthetic Qualification','GIT_AUTHOR_EMAIL':'qualification@example.invalid',
             'GIT_COMMITTER_NAME':'MathGraph Synthetic Qualification','GIT_COMMITTER_EMAIL':'qualification@example.invalid',
             'GIT_AUTHOR_DATE':'2026-11-22T00:00:00+0000','GIT_COMMITTER_DATE':'2026-11-22T00:00:00+0000'}
        git(repo,'read-tree',parent,env=env)
        for path,content in changes.items():
            if content is None: git(repo,'update-index','--force-remove',path,env=env)
            else:
                require(git(repo,'ls-tree',parent,'--',path).startswith('100644 '),'UNSUPPORTED_SOURCE_FILE_MODE')
                blob=git(repo,'hash-object','-w','--stdin',data=content)
                git(repo,'update-index','--cacheinfo','100644',blob,path,env=env)
        tree=git(repo,'write-tree',env=env)
        commit=git(repo,'-c','commit.gpgsign=false','commit-tree',tree,'-p',parent,data=message.encode(),env=env)
    require(repository_state(repo)==before,'CALLER_CHECKOUT_INDEX_OR_REFS_CHANGED')
    require(git(repo,'rev-list','--parents','-n','1',commit)==commit+' '+parent,'SYNTHETIC_PARENT_MISMATCH')
    require(sorted(git(repo,'diff-tree','--no-commit-id','--name-only','-r',parent,commit).splitlines())==sorted(changes),
            'SYNTHETIC_UNDECLARED_CHANGED_PATHS')
    return {'commit':commit,'parent':parent,'tree':tree,'changed_paths':sorted(changes),
            'provenance':'ACTUAL_LOCAL_SYNTHETIC_GIT_COMMIT','caller_checkout_unchanged':True}


def prepare_status_child(repo,parent,out,original_sha=REPAIR_REPORT_SHA,expected_sha=COMBINED_REPORT_SHA):
    source=git(repo,'show',parent+':'+REPORT_PATH,binary=True)
    require(digest(source)==original_sha,'SOURCE_PIN_MISMATCH')
    require(source.count(OLD_CONDITION.encode())==1,'STATUS_REPAIR_CONDITION_NOT_UNIQUE')
    candidate=source.replace(OLD_CONDITION.encode(),NEW_CONDITION.encode(),1)
    require(digest(candidate)==expected_sha,'COMBINED_SOURCE_PIN_MISMATCH')
    result=make_child(repo,parent,{REPORT_PATH:candidate},
                      'Synthetic qualification: combine retained outcome and JUnit status repairs\n')
    require(git(repo,'show',result['commit']+':'+REPORT_PATH,binary=True)==candidate,'COMBINED_COMMIT_BYTES_MISMATCH')
    result.update(path=REPORT_PATH,source_sha256=expected_sha,
                  git_blob=git(repo,'rev-parse',result['commit']+':'+REPORT_PATH))
    (out/'combined-reports.lean').write_bytes(candidate)
    (out/'combined.patch').write_bytes(git(repo,'diff','--no-ext-diff','--no-textconv',parent,result['commit'],binary=True))
    (out/'combined-commit.txt').write_bytes(git(repo,'cat-file','commit',result['commit'],binary=True))
    write_json(out/'combined-candidate.json',result)
    return result


def validate_coverage(result,expected):
    """Check the reported ledger against the separately declared protocol."""
    source_path=ROOT/'integrations/mathgraph-check-github/catalogue-check-v1/catalogue.json'
    catalogue=json.loads(source_path.read_text());coverage=result.get('coverage',{})
    require(coverage.get('revision')==catalogue['revision'] and coverage.get('source')==catalogue['source'] and
            coverage.get('catalogue_sha256')==digest(source_path.read_bytes()),'CATALOGUE_SOURCE_IDENTITY_MISMATCH')
    outcomes={p:'UNKNOWN' if expected is None else 'OBSERVED_MISMATCH' if expected[1][p] else 'OBSERVED_AGREEMENT'
              for p in PROFILE_CASE_IDS}
    counts={'agreement':sum(s=='OBSERVED_AGREEMENT' for s in outcomes.values()),
            'discrepancy':sum(s=='OBSERVED_MISMATCH' for s in outcomes.values()),
            'unknown':sum(s=='UNKNOWN' for s in outcomes.values()),'not_run':0}
    require(result.get('profile_counts')==counts,'PROFILE_COUNTS_MISMATCH')
    row_statuses=[];incomplete_count=0
    for row,canonical in zip(coverage['items'],catalogue['items']):
        require(all(row.get(k)==v for k,v in canonical.items()),'CATALOGUE_PROMPT_CHANGED')
        mapped=[p for p,ids in PROFILE_PROMPTS.items() if row['id'] in ids]
        checks=row.get('checks',[])
        require([c.get('profile') for c in checks]==mapped,'CATALOGUE_PROFILE_MAPPING_MISMATCH')
        status=('UNSUPPORTED_BY_THIS_COMMAND' if not mapped else 'UNKNOWN' if expected is None else
                'BOUNDED_MISMATCH' if any(outcomes[p]=='OBSERVED_MISMATCH' for p in mapped) else 'BOUNDED_AGREEMENT')
        incomplete=bool(mapped) and expected is None
        require(row.get('status')==status and row.get('incomplete') is incomplete,'CATALOGUE_ROW_OUTCOME_MISMATCH')
        require(isinstance(row.get('residual'),str) and bool(row['residual']),'CATALOGUE_RESIDUAL_OMITTED')
        for check in checks:
            p=check['profile'];entry=result['profiles'][p]
            require(check.get('status')==outcomes[p] and entry.get('status')==outcomes[p] and
                    check.get('base')==entry.get('base') and check.get('head')==entry.get('head') and
                    check.get('result')==entry.get('result') and check.get('obligation') and check.get('boundary'),
                    'CATALOGUE_CHECK_EVIDENCE_MISMATCH')
        row_statuses.append(status);incomplete_count+=incomplete
    require(coverage.get('counts')=={
        'accounted_prompts':104,'mapped_prompts':len(set().union(*map(set,PROFILE_PROMPTS.values()))),
        'bounded_agreement':row_statuses.count('BOUNDED_AGREEMENT'),
        'bounded_mismatch':row_statuses.count('BOUNDED_MISMATCH'),
        'unknown':row_statuses.count('UNKNOWN'),'not_run':0,
        'unsupported_by_this_command':row_statuses.count('UNSUPPORTED_BY_THIS_COMMAND'),
        'prompts_with_incomplete_checks':incomplete_count,'fully_covered_families':0},'CATALOGUE_COUNTS_MISMATCH')


def validate_aggregate(result,exit_code,base,head,expected,out):
    coverage=result.get('coverage',{})
    require([x.get('id') for x in coverage.get('items',[])]==list(range(1,105)) and
            coverage.get('complete_failure_coverage') is False and
            all(x.get('full_family_coverage')=='UNESTABLISHED' for x in coverage.get('items',[])),
            'CATALOGUE_ACCOUNTING_OR_BOUNDARY_FAILED')
    require(result.get('subjects')=={'base':base,'head':head},'AGGREGATE_SOURCE_BINDING_FAILED')
    require(set(result.get('profiles',{}))==set(PROFILE_CASE_IDS),'PROFILE_COVERAGE_INCOMPLETE')
    validate_coverage(result,expected)
    if expected is None:
        require(exit_code==2 and result.get('status')=='INCOMPLETE' and
                all(p.get('status')=='UNKNOWN' for p in result['profiles'].values()),'ABSENT_MODULE_NOT_UNKNOWN')
    else:
        head_discrepancy=any(expected[1].values())
        require(exit_code==(1 if head_discrepancy else 0) and result.get('status')==
                ('COMPLETED_WITH_DISCREPANCIES' if head_discrepancy else 'COMPLETED_BOUNDED_AGREEMENT'),
                'AGGREGATE_OUTCOME_FAILED')
    receipts={}
    for profile,case_ids in PROFILE_CASE_IDS.items():
        entry=result['profiles'][profile]
        require(bool(entry.get('result')) and bool(entry.get('result_sha256')),'PROFILE_RECEIPT_MISSING')
        path=out/entry['result']
        require(path.resolve().is_relative_to(out.resolve()) and path.is_file(),'PROFILE_RECEIPT_PATH_INVALID')
        require(digest(path.read_bytes())==entry['result_sha256'],'PROFILE_RECEIPT_DIGEST_MISMATCH')
        receipt=json.loads(path.read_text());receipts[profile]=receipt
        if expected is None:
            require(receipt.get('status')=='UNKNOWN' and
                    any(word in receipt.get('reason','').upper() for word in ('ABSENT','MISSING','UNAVAILABLE','UNREADABLE')),
                    'ABSENT_MODULE_WRONG_UNKNOWN_REASON')
            continue
        require(receipt.get('method',{}).get('id')==profile,'PROFILE_METHOD_MISMATCH')
        require(receipt.get('cost',{}).get('model_calls')==0,'MODEL_CALL_CLAIM_MISMATCH')
        require(receipt.get('subjects',{}).get('base',{}).get('revision')==base and
                receipt.get('subjects',{}).get('head',{}).get('revision')==head,'PROFILE_SOURCE_MISMATCH')
        for side,wanted in zip(('base','head'),expected):
            arm=receipt.get(side,{})
            rows=arm.get('observations',[])
            require(arm.get('complete') is True and sorted(r.get('id','') for r in rows)==sorted(case_ids),
                    'NATIVE_CASE_COVERAGE_INCOMPLETE: '+profile+':'+side)
            require(all(type(r.get('passed')) is bool for r in rows),'CASE_OUTCOME_MISSING')
            mismatches=arm.get('mismatches',[])
            require(mismatches==[r for r in rows if not r['passed']] and
                    sorted(r['id'] for r in mismatches)==sorted(wanted[profile]),
                    'UNEXPECTED_NATIVE_DISCREPANCIES: '+profile+':'+side)
            require(entry.get(side)=={'cases':len(case_ids),'mismatches':len(wanted[profile])},'AGGREGATE_COUNT_MISMATCH')
        require(entry['status']==('OBSERVED_MISMATCH' if expected[1][profile] else 'OBSERVED_AGREEMENT'),
                'PROFILE_VERDICT_MISMATCH')
    return receipts


def execute(command,log_path):
    p=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
    try:
        output,_=p.communicate(timeout=540)
    except (subprocess.TimeoutExpired,KeyboardInterrupt):
        os.killpg(p.pid,signal.SIGTERM)
        try: output,_=p.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid,signal.SIGKILL);output,_=p.communicate()
        log_path.write_bytes(output)
        raise
    log_path.write_bytes(output)
    return p.returncode


def main(argv=None):
    parser=argparse.ArgumentParser();parser.add_argument('--repo',required=True)
    parser.add_argument('--out',required=True);parser.add_argument('--lean',required=True)
    args=parser.parse_args(argv);out=Path(args.out).resolve();out.mkdir();repo=Path(args.repo).resolve()
    started=time.monotonic()
    summary={'engineering_qualification':'INCOMPLETE','runs':{},'boundary':
             'Four retained finite profiles; 104 candidate prompts accounted for, not 104 qualified detectors.',
             'original':ORIGINAL,'outcome_candidate':OUTCOME_REPAIR,'human_trial':'NOT_RUN','comparative_value':'NOT_RUN'}
    def persist():
        summary['wall_seconds']=time.monotonic()-started;write_json(out/'summary.json',summary)
    persist()
    try:
        verifier=verifier_identity();summary['verifier']=verifier;persist()
        require(git(repo,'rev-parse',OUTCOME_REPAIR+'^{tree}')==OUTCOME_REPAIR_TREE,'OUTCOME_REPAIR_TREE_MISMATCH')
        require(git(repo,'rev-list','--parents','-n','1',OUTCOME_REPAIR)==OUTCOME_REPAIR+' '+ORIGINAL,'OUTCOME_PARENT_MISMATCH')
        require(git(repo,'rev-parse',OUTCOME_REPAIR+':L4YAML')==PRODUCTION_SUBTREE,'PRODUCTION_SUBTREE_MISMATCH')
        combined=prepare_status_child(repo,OUTCOME_REPAIR,out);summary['combined_candidate']=combined
        fixed=combined['commit']
        require(git(repo,'rev-parse',fixed+':L4YAML')==PRODUCTION_SUBTREE,'COMBINED_CHANGED_PRODUCTION_SUBTREE')
        absent=make_child(repo,fixed,{REPORT_PATH:None,MAIN_PATH:None},'Synthetic unavailable-source control\n')
        summary['unavailable_source']=absent;persist()
        campaigns=(('partial-repair',ORIGINAL,OUTCOME_REPAIR,(ORIGINAL_MISMATCHES,PARTIAL_MISMATCHES)),
                   ('combined-repair',ORIGINAL,fixed,(ORIGINAL_MISMATCHES,NO_MISMATCHES)),
                   ('withdrawal',fixed,ORIGINAL,(NO_MISMATCHES,ORIGINAL_MISMATCHES)),
                   ('unchanged-candidate',fixed,fixed,(NO_MISMATCHES,NO_MISMATCHES)),
                   ('unavailable-source',fixed,absent['commit'],None))
        methods={};runtimes={};errors=[]
        for name,base,head,expected in campaigns:
            command=['node',str(ROOT/CLI_PATH),'--repo',str(repo),'--base',base,'--head',head,
                     '--out',str(out/name),'--lean',args.lean]
            record={'base':base,'head':head,'command':command,'qualification':'INCOMPLETE'}
            summary['runs'][name]=record;persist()
            try:
                exit_code=execute(command,out/(name+'.log'))
                path=out/name/'result.json';result=json.loads(path.read_text())
                record.update(exit_code=exit_code,status=result.get('status'),profile_counts=result.get('profile_counts'),
                              result_sha256=digest(path.read_bytes()),cost=result.get('cost'))
                receipts=validate_aggregate(result,exit_code,base,head,expected,out/name)
                if expected is not None:
                    for profile,receipt in receipts.items():
                        if profile in methods: require(methods[profile]==receipt.get('method'),'METHOD_CHANGED_BETWEEN_RUNS: '+profile)
                        else: methods[profile]=receipt.get('method')
                        require(bool(receipt.get('runtime')),'RUNTIME_IDENTITY_MISSING: '+profile)
                        if profile in runtimes: require(runtimes[profile]==receipt['runtime'],'RUNTIME_CHANGED_BETWEEN_RUNS: '+profile)
                        else: runtimes[profile]=receipt['runtime']
                    require(result['method']==summary.get('dispatcher_method',result['method']),'DISPATCH_METHOD_CHANGED_BETWEEN_RUNS')
                    summary['dispatcher_method']=result['method']
                record['qualification']='PASSED'
            except Exception as error:
                record.update(qualification='FAILED',reason=str(error));errors.append(name+': '+str(error))
            persist()
        require(verifier_identity()==verifier,'VERIFIER_CHANGED_DURING_QUALIFICATION')
        summary['profile_methods']=methods;summary['profile_runtimes']=runtimes
        require(not errors,'; '.join(errors))
        summary['engineering_qualification']='PASSED';persist();return 0
    except Exception as error:
        summary.update(engineering_qualification='FAILED',failure=str(error));persist();return 2
    finally:
        inventory={str(p.relative_to(out)):digest(p.read_bytes()) for p in sorted(out.rglob('*'))
                   if p.is_file() and p.name!='inventory.json'}
        write_json(out/'inventory.json',{'algorithm':'sha256','files':inventory})


if __name__=='__main__': raise SystemExit(main())
