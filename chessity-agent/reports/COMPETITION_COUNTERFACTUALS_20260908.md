# Defensive alternatives and the rook ending

The user requested bounded defensive search and independent descendant labels,
then a small nominal 2400/2600 screen. Only a win against 2600 triggers a 2800
screen. Rated games will use 120s + 0.5s, one colour pair per setting, and will
be scheduled after the targeted work. No long consistency study or Elo promise.

Five newly reviewed real-game roots, eleven forced choices from exact v1.53:

- Round 61 move 26: Qe3 and f3.
- Round 62 move 27: Ne2 and Qe5.
- Round 66 move 28: Ba3 and Bxe3.
- Round 66 move 32: Rxb7 and Qe4.
- Round 68 move 80: Ra1, Rf1 and Re1, retaining the full repetition history.

No engine changes in this diagnosis. Each branch receives one full-window depth
6 probe, at most 500k nodes/8 seconds. Interrupted scores stay null. Trace only
legal exact transposition entries with matching remaining depth, halfmove,
extension credits and quiet-check context; partial traces remain partial.
Combine those endpoints with each budget's independently reviewed best/current
move prefixes of 4/8 plies. Deduplicate by complete history, not FEN alone.
At most 60 endpoints. Each nonterminal endpoint receives one local quiescence
probe, 100k nodes/2 seconds, then independent Stockfish labels at 80k/320k after
the student exits. Requested teacher ceiling 24M nodes; student ceiling 11.5M.
90s initialization, 360s per worker, 0.25s measured-call overhead allowance.
Pass all 27 compiled search arguments and preserve raw timing, node counts,
restoration and compiled signatures before assertions. No unchanged retries.

Explain the actual defensive alternatives and rook plans. Keep terminal,
repetition-sensitive, in-check, unstable and mate labels distinct when preparing
network data. The current 768-piece input lacks history and its runtime value
correction is disabled: independent labels alone do not update the network.
Do not attach a root label to every descendant, blindly increase an old residual
cap, or fit exposed examples and present recognition as generalisation.

Engine code first, useful representable value learning second, these diagnosed
counterfactuals third. Any implementation follows the resulting evidence and a
small quality gate. Preserve v1.53, all archives and both rejected prior trials.
The interrupted cycle38 and deleted overnight automation remain stopped.

Serial CPU, hidden SystemPowerShell NormalPriority4 from launch. Require 2048MiB
free disk and 768MiB physical RAM before every heavy process, at most20 minutes
capacity waiting. New STOP flags interrupt. No concurrent games, teacher or JIT.
