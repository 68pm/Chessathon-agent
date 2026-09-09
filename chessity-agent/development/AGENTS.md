# Chessity project instructions

The user wants rapid competition improvements and small practical checks.

- Review every new local test game, including wins, draws and losses, using the
  history-aware Stockfish feedback pipeline. Schedule future rated and version
  comparison games through `python -m scripts.feedback_matches` with the same
  arguments as `scripts.overnight_matches`. Do not bypass the review step when
  introducing another game runner. Import downloaded competition PGNs through
  `scripts.feedback_batch` as completed game records with explicit candidate
  colour and honest version attribution.
  On Windows use `python -m scripts.feedback_matches_windows`; it calls the
  unchanged feedback entrypoint with extended paths and excludes live snapshots
  from completed-game scans. This fixes the recorded September9 review path
  failure while preserving frozen engine and feedback sources.
- Reviews reinforce independently supported good moves and prefer verified
  alternatives to mistakes. Game result and opponent Elo must not determine
  move rewards. Preserve uncertain/mate scores and replay histories; do not
  turn an engine mate estimate into a made-up centipawn label.
- Reward-weighted policy checkpoints are experimental. Preserve the selected
  upload until a small practical comparison demonstrates improvement. Runtime
  inference stays read-only, with no Stockfish, networking or training included.
- Root move rewards belong to policy learning. Position-value training requires
  independently labelled, suitable descendant positions; never copy a root
  evaluation onto an imagined leaf. Review engine/search weaknesses first,
  then value learning, then targeted data needs. A policy fit alone is not a
  solution to defective search or endgame evaluation.
- Keep different submission hashes separate. Once a game is used for training,
  label it development data; its replay is not independent strength evidence.
- Use the established 120s + 0.5s competition clock. Avoid long independent
  consistency studies. Run CPU-heavy engines and training serially, with the
  existing capacity and STOP checks; do not change other applications or OS
  memory settings. Preserve frozen sources and failed attempts.
- Do not resume the cancelled overnight automation or stopped cycle 38. These
  instructions do not create a scheduler or authorise endless background work.

For the explicitly authorised 8–9 September overnight run, follow
`../../work/overnight-20260909.md`: search efficiency, move selection/defence,
independent descendant-value learning, then field preparation, in that order.
Use a new bounded run, small colour-balanced checks, and conditional ascent after
a clean played win. Prepare the best retained ZIP and exact results for07:20 BST
on9September; stop starting heavy work at06:40. Earlier cancelled jobs stay stopped.
