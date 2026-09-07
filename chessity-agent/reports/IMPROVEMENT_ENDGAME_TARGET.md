# Measured next coverage gap: rook and bishop against rook

In nominal2600 confirmation game12, v1.41 (Black) reached:

`5R2/7K/2r5/5k2/3b4/8/8/8 b - - 41 65`

The recorded move was **Ke4**, and the game eventually drew. The independent
[Lichess tablebase API](https://github.com/lichess-org/lila-tablebase/blob/main/README.md)
reports the FEN as a win, precise DTZ19, with **Bf6** the only winning check evasion
among the returned legal moves. Ke4 leads to a tablebase draw. The API takes a FEN
and halfmove clock, not the full preceding repetition history; reconstructed history
shows Bf6 does not immediately allow a draw claim or create a twofold repetition.
This is a specific conversion opportunity, not an actual2600 game victory.

Current runtime tables cover only three pieces. Neither v1.41 nor the reduction-only
candidate fixes this five-piece coverage gap. A complete KRBvKR table and capture
subtables (KRBvK, KRvKR, KRvKB, plus current elementary tables) would address the
whole material class without adding a lookup for one benchmark position.

The complete material class has now been acquired in data/rook-bishop-syzygy-v1:
18 WDL/DTZ files totalling2,960,928 bytes. The main five-piece pair came from the
public Lichess HTTPS mirror and was compared byte-for-byte with the independent
Sesse mirror. Four-piece capture subtables came from pinned python-chess fixtures
with verified Git blob hashes; existing three-piece files were copied with verified
SHA256. Every file has recorded provenance and a computed SHA256. The generator
author's published embedded checksums are recorded, not falsely reported as
recomputed whole-file checksums. The [original Syzygy project](https://github.com/syzygy1/tb)
explicitly permits redistribution of generated table files. No generator or
third-party engine code was downloaded into the candidate.

The helper now accepts a configured maximum of five pieces, falling back to normal
search for missing material classes. A rule-edge test exposed an overly broad
fallback: an uncertain losing move could prevent selecting a separately certified
drawing move. The helper now compares each uncertain move's best possible result
against a certified alternative. A nominal loss near the fifty-move boundary may
be a draw, never a win. Potentially winning ambiguous lines still defer to search.
The frozen v1.41 and running reduction candidate are unchanged.

Nine endgame tests passed in18.95s. They cover40 existing KQK/KRK conversions,
16 additional random won KRBvKR positions against independent WDL-preserving,
DTZ-delaying defence, both colours of the measured check evasion, draw/50-move
boundaries, original scope, missing tables and board restoration. These are
diagnostic drills with a fixed seed and finite sample, not an exhaustive proof.

Replaying the actual100-ply recorded history, the helper chooses Bf6 and reaches
checkmate25 plies later against the same independent tablebase defence, without
allowing a repetition or fifty-move draw. This is an exposed conversion drill,
not an ordinary-game victory over a nominal2600 opponent. No neural weights changed:
this data is used for exact root endgame decisions where the old neural policy
was already disabled.

Frozen experimental build, archived as v1.43: candidates/compiled-rook-bishop-v1, ZIP SHA256
`167b9fb7d3b50f93a650a0fa03d96181b27237fb16d943ef4fdfdd4136fbc280`.
Its ZIP is2,997,110 bytes,3,267,147 bytes uncompressed. Strict read-only/no-network/
no-subprocess validation passed, including actual five-piece decisions: init22.15s,
peak229.7MB, two120000ms clock calls, maximum measured search call3.484s. Other
search, clock and neural-weight files match v1.41. It is experimental until its
ordinary-game screen and a suitable later promotion review.

Raw API response and history check: runs/improvement-loop-20260907/rook-bishop-tablebase-case.json.
Full conversion replay: runs/improvement-loop-20260907/rook-bishop-conversion-probe.json.
The current champion remains v1.41. The consistency target remains unmet.
