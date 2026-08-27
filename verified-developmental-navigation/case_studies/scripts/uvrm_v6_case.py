import json, pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
s=(ROOT/'source/uvrm_v6/score_output.txt').read_text()
dec=json.JSONDecoder()
rows,i=dec.raw_decode(s)
meta=json.loads((ROOT/'source/uvrm_v6/run_metadata.json').read_text())
arms=sorted({r['arm'] for r in rows})
agg={}
for a in arms:
    rs=[r for r in rows if r['arm']==a]
    agg[a]={
      'n':len(rs),
      'semantic_passes':sum(bool(r['semantic_pass']) for r in rs),
      'mean_semantic_score':sum(r['semantic_score'] for r in rs)/len(rs),
      'forbidden_hits':sum(r['forbidden_hits'] for r in rs),
      'invocations_per_case':meta['arms'][a]['invocations_per_case'],
      'final_max_tokens':meta['arms'][a]['final_max_tokens'],
      'reconstruction_max_tokens':meta['arms'][a]['reconstruction_max_tokens'],
    }
assert len(rows)==40
assert all(v['n']==8 for v in agg.values())
assert agg['GRAPH']['semantic_passes']==7
assert agg['RECONSTRUCT_1']['semantic_passes']==4
assert agg['GRAPH_PERMUTED']['semantic_passes']==4
assert all(v['forbidden_hits']==0 for v in agg.values())
assert agg['GRAPH']['invocations_per_case']==agg['RECONSTRUCT_1']['invocations_per_case']==1
assert agg['GRAPH']['final_max_tokens']==agg['RECONSTRUCT_1']['final_max_tokens']==220
assert agg['GRAPH']['mean_semantic_score'] > agg['RECONSTRUCT_1']['mean_semantic_score']
assert agg['GRAPH']['mean_semantic_score'] > agg['GRAPH_PERMUTED']['mean_semantic_score']
result={
  'case':'uvrm_graph_v6_real_protected_benchmark',
  'source_run':32691619972,
  'source_commit':'d38055fd8790871ddfd4db7e082171d642bf2ede',
  'raw_scored_rows':len(rows),
  'model':meta['model'],
  'temperature':meta['temperature'],
  'aggregate':agg,
  'matched_budget_graph_minus_reconstruct1_passes':agg['GRAPH']['semantic_passes']-agg['RECONSTRUCT_1']['semantic_passes'],
  'matched_budget_graph_minus_reconstruct1_score':agg['GRAPH']['mean_semantic_score']-agg['RECONSTRUCT_1']['mean_semantic_score'],
  'causal_label_graph_minus_permuted_passes':agg['GRAPH']['semantic_passes']-agg['GRAPH_PERMUTED']['semantic_passes'],
  'causal_label_graph_minus_permuted_score':agg['GRAPH']['mean_semantic_score']-agg['GRAPH_PERMUTED']['mean_semantic_score'],
  'pass':True,
}
(ROOT/'results').mkdir(exist_ok=True)
(ROOT/'results/uvrm_v6.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps(result,indent=2,sort_keys=True))
