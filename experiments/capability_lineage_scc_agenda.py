"""Independent SCC-aware agenda baseline, benchmark-only.

Canonical resolver validates admission. SCCs use independent Kosaraju ordering.
After an evidence change only directly affected components and components whose
claim states change are visited; local SCCs rebuild their least fixed point.
"""
from collections import defaultdict, deque
import heapq
from mathgraph_check.warrant_resolution import resolve_graph

class SCCAgenda:
    def __init__(self, claims, routes, receipts, *, withdrawn=frozenset(), relations=()):
        ref = resolve_graph(claims, routes, receipts, withdrawn=withdrawn, relations=relations)
        self.claims, self.routes, self.receipts = tuple(claims), tuple(routes), tuple(receipts)
        self.withdrawn = set(withdrawn)
        self.relations = tuple(relations)
        self.required, self.by_receipt = [], defaultdict(set)
        self.incoming = defaultdict(list)
        nodes = [c.id for c in claims]
        adj, rev = {x:set() for x in nodes}, {x:set() for x in nodes}
        rels = {r.id:r for r in relations}
        for i,r in enumerate(routes):
            need=set(r.evidence)
            if r.relation:
                b=rels[r.relation]
                need.update((b.verifier,*b.evidence))
            self.required.append(need)
            for e in need: self.by_receipt[e].add(i)
            self.incoming[r.conclusion].append(i)
            for p in r.premises:
                adj[p].add(r.conclusion)
                rev[r.conclusion].add(p)
        seen=set()
        finish=[]
        def dfs(v):
            seen.add(v)
            for w in sorted(adj[v]):
                if w not in seen: dfs(w)
            finish.append(v)
        for v in nodes:
            if v not in seen: dfs(v)
        seen.clear()
        self.parts=[]
        def collect(v,out):
            seen.add(v);out.append(v)
            for w in sorted(rev[v]):
                if w not in seen:collect(w,out)
        for v in reversed(finish):
            if v not in seen:
                out=[];collect(v,out);self.parts.append(tuple(out))
        self.comp={v:i for i,p in enumerate(self.parts) for v in p}
        self.down=defaultdict(set)
        incoming=[0]*len(self.parts)
        for v in nodes:
            for w in adj[v]:
                a,b=self.comp[v],self.comp[w]
                if a!=b and b not in self.down[a]:
                    self.down[a].add(b);incoming[b]+=1
        q=[i for i,x in enumerate(incoming) if x==0]
        heapq.heapify(q)
        order=[]
        while q:
            i=heapq.heappop(q);order.append(i)
            for k in sorted(self.down[i]):
                incoming[k]-=1
                if incoming[k]==0: heapq.heappush(q,k)
        self.rank={i:k for k,i in enumerate(order)}
        self.value={v:False for v in nodes}
        self.route_state=[False]*len(routes)
        for i in order:self._solve(i)
        assert self.states()==dict(ref.states)
        assert self.active_routes()==ref.active_routes

    def _solve(self,i):
        part=self.parts[i]
        old=tuple(self.value[v] for v in part)
        for v in part:self.value[v]=False
        changed=True
        while changed:
            changed=False
            for v in part:
                if not self.value[v]:
                    for j in self.incoming[v]:
                        r=self.routes[j]
                        if not (self.required[j]&self.withdrawn) and all(self.value[p] for p in r.premises):
                            self.value[v]=True;changed=True;break
        for v in part:
            for j in self.incoming[v]:
                r=self.routes[j]
                self.route_state[j]=not (self.required[j]&self.withdrawn) and all(self.value[p] for p in r.premises)
        return old!=tuple(self.value[v] for v in part)

    def update(self,receipt,live):
        if receipt not in {r.id for r in self.receipts}:raise ValueError("UNKNOWN_RECEIPT")
        if (receipt not in self.withdrawn)==live:return 0
        if live:self.withdrawn.remove(receipt)
        else:self.withdrawn.add(receipt)
        pending={self.comp[self.routes[j].conclusion] for j in self.by_receipt[receipt]}
        heap=[(self.rank[i],i) for i in pending]
        heapq.heapify(heap)
        n=0
        while heap:
            _,i=heapq.heappop(heap)
            if i not in pending:continue
            pending.remove(i);n+=1
            if self._solve(i):
                for k in self.down[i]:
                    if k not in pending:
                        pending.add(k);heapq.heappush(heap,(self.rank[k],k))
        return n

    def states(self):
        return {c.id:("WARRANTED_BOUNDED" if c.kind=="formal" else "SOURCE_DOCUMENTED") if self.value[c.id] else "UNKNOWN" for c in self.claims}
    def active_routes(self):
        return tuple(sorted((r for i,r in enumerate(self.routes) if self.route_state[i]), key=lambda r:(r.conclusion,r.evidence,r.premises,r.relation or "")))
