# Recommended upload: chessity-agent v1.56

The new engine reuses separate move and ordering arrays at each search ply.
This removes repeated allocation while preserving fixed-work moves, scores,
depths and node counts. The twelve-root ABBA comparison measured an aggregate
CPU speed ratio of 1.08640 and median 1.09345. Eleven correctness tests passed.
The independent clock-choice review had unchanged choices and no new major
mistake or mate-loss regression.

| Opponent | Wins | Draws | Losses |
|---|---:|---:|---:|
| Exact v1.55 | 2 | 0 | 0 |
| Exact v1.53 | 2 | 0 | 0 |
| Stockfish nominal 2400 | 0 | 1 | 1 |
| Stockfish nominal 2600 | 0 | 1 | 1 |

No rated-setting win was recorded in this screen.
No 2800 pair was run because there was no qualifying 2600 win. These are short
development tests at 120s + 0.5s, with both colours and frozen playing weights.
They do not establish a calibrated Elo or consistent superiority.

All 478 candidate moves were reviewed; independent Stockfish
labels supported 241 moves and identified 34 corrections.
Post-game policy fits remain experimental. The package retains the existing
v1.55 root policy and classical searched-position evaluator, with no new value
fit. The full review identified 24 middlegame and 10 endgame mistakes, including
mistakes in wins. Their root rewards require independent descendant labels
before position-value learning.

Four direct comparison wins support this practical update. The rated pairs
still show substantial weaknesses; the earlier v1.55 win at nominal 2600 was
not repeated. Keep both archives and these exact results available.

Strict read-only validation passed: 17.119s startup
against 90s, two legal calls, blocked filesystem mutations and no network or
subprocess use in inference. Local checks do not guarantee site validation.

ZIP SHA256: `e0fb10c7ec482b93fe4bc20bfce7bd790bce78d163e5810a085a2223e795b99d`. All 56 older ZIPs remain byte-identical.
Automatic competition submission is authorised. Browser control remains
unavailable due to a kernel-assets missing-path error, so no successful site
upload or new active submission has been observed.
