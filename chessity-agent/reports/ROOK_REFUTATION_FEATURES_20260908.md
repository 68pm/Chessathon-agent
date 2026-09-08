# Existing rook-refutation features

**Selected upload remains v1.51.** Replaying eight existing teacher continuations
produced144 legal positions in0.592seconds, with zero JIT compilation,
new teacher searches, fitting or games. The same classical score function was
executed as Python; these are descriptive features, not search results.

The table samples quiet-to-move positions after three and five plies in the
existing320k-node lines. Static scores are from White's perspective. Attack units
weight piece attacks into the white king's adjacent squares; the legacy pressure
column is the existing tapered king-ring term. Static scores for positions in
check are present in the raw record but are not treated as quiescent leaf values.

| Root move | Ply | Last move | Static cp | Nonking attackers | Attack units | Legacy pressure cp |
|---|---:|---|---:|---:|---:|---:|
| Rc8 | 3 | Kg2 | -80 | 1 | 15 | 6.25 |
| Rc8 | 5 | Kf1 | -74 | 2 | 7 | 5.00 |
| Rd3 | 3 | Re3 | -93 | 1 | 2 | 2.92 |
| Rd3 | 5 | h3 | -82 | 1 | 2 | 2.92 |
| Nd1 | 3 | Kg2 | -94 | 0 | 0 | 0.00 |
| Nd1 | 5 | Kf1 | -101 | 1 | 2 | 2.92 |
| Nd5 | 3 | Kg2 | -66 | 1 | 15 | 6.25 |
| Nd5 | 5 | Kf1 | -63 | 2 | 7 | 5.00 |

After the Rc8 line's Kf1, queen and knight pressure involves two attackers but
contributes only5cp through the current tapered term. The Nd1 and Rd3 lines at
the same sampled ply have one attacker and about2.92cp. Material is still -285cp
at these samples; major material losses appear later. The root teacher values
are approximately-973 forRc8, -757 forRd3, -689 forNd1 and-806 forNd5.
Those root estimates are NOT verified labels for each descendant.

This narrow comparison suggests testing a bounded coordination term while a
queen remains, reusing attacks already counted in the evaluator to avoid another
board scan. It does not establish causality, and these features do not distinguish
Rc8 fromNd5 at every point. A term triggered by at least two attacking non-pawn,
non-king pieces could avoid treating a lone queen's activity as equivalent to a
coordinated attack. Any coefficient/cap and full tactical acceptance criteria
must be fixed before the new prototype is measured; no such prototype exists yet.

Engine evaluation diagnosis remains first. Learning would need independently
verified opponent-continuation targets and a reachable residual correction,
not simply copied root scores on every PV prefix. Existing game histories and
teacher references supplied the targeted data; no broad GM collection was needed.

[Predeclaration](IMPROVEMENT_CYCLE_28.md) ·
[Raw features and PVs](evidence/rook-refutation-features-20260908/refutation-features.json) ·
[Evidence manifest](evidence/rook-refutation-features-20260908/manifest.json) ·
[Prior gate](TACTICAL_PILOT_27_20260908.md)
