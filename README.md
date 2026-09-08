# Chessathon-agent

[Download chessity-agent v1.52 (provisional recommendation)](chessity-agent/latest/chessity-agent.zip) ·
[All53 versions](chessity-agent/README.md) ·
[Results and limitations](chessity-agent/reports/IMPROVEMENT_RESULTS.md)

v1.52 adds tested engine search/evaluation repairs. The small120+0.5 comparison
finished **1 win,0 draws,1 loss againstv1.51** with no failures. Tactical mistakes
repeated on the diagnostic clock roots fell from14/17 to8/17. Read-only validation
passed. No calibrated Elo or overall superiority is established; v1.51 remains
a fallback. Its completed rated screen scored0W1D1L at nominal2400 and0W0D2L at2600, with no failures.

The priority is quick practical improvement for the11September competition.
No long consistency study, repository write-access grants or live submission.

[Tactical evidence](chessity-agent/reports/TACTICAL_PILOT_29_20260908.md) ·
[Previous startup results](chessity-agent/reports/STARTUP_RECOVERY_RESULTS_20260908.md) ·
[Historical morning report](chessity-agent/reports/OVERNIGHT_REPORT_20260908.md)

[Completed rated results and diagnosis](chessity-agent/reports/KING_COORDINATION_RATED_RESULTS_20260908.md).

[Full-window first-warning diagnosis](chessity-agent/reports/FIRST_WARNING_SEARCH_TRACE_20260908.md): all three loss choices remain preferred at depth6; depth8 attempts hit their fixed node caps. No agent changed.

[Root PVS pilot](chessity-agent/reports/ROOT_PVS_RESULTS_20260908.md): 24.92% fewer fixed-depth nodes, but all 21 clock-limited choices unchanged; prototype not selected.

[Tactical descendant diagnosis](chessity-agent/reports/TACTICAL_DESCENDANT_DIAGNOSIS_20260908.md): missing opponent defenses and independently measured endpoint value errors; v1.52 unchanged.

[Forcing-check diagnosis](chessity-agent/reports/FORCING_CHECK_DIAGNOSIS_20260908.md): Kh1 was correct; the later rook captures permit a verified mating sequence omitted by shallow search. Agent unchanged.

[Near-queen checks tactical gate](chessity-agent/reports/NEAR_QUEEN_CHECKS_RESULTS_20260908.md): both missed mating sequences found and the Bxf2+ root repaired; this gate alone does not establish game strength.
