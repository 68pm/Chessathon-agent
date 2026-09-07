# Overnight progress: 8 September 2026

Interim findings after the capacity guard stopped at00:16 BST. The requested
07:20 report is still due; this is not a final delivery or a claim that work
continued while the computer was unable to run it.

**Recommended upload remains v1.41.** No overnight candidate has qualified to
replace it, and actual2800-3000 playing strength has not been demonstrated.
Selected ZIP SHA256:
`e4b66bd0f5a16418a49119c0547a818c3bb79a3c9e209b3eca7210907e072f63`.

## What the opponent tests actually showed

All games used120 seconds plus0.5 seconds per move. The complete serial batch
used one prepared C58 position in both colours at each nominal Stockfish setting.

| Opponent setting | Wins | Draws | Losses | What happened |
|---|---:|---:|---:|---|
| 2800 | 0 | 0 | 2 | One initialization failure; one first-response timeout |
| 3000 | 0 | 0 | 2 | Two initialization failures |

There were **zero played moves** in these four attempts. They measure operational
failures, not opening, middlegame or endgame strength. No training examples can
be extracted from moves that were never played. A separate earlier parallel
attempt produced three saved initialization losses and one opponent startup
exception; its incomplete aggregate and individual failure records are preserved.

The strongest nominal opponent beaten in the selected agent's earlier short
check was2600, by checkmate. That two-game set scored1W/0D/1L; the earlier
eight-game confirmation at2600 scored0W/3D/5L. At2400, the earlier confirmation
scored3W/4D/1L and the later short check0W/0D/2L. Keep these samples separate.
These handicap settings and small samples do not establish a calibrated Elo.

## Completed useful work

- **Startup readiness:** a deterministic test exposed a warmup deadline bug.
  If setup takes over60 seconds, v1.41 can announce readiness without compiling
  its root search. The startup-complete candidate preserves its one-depth and
  4096-node limits while leaving the external90-second initialization watchdog
  in control. Three regression tests passed.
- **Runtime check:** that candidate passed strict read-only validation with
 42.105-second initialization and two legal calls, but then failed the actual
  background protocol. The stderr trace showed a native access violation in
  Colorama's Windows console conversion during Numba diagnostics. It is not
  promoted, and this trace does not explain every earlier failure.
- **Plain diagnostics:** a separate candidate uses Numba's supported option to
  bypass console highlighting while preserving errors. Two tests passed,
  including an isolated check that forbids Colorama initialization. It is
  packaged but has not completed strict read-only or actual protocol validation.
- **Useful search depth:** the aspiration-window pilot passed nine correctness
  checks. Its first measured baseline output failed with an explicit disk-full
  error. The zero-byte result, original context and logs remain intact; there is
  no usable position gate result or demonstrated speed gain.

Current disk availability was below1GiB. The new guard stopped after20 minutes
because it requires2GiB free disk and768MiB available memory before heavy work.
No user files were deleted, unrelated apps closed or pagefile settings changed.
Repeatedly launching the same blocked workload would not improve the agent.

## The next three priorities

1. **Engine:** restore enough disk space, validate the plain-diagnostics candidate
   under strict read-only and actual protocol checks, then return to useful
   defensive search. Do not repeat nominal matches until initialization works.
2. **Learning:** retain the current weights during runtime repairs. The completed
   mistake-replay pilot did change parameters, but its final candidate did not
   outperform the equal-compute control on held-out roots. Further identical
   epochs are not justified by that result.
3. **Targeted data:** existing audited quiet-defence and conversion errors remain
   the relevant targets. No new broad GM download is needed to repair startup or
   storage. Obtain new build-specific mistakes only from completed legal games.

If capacity returns, resume the same cycle19 controller from its capacity stage,
preserving the passed tests and package. Any subsequent aspiration comparison
must be separately declared with consistent working startup conditions, retaining
the failed original attempt. Use small practical tests for a passing change.

The two startup candidates are archived as unselected development experiments,
without new release numbers or a claim that the latest upload changed. All50
numbered versions throughv1.49 remain preserved. See the matching source,
hash manifest and failure evidence accompanying this report.

A later lightweight [learning review](LEARNING_REACHABILITY_REVIEW.md) found that
14 of the replay pilot's 18 endpoint targets exceed its permitted 125cp correction,
and two requested pair margins are unreachable under that cap. Four final targeted
endpoints saturate the hard output clip, versus none for the matched control.
This identifies a training-objective limitation to address before another fit;
it is not new training, a proven sole cause of the failed pilot or an Elo gain.
