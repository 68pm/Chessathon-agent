# chessity-agent

**Recommended competition upload: v1.53 (provisional).** [Download ZIP](latest/chessity-agent.zip).

Bounded checking continuations repair a diagnosed tactical miss. Read-only
validation passed and the 120s + 0.5s comparison scored **1 win, 0 draws, 1 loss
against v1.52**, with no failures on either side. Both Black sides won; this small
pair does not establish overall superiority or calibrated Elo. No neural weights
changed, and v1.52 remains a fallback. Its rated results appear below.

[Current results](reports/IMPROVEMENT_RESULTS.md) ·
[Tactical evidence](reports/NEAR_QUEEN_CHECKS_RESULTS_20260908.md)

Inference is read-only and uses no network or subprocesses. No live competition
submission or repository permission changes occurred. The long study is cancelled.

Latest E55 rated screen: **2400 1W0D1L; 2600 0W1D1L**. [Full results](reports/COMPETITION_CONDITIONAL_RATED_RESULTS_20260908.md).

## Versions

| Version | Build | Status |
|---|---|---|
| [v1](versions/v1/chessity-agent-v1.zip) | Original classical engine | historical; superseded timing implementation |
| [v1.1](versions/v1.1/chessity-agent-v1.1.zip) | Original 50k neural evaluator | experimental |
| [v1.2](versions/v1.2/chessity-agent-v1.2.zip) | Original 50k classical/neural hybrid | experimental |
| [v1.3](versions/v1.3/chessity-agent-v1.3.zip) | Classical attacking-style experiment | experimental |
| [v1.4](versions/v1.4/chessity-agent-v1.4.zip) | Auxiliary style-target experiment | experimental |
| [v1.5](versions/v1.5/chessity-agent-v1.5.zip) | Classical engine with clock fixes | preserved classical baseline |
| [v1.6](versions/v1.6/chessity-agent-v1.6.zip) | 100k neural evaluator | experimental |
| [v1.7](versions/v1.7/chessity-agent-v1.7.zip) | 100k hybrid | experimental |
| [v1.8](versions/v1.8/chessity-agent-v1.8.zip) | 300k neural evaluator | experimental |
| [v1.9](versions/v1.9/chessity-agent-v1.9.zip) | 300k hybrid | preserved value baseline |
| [v1.10](versions/v1.10/chessity-agent-v1.10.zip) | Initial Alien Gambit hybrid | historical forced-opening experiment |
| [v1.11](versions/v1.11/chessity-agent-v1.11.zip) | Revised Alien Gambit hybrid | historical forced-opening experiment |
| [v1.12](versions/v1.12/chessity-agent-v1.12.zip) | Witty-trained 300k hybrid | experimental forced-opening candidate |
| [v1.13](versions/v1.13/chessity-agent-v1.13.zip) | Classical/Witty with optional Alien | experimental |
| [v1.14](versions/v1.14/chessity-agent-v1.14.zip) | Classical/Witty/Magnus policy | preserved former champion; superseded by v1.41 after independent confirmation |
| [v1.15](versions/v1.15/chessity-agent-v1.15.zip) | Phase-pilot ordinary-data control | control ablation |
| [v1.16](versions/v1.16/chessity-agent-v1.16.zip) | Phase curriculum pilot | not promoted |
| [v1.17](versions/v1.17/chessity-agent-v1.17.zip) | Puzzle-pilot ordinary-data control | control ablation |
| [v1.18](versions/v1.18/chessity-agent-v1.18.zip) | Verified puzzle-trained player policy | provisional; see mixed raw/search evidence |
| [v1.19](versions/v1.19/chessity-agent-v1.19.zip) | Full fusion with 300k leaf evaluator | final comparison candidate |
| [v1.20](versions/v1.20/chessity-agent-v1.20.zip) | Full fusion with bounded root value preference | final comparison candidate |
| [v1.21](versions/v1.21/chessity-agent-v1.21.zip) | Fast-chess pilot matched broad-data control | control ablation |
| [v1.22](versions/v1.22/chessity-agent-v1.22.zip) | Hikaru/Gotham verified policy with original clock controller | clock ablation |
| [v1.23](versions/v1.23/chessity-agent-v1.23.zip) | Hikaru/Gotham verified policy with adaptive 120+0.5 controller | see measured pilot promotion decision |
| [v1.24](versions/v1.24/chessity-agent-v1.24.zip) | Three-phase PVS search candidate | PVS search experiment; not promoted after fresh confirmation |
| [v1.25](versions/v1.25/chessity-agent-v1.25.zip) | Elite verified-case seed policy | experimental intermediate checkpoint; not promoted |
| [v1.26](versions/v1.26/chessity-agent-v1.26.zip) | Elite outcome-guided policy after training game 1 | experimental intermediate checkpoint; not promoted |
| [v1.27](versions/v1.27/chessity-agent-v1.27.zip) | Elite outcome-guided policy after training game 2 | validation retained previous checkpoint; identical ZIP to v1.26 |
| [v1.28](versions/v1.28/chessity-agent-v1.28.zip) | Elite outcome-guided policy after training game 3 | experimental intermediate checkpoint; not promoted |
| [v1.29](versions/v1.29/chessity-agent-v1.29.zip) | Elite outcome-guided policy after training game 4 | validation retained previous checkpoint; identical ZIP to v1.28 |
| [v1.30](versions/v1.30/chessity-agent-v1.30.zip) | Elite outcome-guided policy after training game 5 | experimental intermediate checkpoint; not promoted |
| [v1.31](versions/v1.31/chessity-agent-v1.31.zip) | Elite outcome-guided policy after training game 6 | experimental intermediate checkpoint; not promoted |
| [v1.32](versions/v1.32/chessity-agent-v1.32.zip) | Elite outcome-guided policy after training game 7 | experimental intermediate checkpoint; not promoted |
| [v1.33](versions/v1.33/chessity-agent-v1.33.zip) | Elite outcome-guided policy after training game 8 | final outcome candidate; not promoted after fresh comparisons |
| [v1.34](versions/v1.34/chessity-agent-v1.34.zip) | Elite teacher-only matched control | matched teacher-only ablation; not independently promoted |
| [v1.35](versions/v1.35/chessity-agent-v1.35.zip) | Original compiled search preflight | failed Windows import preflight; archival only; do not upload |
| [v1.36](versions/v1.36/chessity-agent-v1.36.zip) | Original compiled classical search | 8W0D0L versus v1.14 in development; not independently promoted |
| [v1.37](versions/v1.37/chessity-agent-v1.37.zip) | Original trained leaf residual evaluator | 2W4D2L versus compiled control; no demonstrated gain; not promoted |
| [v1.38](versions/v1.38/chessity-agent-v1.38.zip) | Compiled search with elementary endgame tables | conversion drills and read-only checks passed; no ordinary matches |
| [v1.39](versions/v1.39/chessity-agent-v1.39.zip) | Incremental residual evaluation | numerical and read-only checks passed; no ordinary matches |
| [v1.40](versions/v1.40/chessity-agent-v1.40.zip) | Efficient quiescence terminal checks | fixed-node parity and read-only checks passed; no ordinary matches |
| [v1.41](versions/v1.41/chessity-agent-v1.41.zip) | Efficient compiled search with endgame tables | Preserved playing-engine baseline and fallback; selected startup revision is v1.51 |
| [v1.42](versions/v1.42/chessity-agent-v1.42.zip) | Conservative late quiet move reductions | 1W5D2L versus v1.41; 2W0D2L at nominal2400; 1W2D1L at nominal2600; not promoted |
| [v1.43](versions/v1.43/chessity-agent-v1.43.zip) | Verified rook-bishop conversion tables | 3W1D4L versus v1.41; 1W2D1L at nominal2400; 0W2D2L at nominal2600; not promoted |
| [v1.44](versions/v1.44/chessity-agent-v1.44.zip) | History-safe transposition move ordering | 2W2D4L versus v1.41; 3W1D0L at nominal2400; 0W0D4L at nominal2600; not promoted |
| [v1.45](versions/v1.45/chessity-agent-v1.45.zip) | Matched score-only residual learning control | six-epoch own-trained control; read-only and model-parity checks passed; experimental |
| [v1.46](versions/v1.46/chessity-agent-v1.46.zip) | Verified counterfactual preference learning | 2W3D3L versus v1.45; 1W2D5L versus v1.41; 1W1D2L at nominal2400; 0W2D2L at nominal2600; not promoted |
| [v1.47](versions/v1.47/chessity-agent-v1.47.zip) | Calibrated quarter-weight learned evaluation | 2W5D1L versus v1.41; 2W1D1L at nominal2400; 0W1D3L at nominal2600; interrupted development audited; not promoted |
| [v1.48](versions/v1.48/chessity-agent-v1.48.zip) | Exact legal-pawn proof speeds quiescence | 0W/1D/1L versus v1.41 at120+0.5; exact-work/speed/read-only gates passed; not selected after the short comparison |
| [v1.49](versions/v1.49/chessity-agent-v1.49.zip) | Queen-aware passed-pawn evaluation | Archival only: 0W0D2L vs41, 0W2D0L vs47, 1W0D1L vs48; two startup losses at2400; 1W1D0L at2600 with opponent flag win; not selected |
| [v1.50](versions/v1.50/chessity-agent-v1.50.zip) | Complete root compilation before readiness | Archival only: readiness and read-only checks passed; instrumented protocol initialization failed; superseded startup experiment |
| [v1.51](versions/v1.51/chessity-agent-v1.51.zip) | Completed warmup with plain compiler diagnostics | Preserved v1.51 startup fallback; provisional tactical recommendation is nowv1.52 |
| [v1.52](versions/v1.52/chessity-agent-v1.52.zip) | Bounded check search and coordinated king-pressure evaluation | Provisional:1W0D1L vs51; rated2400 0W1D1L and2600 0W0D2L; no Elo established |
| [v1.53](versions/v1.53/chessity-agent-v1.53.zip) | Bounded forcing checks near the enemy king | Provisional: 1W0D1L vs52; rated2400 0W1D1L and2600 0W0D2L; no calibrated Elo |

