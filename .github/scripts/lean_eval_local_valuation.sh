#!/usr/bin/env bash
set -u
LEAN_EVAL_SHA=9b82c4083e71e93c7d6aa43a960cd492ae53a35d
TARGET=annals_erdos_supersingular_primes
rm -rf /tmp/lean-eval "/tmp/$TARGET"
git clone --filter=blob:none https://github.com/leanprover/lean-eval.git /tmp/lean-eval
cd /tmp/lean-eval
git checkout "$LEAN_EVAL_SHA"
test "$(git rev-parse HEAD)" = "$LEAN_EVAL_SHA"
lake exe cache get
lake build
lake exe lean-eval start-problem "$TARGET" "/tmp/$TARGET"
cd "/tmp/$TARGET"
lake update
cat > Submission.lean <<'LEAN'
import ChallengeDeps
import Mathlib.Analysis.Complex.Exponential
import Mathlib.NumberTheory.Padics.PadicVal.Basic

set_option autoImplicit false
namespace ErdosSupersingularPrimes
open Int Real

def k₀ : ℕ := sorry

theorem generated_core_bound (k : ℕ) (hk : k ≥ k₀) (s : Solution k)
    (hs : s.l.Prime) (hy : s.y ≠ 0) (hd : s.d ≠ 0) :
    s.l ≤ exp (10 ^ k) := by
  have hDelta : ∀ p : ℕ, p.Prime →
      (∑ i ∈ Finset.range k,
        padicValRat p (((s.n + i * s.d) : ℤ) : ℚ)) =
      (s.l : ℤ) * padicValRat p (s.y : ℚ) := by
    intro p hp
    letI : Fact p.Prime := ⟨hp⟩
    have hprod : (∏ i ∈ Finset.range k, (s.n + i * s.d)) ≠ 0 := by
      have hpow : s.y ^ s.l ≠ 0 := pow_ne_zero _ hy
      rw [← s.eq] at hpow
      exact hpow
    have hfac : ∀ i ∈ Finset.range k, (s.n + i * s.d) ≠ 0 :=
      Finset.prod_ne_zero_iff.mp hprod
    let f : ℕ → ℤ := fun i => s.n + i * s.d
    have hval_general : ∀ t : Finset ℕ,
        (∀ i ∈ t, f i ≠ 0) →
        padicValRat p (((∏ i ∈ t, f i) : ℤ) : ℚ) =
          ∑ i ∈ t, padicValRat p ((f i : ℤ) : ℚ) := by
      intro t
      refine Finset.induction_on t ?_ ?_
      · intro ht
        simp
      · intro a t ha ih ht
        rw [Finset.prod_insert ha, Finset.sum_insert ha, Int.cast_mul]
        rw [padicValRat.mul]
        · rw [ih]
          intro i hi
          exact ht i (Finset.mem_insert_of_mem hi)
        · exact_mod_cast ht a (Finset.mem_insert_self a t)
        · exact_mod_cast Finset.prod_ne_zero_iff.mpr (by
            intro i hi
            exact ht i (Finset.mem_insert_of_mem hi))
    have hval := hval_general (Finset.range k) (by simpa [f] using hfac)
    rw [← hval]
    rw [s.eq]
    simpa using (padicValRat.pow (p := p) (s.y : ℚ) (k := s.l))
  sorry
end ErdosSupersingularPrimes
LEAN
set +e
lake build Submission > /tmp/local-valuation-interface.log 2>&1
code=$?
echo "LOCAL_VALUATION_INTERFACE_VERIFY exit=$code"
cat /tmp/local-valuation-interface.log
if [ "$code" -ne 0 ]; then
  echo 'LOCAL_VALUATION_GATE {"classification":"INTERFACE_PROOF_FAILURE"}'
  exit 0
fi
cp Submission.lean /tmp/local-base.lean
solved=0
winner=''
: > /tmp/replay.tsv
while IFS=$'\t' read -r name body; do
  cp /tmp/local-base.lean Submission.lean
  BODY="$body" python3 - <<'PY'
import os,re
s=open('Submission.lean').read()
s,n=re.subn(r'  sorry\nend ErdosSupersingularPrimes', '  '+os.environ['BODY']+'\nend ErdosSupersingularPrimes', s, count=1)
if n != 1: raise SystemExit(f'replay replacements={n}')
open('Submission.lean','w').write(s)
PY
  if [ $? -ne 0 ]; then echo 'LOCAL_VALUATION_HARNESS_FATAL'; exit 90; fi
  lake build Submission > "/tmp/replay-${name}.log" 2>&1
  rc=$?
  echo "LOCAL_VALUATION_REPLAY name=$name exit=$rc"
  printf '%s\t%s\n' "$name" "$rc" >> /tmp/replay.tsv
  if [ "$rc" -eq 0 ]; then solved=1; winner="$name"; break; fi
done <<'EOF'
simp	try simp_all
aesop	try aesop
grind	try grind
norm	try norm_num at *
linarith	try linarith
nlinarith	try nlinarith
positivity	try positivity
ringnf	try ring_nf
fieldsimp	try field_simp
elim	try solve_by_elim
contra	try contradiction
tauto	try tauto
EOF
if [ "$solved" -eq 1 ]; then
  echo "LOCAL_VALUATION_GATE {\"classification\":\"EXACT_REACHED\",\"winner\":\"$winner\"}"
else
  echo 'LOCAL_VALUATION_GATE {"classification":"LOCAL_VALUATION_VERIFIED_NO_EXACT"}'
fi
