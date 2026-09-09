# Diagnose six new defensive, structural and conversion decisions

The latest three own public games contain two losses and a draw, with unknown
submission hashes. Review all candidate moves first; do not attribute those
public decisions to selectedv1.56 without submission evidence.

Compare currentv1.56's forced played/teacher-alternative branches at six exposed
roots: round83 Black19...Be4/...Re8; round82 White43Nxe5/Ne1 and45Kf4/Ke4;
round81 White8fxe5/f5,48Ke3/d4 and55Kxd4/Bd7. Existing root reviews agree on
these alternatives. The drawn game had a substantial advantage at several of
these points, unlike the previously diagnosed local draw. Do not conflate them.

Run twelve branches to eight plies, each bounded by2million nodes and5seconds,
with exact history-compatible table tracing and full restoration checks. Reuse
the correct v1.56 search buffers. Root-policy preferences are disabled only in
this forced-branch diagnostic. Preserve incomplete traces and mates explicitly.
Quiescence probes use100k nodes and2seconds.

Independently label at most72 actual student/teacher-PV descendants with80k/320k
node Stockfish searches, at most28.8million new teacher nodes. Do not copy root
scores onto leaves. Preserve mate, checked, terminal, repetition and unstable
cases as unsuitable for finite training. The new eligibility rule permits
quiet endgames as well as middlegames: unlike earlier fits that excluded them,
the reviewed draw directly motivates learning endgame values. Require a valid,
nonchecked, nonterminal position, halfmove clock below70, no twofold repetition,
finite scores within1500cp and two-budget disagreement at most100cp. Further
quiescence/static suitability and group separation are still required before fit.

This is diagnostic development data, not independent strength validation.
Selectedv1.56 remains unchanged. The preceding legal-buffer trial preserved
fixed-work parity but measured only about3% gain and failed its5% promotion gate;
it is not included. Run serially with capacity, STOP, owned-worker and deadline guards.