All 54 numbered versions are retained chronologically. A higher version number alone is not evidence of strength.

[Recent competition losses and draw: old/current comparison, verified cases and rejected fixes](reports/COMPETITION_LOSSES_RESULTS_20260908.md). Recommendation remains v1.53.

[Defensive/rook descendant findings](reports/COMPETITION_COUNTERFACTUALS_RESULTS_20260908.md) · [Requested 2400/2600 and conditional 2800 results](reports/COMPETITION_CONDITIONAL_RATED_RESULTS_20260908.md).

Latest loss/draw review: two implemented heuristics and an actually fitted
local-value model did not qualify for promotion. The small requested rematch
and every failure are recorded in the [learning report](reports/E55_LOSSES_DRAW_AND_LEARNING_20260908.md). v1.53 remains
the recommended upload; no new version is implied by this experiment.

Every-game feedback is now the default local test workflow. [Latest competition review and learning results](reports/ALL_GAME_FEEDBACK_RESULTS_20260908.md) cover all 395 moves in eight games. The reward-policy checkpoint remains experimental; v1.53 remains the recommended upload.

[Overnight first-pass checkpoint,9September](reports/OVERNIGHT_FIRST_PASS_20260909.md): completed engine trials, independent value fit and638 reviewed competition moves. No successor qualified at this checkpoint; v1.53 and all54 archives remain unchanged.
