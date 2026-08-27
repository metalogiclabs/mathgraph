import itertools, json, pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
data=json.loads((ROOT/'source/kernel_v41/disagreement_atlas.json').read_text())
out=data['all_outcomes']
tests=sorted(out)
checkers=sorted(next(iter(out.values())))

def partition(subset):
    groups={}
    for c in checkers:
        sig=tuple(out[t][c] for t in subset)
        groups.setdefault(sig,[]).append(c)
    return sorted(tuple(sorted(v)) for v in groups.values())

target=partition(tests)
minimal=[]
for k in range(len(tests)+1):
    for sub in itertools.combinations(tests,k):
        if partition(sub)==target:
            minimal.append(sub)
    if minimal: break

disagreements=[t for t in tests if len(set(out[t].values()))>1]
assert len(tests)==141
assert len(checkers)==6
assert len(disagreements)==9
assert target==[('lean4lean','nanoclo'),('mathgraph','nanobruijn','official'),('nanoda',)]
assert len(minimal[0])==2
result={
  'case':'lean_kernel_v41_real_differential_census',
  'source_run':32782797883,
  'source_commit':'cfa4d1cbb838d3116808ea3a2babdc7f805a9d80',
  'records':len(tests)*len(checkers),
  'tests':len(tests),
  'checkers':len(checkers),
  'disagreement_tests':len(disagreements),
  'future_equivalence_classes':[list(x) for x in target],
  'minimum_context_basis_size':len(minimal[0]),
  'minimum_bases_count':len(minimal),
  'one_minimum_basis':list(minimal[0]),
  'context_compression_factor':len(tests)/len(minimal[0]),
  'pass':True,
}
(ROOT/'results').mkdir(exist_ok=True)
(ROOT/'results/kernel_v41.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps(result,indent=2,sort_keys=True))
