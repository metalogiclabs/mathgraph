"""Immutable source-only cohort oracle, committed before inspecting Rust targets."""
from itertools import product,combinations_with_replacement
VALUES=(-2,-1,0,1,2)
KEYS=(-3,-2,-1,0,1,2,3)
UINT_MAX=4294967295
COUNTS={"recursive_search":5467,"binary_search":1764}
def cases(name):
    if name=="recursive_search":
        for n in range(5):
            for a in product(VALUES,repeat=n):
                for k in KEYS:
                    yield a,k
    elif name=="binary_search":
        for n in range(6):
            for a in combinations_with_replacement(VALUES,n):
                for k in KEYS:
                    yield a,k
    else:raise ValueError("UNKNOWN_CASE:"+name)
def allowed(name,array,key,result):
    if type(result) is not int:return False
    hits={i for i,x in enumerate(array) if x==key}
    if hits:return result in hits
    return result==(UINT_MAX if name=="recursive_search" else -1)
def require_counts():
    observed={name:sum(1 for _ in cases(name)) for name in COUNTS}
    if observed!=COUNTS:raise AssertionError("PREREGISTERED_CENSUS_MISMATCH")
    return observed
