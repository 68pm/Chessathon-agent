# chessity-agent

**Best verified upload: v1.14 — Classical/Witty/Magnus policy.**

[Download the competition ZIP](latest/chessity-agent.zip). Upload the agent ZIP directly.

The phase and elite-learning experiments are complete. The final outcome candidate v1.33 scored **1W/1D/14L at 2400** and **0W/5D/11L at 2600**, and lost its direct comparison against v1.14. Highest individual winning setting: 2400. Consistent 2400/2600 wins were not achieved. All tests use 120+0.5; nominal engine settings are not a human/site Elo.

[Full delivery](reports/DELIVERY.md) · [Elite learning and rewards](reports/ELITE_LEARNING_RESULTS.md) · [Phase search results](reports/THREEPHASE_RESULTS.md)

## Read-only runtime and repository access

The selected package passed blocked file-creation, deletion, renaming and directory-creation checks. Inference requires no writes, network or subprocess. Training tools write their own checkpoints. Public visitors can read and download; edits require repository write permission. No collaborator or public write grants were added.

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
| [v1.14](versions/v1.14/chessity-agent-v1.14.zip) | Classical/Witty/Magnus policy | best verified upload after completed phase and elite comparisons |
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

All 35 versions have chronological development commits and annotated version tags. Source and own trained weights beside each ZIP match its bytes. v1.27/v1.26 and v1.29/v1.28 are intentionally identical after validation rejected those updates. Newest v1.34 is the matched teacher-only control, not the recommended upload. Downloaded raw histories, supplied source packs and external engine executables are not included.
