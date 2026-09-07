# Cycle08: preserve the search tree while updating position hashes incrementally

Predeclared before implementation or measurement. v1.41 remains selected. Cycle07
completed2W/5D/1L against it,2W/1D/1L at nominal2400 and0W/1D/3L at nominal2600;
neither promotion nor opponent retirement is justified. Three of v1.47's four lost
games first showed a verified losing transition in the middlegame, although all
four ended in an endgame. Useful threat calculation remains a priority.

1. Engine: the current core scans the whole board to reconstruct its Zobrist hash
   after every searched move. Hypothesis: updating only changed pieces, castling
   rights and side to move preserves exactly the same keys and search tree while
   recovering enough search work to improve completed depth at the real clock.
   The cost is not yet measured; passing correctness alone is insufficient.
   Use the original full hash whenever parent or child has a raw en-passant square,
   preserving the existing legal-capture normalisation without a new shortcut.
   Handle captures, all promotions and both castlings explicitly. Never change
   repetition context, halfmove-clock guards, evaluation, pruning or root preferences.
2. Learning: retain the exact selected v1.41 policy and evaluation for this isolated
   code test. Own descendant-value networks already exist experimentally, but no
   additional blend, architecture change or fit is warranted by this hypothesis.
   Better speed may help existing evaluation search farther; actual matches must
   demonstrate any benefit. Do not mix the rejected search or neural experiments.
3. Data: existing verified failures and special-move correctness positions suffice.
   Use the union of stable >=200cp roots from v1.41's rated confirmation and v1.47's
   rated screen, deduplicated by exact starting position plus full history. Preserve
   source identities and all decisions, including errors in games later won.
   No external collection, teacher calls or accepted training labels for this pilot.

Budget and gates:
- One implementation cloned from the exact frozen v1.41 core, plus a development
  driver whose only change is the import name. No unpromoted v1.44 hint code.
- Differential hash checks for every legal child of240 seeded legal positions and
  explicit castling, rook-capture rights, promotion, legal/pinned/irrelevant en-passant
  cases. Check make/unmake restoration and independent full-hash equality. Add mate,
  node-limit and poisoned history/clock search checks using the new core.
- One500,000-node probe per unique audited root per build, with20s ceiling per root.
  Require identical move, score, completed depth and node count, legal/restored boards,
  and node budget reached unless both stop early on the same mate/depth limit.
  Compare elapsed times from these equal-work probes: median baseline/candidate ratio
  must be at least1.10 before spending an ordinary match budget.
- One1s probe per root per build. Require no lower mean completed depth and no more
  repeated original errors. These exposed-root diagnostics do not prove stronger play;
  changing a move is not automatically a correction. Record all outputs and timing.
- If all gates pass, freeze a new one-file runtime variant, require strict read-only
  checks, then run a fixed16-game development screen at120+0.5:8 versus v1.41 and
  8 versus nominal2400, four exposed elite opening pairs each, offset0, both colours,
  at most2 games simultaneously. Then audit every rated own move and report phases.
  Use the pool-aware runner with --levels2400; no new2600/2800/3000 screen this cycle.

Preserve every failed gate without weakening thresholds or repeating unchanged
timing runs. No fresh confirmation, qualification or promotion follows from a speed
gate. Any successful match candidate still needs an independent confirmation plan.
Keep both active opponent levels until the documented consistency gate is satisfied.
