# Chessity morning report — 8 September 2026

**Best recommended upload: v1.41. No stronger overnight candidate qualified.**
The overnight work did not establish 2800–3000 strength. This final report is
being delivered after the requested 07:20 time; the earlier saved report was
explicitly an interim draft.

[Download the selected agent](../latest/chessity-agent.zip)

Selected ZIP SHA256:
`e4b66bd0f5a16418a49119c0547a818c3bb79a3c9e209b3eca7210907e072f63`.
The local generic and v1.41 versioned downloads were rechecked and match.
The selected build retains its prior strict read-only validation; no fresh
runtime test of it is claimed this morning.

## Results at 120 seconds plus 0.5 seconds

| Dataset and opponent | Wins | Draws | Losses | Interpretation |
|---|---:|---:|---:|---|
| Earlier v1.41 confirmation vs v1.14 | 23 | 1 | 0 | Historical promotion evidence |
| Earlier v1.41 confirmation, nominal 2400 | 3 | 4 | 1 | Separate historical sample |
| Earlier v1.41 confirmation, nominal 2600 | 0 | 3 | 5 | Separate historical sample |
| Later short v1.41 check, nominal 2400 | 0 | 0 | 2 | Both checkmates |
| Later short v1.41 check, nominal 2600 | 1 | 0 | 1 | Both checkmates |
| Overnight serial v1.41 attempts, nominal 2800 | 0 | 0 | 2 | One init failure, one first-response flag |
| Overnight serial v1.41 attempts, nominal 3000 | 0 | 0 | 2 | Two init failures |

**Strongest nominal opponent beaten by the selected build: 2600**, by checkmate
in the earlier short check. It did not beat 2800 or 3000 overnight. The four
overnight serial attempts produced zero played moves, so they do not measure
chess strength or provide tactical training examples. The separate earlier
parallel attempt also failed operationally: three saved initialization losses
and one opponent handshake exception. Its incomplete aggregate is preserved.

The nominal Stockfish settings are not a calibrated rating for Chessity. These
separate, small samples do not support a reliable new Elo estimate or consistent
2600 strength. Saved actual competition rounds54–56 scored 2W/1D/0L, with v1.41
attribution inferred; no newer dashboard games were obtained.

## What improved in the development work

- A deterministic test exposed a startup warmup deadline bug. Its separate fix
  passed three focused tests and a strict read-only check, but failed the actual
  background protocol. That candidate remains unselected.
- The captured failure identified native Colorama console conversion during
  Numba diagnostics. A separate plain-diagnostics candidate passed two focused
  checks and was packaged. Its runtime validation remains unfinished.
- The aspiration-search prototype passed nine correctness checks. Disk exhaustion
  prevented saving its first baseline measurement; no speed or strength gain is
  claimed, and the failed attempt was not rerun unchanged.
- A lightweight review found that 14 of 18 replay endpoint targets exceed the
  experimental network's permitted 125cp correction; two requested pair margins
  are mathematically unreachable. Four targeted-model endpoints saturate the
  output clip, versus none for its matched control. This is a useful learning
  diagnosis, not a new fit or proof of the sole cause of the failed pilot.

## Why work stopped and what comes next

Heavy validation stopped after the disk guard expired at00:16 BST. No training
or matches continued behind that failed controller. At07:14, disk space had
recovered to about3.6GiB, but available physical memory was only450MiB, below the
768MiB guard. The attempted capacity check therefore did not restart the job.
No unrelated apps, user files or pagefile settings were changed.

Resume the existing plain-diagnostics validation only when both resource guards
pass. Then return to useful defensive search and short practical comparisons.
Before another neural fit, make its targets compatible with the runtime's allowed
corrections and use a matched control. Existing verified mistakes are sufficient;
another broad game download would not repair the current runtime or learning
limitations. The abandoned long consistency study remains stopped.

GitHub retains all50 numbered versions throughv1.49, with v1.41 selected. The
startup candidates, source, tests and failure evidence are archived as unselected
development experiments, without new release numbers. See the
[overnight evidence](OVERNIGHT_PROGRESS_20260908.md) and
[learning diagnosis](LEARNING_REACHABILITY_REVIEW.md).
