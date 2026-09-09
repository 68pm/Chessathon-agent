"""Write the completed, non-promotion report from the audited progression results."""
import json
from pathlib import Path
from scripts.progression_common import ROOT, RUN, digest


def run():
    final = json.loads((RUN / 'session-audit.json').read_text())
    assert final['status'] == 'complete' and not final['challenger_qualified']
    assert digest(ROOT.parent / 'chessity-agent.zip') == final['incumbent_sha256']
    groups = final['groups']; c = groups['challenger-versus56']
    rows = '\n'.join(f"| {label} | {g['wins']} | {g['draws']} | {g['losses']} |"
        for label, g in groups.items() if label != 'challenger-versus56')
    table = '\n'.join(f"| {t['name']} | {t['mean_regret_cp']['baseline'][0]:.2f} / "
        f"{t['mean_regret_cp']['baseline'][1]:.2f} | {t['mean_regret_cp']['prototype'][0]:.2f} / "
        f"{t['mean_regret_cp']['prototype'][1]:.2f} | {'Tactical gate passed; see matches' if t['passed'] else 'Rejected'} |"
        for t in final['trials'] if 'mean_regret_cp' in t)
    public_rows = '\n'.join(f"| {r['label']} | [Round {r['round']}]({r['url']}) | {r['opponent']} | "
        f"{r['score']:g} | {r['own_moves']} | {r['rewarded']} | {r['penalised']} |"
        for r in final['public_reviews'])
    public_moves = sum(r['own_moves'] for r in final['public_reviews'])
    text = f"""# Chessity progression results — 9 September

**Keep v1.56.** The new root-verification challenger scored **{c['wins']} wins, {c['draws']} draws and {c['losses']} loss(es) against exact v1.56**. It did not clear the predeclared promotion gate. No v1.57 was created, the upload alias is unchanged, and no new competition submission was made by this batch.

## Completed games

All games used 120 seconds + 0.5 seconds. Each pair reversed colours from the same preset opening. The candidate remained frozen while each completed game received Stockfish review and a separate experimental reward-policy fit.

| Match label | Wins | Draws | Losses |
|---|---:|---:|---:|
{rows}

`v156-development2400` is the selected v1.56 playing the nominal 2400 Stockfish setting in the Caro-Kann Advance Short. The `versus56-*` rows belong to the new challenger, playing exact v1.56. Keep these identities separate. The challenger needed at least 5/6 points across three fresh opening pairs, at least 1/2 in each pair, and wins with both colours. It finished with 4/6 points. Promotion became impossible after game five; the scheduled colour reversal was completed and reviewed. No rated stage was started. Rated qualification would then have required at least 1/2 at nominal 2400 and 0.5/2 at nominal 2600; 2800 required a clean 2600 win. A small practical screen does not establish a calibrated Elo or prove universal strength.

## Engineering and learning

| Isolated search/evaluation trial | Baseline mean move regret at 80k /320k, cp | Candidate mean regret, cp | Decision |
|---|---:|---:|---|
{table}

Each row has its own interleaved, equal-clock comparator. These are exposed development positions, not an independent strength sample. Absolute means should not be merged across trials: runtime timing varies, and root-verification specifically used a 1s hard clock and 0.6s soft clock for both builds. The earlier probes used their declared protocol. The quality gate required at least 10% lower mean regret at one teacher budget, no increase at the other, and no new major or mate-loss regression.

Root verification keeps the three highest root-search bounds from the last completed full-root depth, including its selected move. If clock reserve remains, it compares those moves one ply deeper. It preserves the original completed result if interrupted. Full-root depth and the selective verification depth are reported separately. Only 4/24 candidate development probes completed that extra comparison. Their move-order bounds are not independent MultiPV values or suitable teacher labels. The tactical result qualified it for games, but did not prove that this mechanism caused the improvement or that it was stronger overall. Read-only package validation and all 11 correctness tests passed before playing.

The other engine trials tested root principal-variation probes, full-depth protection for late quiet moves in wide windows, and excluding enemy-pawn-controlled squares from mobility bonuses. Each introduced tactical regressions and stayed experimental.

For position learning, 12 bounded forced branches from six reviewed mistakes produced 66 descendant positions. Stockfish independently evaluated them at 80k/320k requested node budgets: 53 were eligible labels, and 40 new quiet, nonduplicate positions joined the fit. No root reward was copied onto an imagined future position. One diagnostic continuation after v1.56’s 35.h5 was evaluated at +226cp by its static evaluator but about −379cp by the independent teacher. This exposes optimism in the position assessment as well as missing defensive continuations.

A three-feature, symmetric position correction was fitted on 13,426 rows, including the new quiet descendants and existing broad/GM data. It learned a bounded king-shelter term, while the two unsafe-mobility terms stayed zero. Broad development squared error improved only about 0.37%; the Black cohort and GM examples worsened. Latest-descendant mean absolute error improved only about 3.1%, below the 5% requirement. It was rejected before runtime integration. The three reserved Italian games remain unused.

The separate reward-policy fit used 132 independently supported good actions and 34 supported corrections from six earlier completed games, plus 128 broad replay positions. Eight passes reduced its training objective by about 30%. However, a frozen runtime test with a bounded 40cp policy preference produced more tactical error and new major mistakes. Training-objective improvement did not qualify it for release. It was not combined with the root-verification challenger.

## What the games taught us

All **{final['reviewed_moves']} candidate moves** in this batch's completed games were reviewed. Stockfish supplied **{final['positive_labels']} positive labels**, **{final['negative_labels']} negative labels**, and **{final['usable_corrections']} supported legal alternatives**. Correction phases: `{final['correction_phases']}`. Uncertain alternatives remain null, and mate estimates remain mate estimates. These thresholded labels are not a complete error rate or an Elo estimate.

The two fresh v1.56 losses at nominal 2400 were both checkmates, with 14 thresholded mistakes, all tagged middlegame. The largest White error was 35.h5: Stockfish preferred 35.g5, with 483/506cp regret at the two budgets. The Black loss included 24...b5 instead of...Re7 and 40...Rxf2 instead of...Qe5, followed by missed mating defences. These are targeted defence and evaluation problems, not evidence that more gambit openings would help.

In the challenger's first Petrov game, the draw had 56 reviewed moves, 50 supported good moves and no threshold-crossing mistake. The largest available two-budget advantage was only about +0.6 pawns; the final repetition evaluated 0cp at the deeper budget. Avoiding this repetition for its own sake would not establish a winning improvement. Good moves in a draw still receive positive training signals.

The archived PGNs, full reviews and legal correction targets are now development data. A later model trained on them must not present their replay as independent strength evidence. Search efficiency, defensive move selection and independently validated position-value learning remain the priorities; none of the failed changes was silently merged into the selected upload.

## Newly completed competition games

The authenticated dashboard control still failed with a missing kernel-assets path. The existing public-page downloader worked. It retrieved the four newest completed Chessity games (rounds 85–88, two wins and two losses) and the current leaderboard leader's two newest completed games (a loss and a draw). The PGNs were legally replayed and all **{public_moves} tracked-side moves** received the same independent Stockfish review, followed by separate experimental policy fits for our games and the leader's games. These public results cannot be assigned to v1.56 or the local challenger: the public pages did not verify the submission hash.

| Tracked team | Game | Opponent | Score | Reviewed moves | Positive labels | Negative labels |
|---|---|---|---:|---:|---:|---:|
{public_rows}

All four of our games ended by checkmate. Our 181 reviewed moves produced 97 positive and 17 negative labels; 16 of those mistakes were tagged middlegame and one opening. In the round 88 win, 26.Bxg5 erased roughly 500cp of advantage relative to Rf1. In the round 87 loss, 21...b5 cost 442/461cp relative to...f5, while 19...Rxe8 was inferior to...Bxe8. In the round 86 loss, 18.Nc5 cost 272/271cp relative to Qe2. This reinforces the need to compare defensive alternatives, pawn breaks and the piece used to recapture. It does not justify a rule that every pawn push or capture is bad.

The leader’s 180 reviewed moves produced 147 positive labels and one negative label. Its win/loss status did not determine move rewards either; individual moves were judged by Stockfish. Thresholds can miss gradual deterioration, so few marked blunders do not prove perfect play. Public correction targets retain null alternatives when the reviews disagree. No downloaded opponent executable, unverified bot version assignment or fabricated Elo comparison was introduced.

The separate policy fit on our newest games used 96 eligible good examples and 16 supported corrections, with 128 broad replay positions. Its one-pass objective fell 0.96213→0.94293; the model SHA256 is `72ca73d27090618815a7c4d3bbeeb4956b884165772f8ba46e51fc4625908fbb`. The leader-data fit used 95 eligible good examples and one correction, also with 128 replay positions; its objective fell 1.08126→1.06482. Both are experimental training results, with no runtime match validation and no selected weight changes.

## Selected upload and limits

v1.56's original release screen was 2W/0D/0L against v1.55, 2W/0D/0L against v1.53, 0W/1D/1L at nominal 2400 and 0W/1D/1L at nominal 2600. The new 0W/0D/2L development pair at nominal 2400 is reported separately above. Those results do not support claiming a stable 2400 or 2600 Elo.

Selected ZIP SHA256: `{final['incumbent_sha256']}`. The archive and read-only runtime remain unchanged. The currently active competition submission was not verified in this batch; GitHub publication is tracked separately after the push is verified.
"""
    for path in (ROOT / 'docs/PROGRESSION_RESULTS_20260909.md', ROOT.parent / 'chessity-progression-improvement-20260909.md'):
        assert not path.exists()
        path.write_text(text, encoding='utf-8')
    print('Wrote completed progression report', flush=True)


if __name__ == '__main__':
    run()
