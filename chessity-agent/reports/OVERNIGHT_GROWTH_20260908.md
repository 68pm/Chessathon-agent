# Overnight Chessity development: 7–8 September 2026

The user authorized continued development overnight and requested a report and
the strongest verified downloadable agent around **07:20 BST on 8 September
(06:20 UTC)**. The aim is practical strength approaching nominal 2800–3000, not
merely collecting one win. No outcome or calibrated rating is promised.

The existing Codex heartbeat runs hourly at :20 and :50. It performs both continued
development and the 07:20 report; there is no second delivery automation. At 06:50
prepare the final report and package. Stop speculative new branches by 05:45 BST.
The machine must remain available for local work and scheduled follow-ups.

## Fixed starting point

- Selected v1.41: `candidates/compiled-qsearch-endgames-v1`.
- ZIP SHA256: `e4b66bd0f5a16418a49119c0547a818c3bb79a3c9e209b3eca7210907e072f63`.
- All 50 released archives through v1.49 remain preserved. v1.49 is experimental.
- The ten-game cycle15 and failed mistake-replay cycle16 are complete. Do not
  repeat unchanged training or games, or resume the abandoned 256-game study.
- Latest saved competition rounds54–56 have v1.41 attribution inferred. Browser
  retrieval of newer games was blocked; do not claim new dashboard data.

## Initial bounded work

1. Baseline v1.41: **four games total**, one colour pair at nominal2800 and one
   at nominal3000, 120+0.5. Use prepared start index5, C58 Two Knights Polerio,
   chosen before outcomes. These are diagnostics, not rating certification.
   Record every result, startup failure and flag, then audit the games and phases.
2. Cycle17: implement an original root aspiration-window pilot, based only on41.
   It narrows the search around the prior completed iteration's score, widens on
   fail-high/low, and preserves the last completed result on interruption. Preserve
   root policy bonuses, mate scores, history, board state and terminal rules.
3. Before timing, check full-window score parity and window bounds, widening,
   mate/promotion/repetition and node-limit fallback. Use existing verified roots
   for a cheap two-pass clock comparison. Reject added tactical errors, unsafe
   bounds, or no useful depth/choice benefit; don't run games for a failed gate.
4. A passing candidate gets one colour pair against41 on the next unused prepared
   opening family. Require no operational failures and at least50% score, together
   with the earlier position and read-only gates, before one small follow-up.
   A promising survivor gets a fixed eight-game follow-up: four against41 across
   two opening families, two nominal2800 and two nominal3000. Preserve all results;
   do not extend the schedule to chase a win. Before those games, declare the
   practical release rule, including how inconclusive results are handled.

## The three needs for cycle17

**Engine:** the actual round55 Rc1 defence appeared at greater depth than the root
could finish. Aspiration may reduce search work without speculative pruning.
It is a hypothesis, not an established fix. Startup margin is also monitored:
v1.49 previously failed twice despite a successful separate preflight.

**Learning:** keep the selected policy and classical leaf values fixed to isolate
search. The existing incremental residual network remains available for a later
diagnosed change; cycle16 showed lower static loss alone did not improve held-out
root decisions. No blind repeat of that fit is authorized by this plan.

**Data:** existing verified errors and cached labels are sufficient for this pilot.
Use the new high-opponent games to identify the first deterioration and its phase,
then choose any further training signal or data extraction from that evidence.

## Night and morning operation

Use hidden service-owned Windows tasks, local CPU only, maximum two simultaneous
timed games. No heavy teacher, JIT timing or training during timed matches. Respect
STOP_TRAINING and STOP_BENCHMARK. Never stop unrelated processes. Preserve frozen
sources and configs and record controller paths in `work/improvement-active.md`.

Launch diagnosis at22:20–22:42BST: the original parallel batch produced three
saved candidate init losses and an uncaught opponent startup exception, with zero
played moves. All are retained under overnight-baseline-01 and its controller's
recovery.json. The serial successor records startup exceptions and stderr and
waits for768MiB available RAM before each game; use `scripts.overnight_matches`.
Its independent `audited()` supports the declared one-worker protocol; the older
`improvement_review.audited()` insists on two workers and must not be used here.

Background launchers were observed at BelowNormal priority with negligible CPU
time while their threads were ready. Task Scheduler defaults to priority7. The
two new overnight tasks now use priority4 (Normal), with ordinary full CPU affinity;
no unrelated process was changed. This is an operational amendment, not engine
strength evidence. Compare candidates and baseline under the same new conditions.
Use the Windows system PowerShell hidden wrapper launchers in work. Earlier
pythonw and bundled-PowerShell launch attempts were stopped after ownership
checks before a controller or game started. The separate headless service module
is preserved as diagnostic code, not the current launch path.

Each follow-up reviews completed work, rejects failed ideas cheaply, and undertakes
the next justified small change. No large consistency study, indiscriminate game
download, live competition submission, paid compute, or external engine/weights
inside the submitted runtime. Claude was cancelled.

By07:05 BST prepare `outputs/chessity-overnight-report-20260908.md`, best
`outputs/chessity-agent.zip`, the exact selected version and hash, W/D/L by opponent,
termination types, strongest opponent actually beaten, changes and remaining gaps.
Publish justified chronological versions and evidence to the authorized GitHub
repository. If no candidate qualifies, deliver41 with that finding explicitly.
At07:20 send the report and download even if some work is unfinished, then record
delivery and update the same heartbeat for the continuing competition deadline.
