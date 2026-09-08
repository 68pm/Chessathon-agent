# Chessathon-agent
Chessathon agent team verity made for the  AI Chessathon x Optiver event, uploaded all the different version onto this repo tracking the development and progression

## chessity-agent releases

[Download the selected agent (v1.51)](chessity-agent/latest/chessity-agent.zip) ·
[All 52 versions](chessity-agent/README.md) ·
[Results and limitations](chessity-agent/reports/IMPROVEMENT_RESULTS.md)

v1.51 retains v1.41's playing engine and trained policy while fixing startup
completion and compiler diagnostic handling. Read-only checks and four ordinary
games passed without candidate runtime failures. At120+0.5 it scored0W/1D/1L
against each nominal2800 and3000 setting. This is a practical startup revision,
not proof of higher playing Elo. v1.41 is preserved as a fallback.

The11September competition priority is quick, useful improvements from diagnosed
mistakes. No long consistency study is running. Public visitors can read/download;
no repository write-access grants or live competition submissions were made.

[Earlier morning report](chessity-agent/reports/OVERNIGHT_REPORT_20260908.md) ·
[Latest startup results](chessity-agent/reports/STARTUP_RECOVERY_RESULTS_20260908.md) ·
[Learning diagnosis](chessity-agent/reports/LEARNING_REACHABILITY_REVIEW.md)

[Latest search results](chessity-agent/reports/CHECK_EXTENSION_RESULTS_20260908.md): the bounded check-extension pilot failed its tactical gate. Selected upload remains v1.51.

[Rook-regression diagnosis](chessity-agent/reports/ROOK_REGRESSION_DIAGNOSIS_20260908.md): full-window values confirm a horizon-dependent preference; no new upload is selected.

[Direct-check ordering pilot](chessity-agent/reports/DIRECT_CHECK_ORDER_RESULTS_20260908.md): tactical gate failed; selected upload remains v1.51.

[Pawn-proof/check-extension combination](chessity-agent/reports/PAWN_CHECK_RESULTS_20260908.md): gate failed; selected upload remains v1.51.

[Queen-aware evaluation with bounded check search](chessity-agent/reports/TACTICAL_PILOT_27_20260908.md): gate failed; selected upload remains v1.51.

[Rook-refutation features](chessity-agent/reports/ROOK_REFUTATION_FEATURES_20260908.md): a cheap existing-data review suggests inspecting queen-supported coordination; no new upload selected.
