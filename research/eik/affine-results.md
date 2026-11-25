# Affine folding experiment — 2026-11-25

Baseline rrr SHA256 3d9777afffd5aba80d52bf4926243aa3dbe1c1fa78b12f63ed597d634895e3b4.
Evaluator 5a32428ad4aa23bce737d50a738ace24ddeeed2e.
Generator fold.py, commit 23ea084f2147f409c5d716c50e8b84681f4d5ddc.
Workflow 00125c4ec7e0c0fa8e5ddde6280bb9967e5fef2d.
Run https://github.com/metalogiclabs/mathgraph/actions/runs/45547504823.

The exact dyadic shift folds an input-dependent affine term into a cubic coefficient. No new guard is needed. Four table variants and two small-input rounding identities tested separately. Native GCC differential tests compared all words of both signs in magnitude ranges [0x407ff000,0x418ab001) for sigmoid, [0x40000000,0x41103001) for tanh, [0x337ff000,0x3a689001) for sigmoid. Per variant: 34,963,458 + 35,676,162 + 231,817,218 = 302,456,838 outputs; total 1,814,741,028, no discrepancies. Each also passed 18,147,264 pseudorandom/exponent-boundary comparisons. These are comparisons to rrr, not independent proof of all binary32 outputs.

Official measure seed 20261125, all seven jobs and sampled reference checks passed:
- control 29.10782642186173
- small2 29.244930975365254
- direct 29.451046227412483
- signed 29.451046227412483
- reconstruct 29.454632522306333
- small 29.47028406688935
- biased 29.524999997909294

Biased artifact 14991629608 (59,401 bytes, SHA256 6a582769cddfe032abec489e697223151eea4d6195c80ba07c05443b27c25079; independent hash and ZIP CRC match). Actual source hash 30c37afc9d057a3a6a2132b57003187394938f56030603c26e70293ed1584acc. Sample per target 98,304 words, zero discrepancies on each. Local exact evaluator GCC sanitizer host check (entry compiled with host_cc_args; checker linked to vendored exact-c) on biased: sigmoid chunks 1031:1049, tanh 1024:1042 and 3072:3090; each 18,874,368 checked, zero mismatch, range_complete true, no sanitizer failure. Total 56,623,104. Full check remains UNKNOWN.

Separate cell probe: enumerated 135,706,627 affected positive/negative cell inputs and compared unguarded quotient against rrr. 341,926 mismatches in total. Intersection of allowed signed integer constant-bias intervals feasible in 18/656 examined family/cell pairs (0/132 positive sigmoid, 1/99 negative sigmoid, 0/153 middle tanh, 7/137 high tanh, 10/135 high sigmoid). This rejects the direct unguarded constant-bias shortcut in the remaining examined cells; does not prove no better polynomial exists.

Public frontier inventory run https://github.com/metalogiclabs/mathgraph/actions/runs/45547043299 failed at the documented boards endpoint (HTTP 403). No newer public source retrieved and no attempt to access unpublished code. Historical threshold 27.354 is not current champion verification. No fees or submission. All six modifications rejected for performance relative to same-seed control. No winning implementation.
