# Why the first value fit remains experimental

This diagnosis uses the31already evaluated descendant predictions saved by the
failed first fit. No new inference, teacher labels, fitting or games were run.

| Stage | Positions | Classical MAE | Corrected MAE | Improved / worsened |
|---|---:|---:|---:|---:|
| Opening | 6 | 46.42cp | 72.78cp | 1 / 5 |
| Middlegame | 17 | 308.21cp | 249.85cp | 12 / 5 |
| Endgame | 8 | 174.94cp | 235.90cp | 0 / 8 |
| All | 31 | 223.15cp | 211.98cp | 13 / 18 |

The aggregate5%error reduction concealed worse estimates in every sampled endgame
and most openings. The correction's600cp range is not the main explanation: only
one target exceeded that range, and none of the endgame targets did. One source
group improved while the other worsened, so this small fit has uneven transfer.

Stages are descriptive: non-pawn phase N/B=1,R=2,Q=4, with<=8classified as endgame;
otherwise fullmove<=15and phase>=18is opening; remaining positions are middlegame.
These are small, correlated groups and do not establish stage-specific Elo.

This is development evidence for a future phase-aware learning hypothesis. Do not
disable corrections selectively using these scores and present the same positions
as fresh validation. A revised fit needs separately reserved game groups and a
runtime cost/choice check before playing strength claims. The current upload keeps
its previous weights and evaluation.

Sources: scripts/overnight_value_diagnosis.py and
runs/overnight-20260909/rule-value-diagnosis-01/diagnosis.json, including exact source
hashes, individual residuals and source-game groups.
