# Defensive continuations: why the current leaf values are insufficient

The corrected diagnostic completed on8September at16:09:49BST using unchanged
v1.53. It exposes missed opponent continuations and large errors in some of their
descendant values. It does not provide a new model, played win or Elo estimate.

| Forced depth6 choice | Root-side score | Completed |
|---|---:|---|
| 10...Nc6 | +134cp | Yes |
| 10...Kh7 | +37cp | Yes |
| 14.Qb3 | -56cp | Yes |
| 14.h3 | -78cp | Yes |
| 19...Bh4 | Unavailable | No:500k-node cap |
| 19...Be6 | +50cp | Yes |

The two completed pairs still prefer the played mistakes at a full window with
policy disabled. No conclusion is drawn from the incomplete Bh4 score. Three
exact traces reached quiescence; Kh7 and Be6 stopped at missing/nonexact table
entries and remain explicitly partial. All23 endpoint quiescence probes completed.
Total student work was1,245,567 nodes; initialization73.924seconds. Every measured
call retained its node/wall/restoration data and added zero compiled signatures.
All state, accumulator and history checks passed. The longest probe was3.190s.

Independent80k/320k review of all23 actual-history endpoints requested9.2million
teacher nodes. All scores were finite. Nine endpoint discrepancies exceeded125cp
at both budgets; eight exceeded200cp and four exceeded500cp. These are local
quiescence-versus-teacher discrepancies, not direct errors of every root move.

| Example endpoint, root perspective | Student q | Teacher80k /320k |
|---|---:|---:|
| Nc6 student line after Bxh6 Nxd4 Qg5 Ne6 Qg3 | +134 | +122 /+173 |
| Partial Kh7 line after Rg1 Nc6 Be3 Kg8 | +37 | -694 /-786 |
| Nc6 counterfactual after Bxh6 e5 Rg1 | +58 | -241 /-218 |
| Qb3 student line after Bxf3 gxf3 Bd4 Qb5 Ne5 | -56 | -29 /-12 |
| Qb3 counterfactual after Bxf3 gxf3 a4 | +112 | -409 /-406 |
| Bh4 counterfactual after Bd3 Be6 O-O | +50 | -385 /-405 |
| Bh4 counterfactual after Bd3 Be6 O-O Rc8 Ra1 Qc5 Qh6 | +185 | -541 /-507 |

The first and fourth rows show why training only the student's imagined line is
misleading: those particular endpoints are approximately valued correctly. The
opponent can choose a stronger continuation that the search does not appreciate.
Root labels must not be copied onto these leaves.

Descriptive king-file pawn counts and absolute pins do not explain everything.
The Nc6 student endpoint and its Rg1 counterfactual both have Black's king on g8,
no pawn on the g-file and a pinned bishop on g7, but their independent values
differ substantially. Similarly, some Qb3 endpoints have a damaged pawn shield
and an accurate student value while others are badly overvalued. A blanket
penalty for a missing king-file pawn would damage correctly valued examples.
Queen/rook/bishop coordination, blocked lines and available defences matter.

Engine work should address those distinctions. For useful learned evaluation,
the earlier effective125cp correction range is inadequate for these diagnosed
cases; even a500cp correction cannot reach four endpoints. Any next fitting
experiment needs a newly specified, representable objective, counterfactual
coverage and a matched control. Simply increasing the blend/cap or repeating
epochs is not justified. These23 positions and the prior reviewed games are
targeted development data, with whole game/opening relationships retained.

The preceding cycle36 attempt initialized in73.704seconds but failed its first
combined node/wall assertion before recording a branch. Its exact cause cannot
be recovered from the missing raw measurements. It omitted the two new optional
compiled-search arguments; cycle37 passed all27 arguments explicitly, matching
the successful earlier proof, and saved diagnostic measurements before assertions.
All original36 sources, plans and failure logs remain preserved. No teacher
samples or completed games were repeated, and no limit was relaxed.

Both diagnostic tasks have finished and were removed after their exits and lack
of owned processes were verified. The selected v1.53 ZIP and all54 archives are
unchanged. No neural fitting or new package was performed in either diagnosis.

[Original diagnostic](IMPROVEMENT_CYCLE_36.md) ·
[Corrected call rules](IMPROVEMENT_CYCLE_37.md) ·
[All results and failures](evidence/defensive-descendants-20260908/manifest.json)
