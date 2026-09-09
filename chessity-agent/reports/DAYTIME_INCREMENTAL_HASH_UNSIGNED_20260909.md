# Isolated incremental hashing on v1.42 — 9 September

Test the retained exact v1.42 with EP-complete incremental position keys only.
Keep full recomputation as an independent oracle and for actual game histories.
The previous pure hash pilot retained a full-board raw-EP fallback and failed
its timed quality gate; the later EP-complete integration also changed root
scouts on v1.53. This experiment removes that second variable and uses v1.42.

Do not change search windows, root scoring, ordering, evaluator, network,
repetition context, halfmove checks, clock allocation or compiler settings.
Special-move tests cover legal/pinned/irrelevant en-passant, castling, captured
rook castling rights, captures, all promotions, both colours and board restoration.
Compare all legal children in 240 seeded positions to full recomputation.

Use the existing 12 reconstructed development roots. Import each production
agent once under the actual 90-second limit, then alternate ABBA in two regimes:
100,000 nodes with a 12-second safety cap, and 1 second of clock search. Only one
worker searches at a time. Clear all search caches and preserve replay history.
Require identical fixed-node move, score, depth and nodes, completed node budgets
or identical early terminal stops, at least 1.05 median and aggregate CPU ratio,
and no reduction in mean timed depth. This is an efficiency screening threshold,
not a playing-strength claim. Timed choice review must follow before games.

Keep the prepared source, input hashes and all outcomes immutable. No unchanged
retry after failure. Successful efficiency measurements permit targeted teacher
checks and the user's short playing test; they do not automatically promote or
upload a release. Use the new daytime capacity and deadline checks. Freeze the
playing candidate through all tests, and retain exact v1.42 pending qualification.

The first daytime unit run reproduced the old signed-integer Python/JIT
boundary issue: identical 64-bit keys were boxed negative instead of unsigned.
It stopped before any benchmark or games (7 failed, 6 passed in 5.10 seconds).
Preserve that run. This revision explicitly converts both parent key inputs
and the output to uint64, using the corrected representation already recorded
in overnight_hash_scout_fixed.py. No other algorithm or gate changes.
