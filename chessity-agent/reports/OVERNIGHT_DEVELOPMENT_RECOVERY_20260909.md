# Saved-game recovery after Windows path failure

At 02:27 BST the first game against nominal 2400 ended in a clean checkmate loss.
The engine initialized in 48.861 seconds. The following review failed while
writing review.json.pending at a 267-character Windows path. This was a review
storage failure after the game, not an engine crash or a replayable game.

Preserve the original failed run, logs and saved game. Copy its exact game-001
and failed result manifest into the new shorter n9-dev-2400 output directory,
record both hashes, and resume feedback. The original first loss is retained;
only the second colour game remains unplayed. Ladder conditions and the playing
candidate remain unchanged. No extra pair or rerun to find wins.

The new feedback_matches_windows adapter calls the unchanged
scripts.feedback_matches.main entrypoint. Its scoped path class enables native
Windows extended paths and excludes live game-001.current.json snapshots from
completed-game scans. It restores the original modules' roots on exit. Atomic
JSON replacement and NumPy model save/load above 280 path characters, completed
game filtering, and restoration on success/failure passed four focused tests.
Existing frozen feedback and engine source files remain unchanged.

The recovery controller has its own state and source manifest, preserves the
same 45-minute bound per pair and reserves it before 06:40 BST. Every game still
receives Stockfish review and a separate experimental learning checkpoint.
Report the candidate as v1.53 logic with compiler repair, separately from the
selected v1.53 release. No promotion or calibrated Elo claim.
