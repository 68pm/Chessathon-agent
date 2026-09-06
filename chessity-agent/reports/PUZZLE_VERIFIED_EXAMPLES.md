# Thirty verified examples from the training split

These examples show actual labels used in the pilot. Source motif tags describe sampling categories; they are not independently proved explanations. Only exhaustive short mates are exact. Other targets are estimates from Stockfish 19 at two fixed budgets. Principal variations illustrate one continuation and do not prove coverage of every defensive reply. No held-out test examples appear here.

## 1. mating_patterns: constructed:dc1061623658bc6cf5ff514f1735a06b3ca5b8bfbb0b2531b27786cc3ee24955

White to move. Origin: `constructed_elementary`. Confidence: **exact**.

Objective: Force checkmate against every legal defence within 1 plies.

```text
. Q . . . . . .
. . . . . . . .
. . . . . . . .
. . . . . . . .
. . . . . . . .
. . . . . . . .
. . . . . . . .
. . . . . K . k
  a b c d e f g h
```

FEN: `1Q6/8/8/8/8/8/8/5K1k w - - 0 1`

Accepted alternatives: Qh8# (`b8h8`).

Source tags: mateIn1, endgame.

Proof type: `exhaustive_mate_within_1_plies`. Verification: `{"requested_nodes_per_pass": [80000, 320000], "actual_nodes_per_pass": [80067, 320313], "seconds": 0.18550469999900088, "exact_proof_nodes": 24, "mate_horizon_plies": 1}`.

Illustrative continuation: Qh8#.

No separate stable 200cp mistake label was assigned to this record. A failed short-mate objective is not automatically a proved lost game.

## 2. ordinary_negative_control: local:55902851b8830562ba6fa940e202bbb982dc2cc5cc596f44226a0c2a49d3fad4:76

White to move. Origin: `actual_local_game`. Confidence: **engine_supported**.

Objective: Choose a move within 70cp of the best at BOTH declared budgets. Estimated move quality, not proof of a win.

```text
. . . . . . . .
. . . . R . . .
. . . p . . . r
p . . r . p k .
p . . . . . . p
K . P . . . P .
. . . . B . . .
. . . . . . . .
  a b c d e f g h
```

FEN: `8/4R3/3p3r/p2r1pk1/p6p/K1P3P1/4B3/8 w - - 0 41`

Accepted alternatives: c4 (`c3c4`), Bf3 (`e2f3`), Rb7 (`e7b7`), Re3 (`e7e3`), Rg7+ (`e7g7`), gxh4+ (`g3h4`).

Source tags: .

Proof type: `two_budget_full_legal_root_analysis`. Verification: `{"requested_nodes_per_pass": [80000, 320000], "actual_nodes_per_pass": [80020, 320057], "seconds": 0.5076336999918567, "exact_proof_nodes": 27, "mate_horizon_plies": null}`.

Illustrative continuation: c4 Rc5 gxh4+ Rxh4 Re3 Rh8 Kxa4 Ra8.

Illustrative continuation: Bf3 Rc5 gxh4+ Rxh4 Re3 Rh3 Rd3 Rh2 Bb7 Rf2.

Verified bad alternative `e7e5`: estimated regret [276, 258]cp at the two budgets; illustrative refutation `e7e5 d5e5 g3h4 g5f4 e2d1 h6h8 a3a2`.

Source reference: `local:docs/evidence/magnus-mixed-20260906-games.json`. Family: `local:55902851b8830562ba6fa940e202bbb982dc2cc5cc596f44226a0c2a49d3fad4`.

## 3. punish_blunder: local:55902851b8830562ba6fa940e202bbb982dc2cc5cc596f44226a0c2a49d3fad4:76:mistake

Black to move. Origin: `legal_branch_from_actual_game`. Confidence: **engine_supported**.

Objective: Choose a move within 70cp of the best at BOTH declared budgets. Estimated move quality, not proof of a win.

```text
. . . . . . . .
. . . . . . . .
. . . p . . . r
p . . r R p k .
p . . . . . . p
K . P . . . P .
. . . . B . . .
. . . . . . . .
  a b c d e f g h
```

FEN: `8/8/3p3r/p2rRpk1/p6p/K1P3P1/4B3/8 b - - 1 41`

Accepted alternatives: Rxe5 (`d5e5`), dxe5 (`d6e5`).

Source tags: .

Proof type: `two_budget_full_legal_root_analysis`. Verification: `{"requested_nodes_per_pass": [80000, 320000], "actual_nodes_per_pass": [80078, 320062], "seconds": 0.40882260000216775, "exact_proof_nodes": 18, "mate_horizon_plies": null}`.

Illustrative continuation: Rxe5 gxh4+ Rxh4 Bf3 Rh6 Kxa4 Rh3 Kb3.

Illustrative continuation: dxe5 gxh4+ Kf4 Kxa4 Ke3 Bc4 Rc5.

Verified bad alternative `d5b5`: estimated regret [880, 963]cp at the two budgets; illustrative refutation `d5b5 g3h4 h6h4 e5b5 h4h3 b5b2 h3c3 a3a4 c3e3 a4a5`.

Verified bad alternative `d5c5`: estimated regret [212, 321]cp at the two budgets; illustrative refutation `d5c5 g3h4 h6h4 e5c5 d6c5 e2f1 g5f6 c3c4 h4h7 a3a4`.

Source reference: `local:docs/evidence/magnus-mixed-20260906-games.json`. Family: `local:55902851b8830562ba6fa940e202bbb982dc2cc5cc596f44226a0c2a49d3fad4`.

## 4. quiet_ideas: lichess:012wC

White to move. Origin: `lichess_cc0_puzzle`. Confidence: **engine_supported**.

Objective: Choose a move within 70cp of the best at BOTH declared budgets. Estimated move quality, not proof of a win.

```text
r . . q . r k .
p b p n . p . n
. p . b p . . Q
. . . . . . . .
. . . . . . . .
. B . P . N N .
P P P . . P P P
R . . . K . . R
  a b c d e f g h
```

FEN: `r2q1rk1/pbpn1p1n/1p1bp2Q/8/8/1B1P1NN1/PPP2PPP/R3K2R w KQ - 1 13`

Accepted alternatives: Nh5 (`g3h5`).

Source tags: advantage, kingsideAttack, middlegame, quietMove, short.

Proof type: `two_budget_full_legal_root_analysis`. Verification: `{"requested_nodes_per_pass": [80000, 320000], "actual_nodes_per_pass": [80071, 320197], "seconds": 0.872513299997081, "exact_proof_nodes": 47, "mate_horizon_plies": null}`.

Illustrative continuation: Nh5 Be5 Nxe5 Qg5 Qxg5+ Nxg5 Nxd7 Bxg2 Rg1 Nf3+.

Verified bad alternative `a1b1`: estimated regret [1200, 1239]cp at the two budgets; illustrative refutation `a1b1 d8f6 h6e3 a7a5 c2c3 f6f4 b3c2 f4e3 f2e3`.

Verified bad alternative `a1c1`: estimated regret [1184, 1283]cp at the two budgets; illustrative refutation `a1c1 d8f6 h6e3 f6f4 g3e4 f4e3 f2e3 b7e4`.

Source reference: `https://lichess.org/0Dqefo5O/black#24`. Family: `lichess:0Dqefo5O`.

## 5. fundamental_tactics: lichess:00XPh

Black to move. Origin: `lichess_cc0_puzzle`. Confidence: **engine_supported**.

Objective: Choose a move within 70cp of the best at BOTH declared budgets. Estimated move quality, not proof of a win.

```text
. . b r . . . k
. . . . . p . p
p p n . . N p .
. . b . q . P .
. . P . p . . N
P . . . . . . .
. P . . B . K .
R . Q . . R . .
  a b c d e f g h
```

FEN: `2br3k/5p1p/ppn2Np1/2b1q1P1/2P1p2N/P7/1P2B1K1/R1Q2R2 b - - 7 27`

Accepted alternatives: Bd6 (`c5d6`).

Source tags: crushing, long, middlegame.

Proof type: `two_budget_full_legal_root_analysis`. Verification: `{"requested_nodes_per_pass": [80000, 320000], "actual_nodes_per_pass": [80068, 320307], "seconds": 0.5393584999983432, "exact_proof_nodes": 53, "mate_horizon_plies": null}`.

Illustrative continuation: Bd6 Qf4 Qxf4 Rxf4 Bxf4 Rh1 h5 gxh6 Nd4.

Verified bad alternative `a6a5`: estimated regret [725, 714]cp at the two budgets; illustrative refutation `a6a5 c1f4 e5b2 f4e4 c6d4 a1e1 d4c2`.

Verified bad alternative `b6b5`: estimated regret [675, 676]cp at the two budgets; illustrative refutation `b6b5 c1f4 e5f4 f1f4 c5e3 f4e4 e3g5 a1f1 c8b7 f6d5`.

Source reference: `https://lichess.org/8CP4mZnr#53`. Family: `lichess:8CP4mZnr`.

## 6. endgame: lichess:01Opl

Black to move. Origin: `lichess_cc0_puzzle`. Confidence: **engine_supported**.

Objective: Choose a move within 70cp of the best at BOTH declared budgets. Estimated move quality, not proof of a win.

```text
. . . . . . . .
. . . . . . . .
. . . . n . . .
. . . . B K . .
. . k . . . . .
. p . . . . . .
. . . . . P . .
. . . . . . . .
  a b c d e f g h
```

FEN: `8/8/4n3/4BK2/2k5/1p6/5P2/8 b - - 1 56`

Accepted alternatives: Nd4+ (`e6d4`).

Source tags: advancedPawn, crushing, endgame, long, promotion.

Proof type: `two_budget_full_legal_root_analysis`. Verification: `{"requested_nodes_per_pass": [80000, 320000], "actual_nodes_per_pass": [80031, 320221], "seconds": 0.39892360000521876, "exact_proof_nodes": 14, "mate_horizon_plies": null}`.

Illustrative continuation: Nd4+ Bxd4 Kxd4 f4 b2 Kg5 b1=Q Kf6 Qb3 Kf5.

Verified bad alternative `b3b2`: estimated regret [505, 518]cp at the two budgets; illustrative refutation `b3b2 e5b2 e6c5 f2f3 c5d3 f5g4 d3b2 g4h3 c4c5 h3g3`.

Verified bad alternative `c4b4`: estimated regret [1006, 896]cp at the two budgets; illustrative refutation `c4b4`.

Source reference: `https://lichess.org/ND7kZ8aU#111`. Family: `lichess:ND7kZ8aU`.

## 7. defence: lichess:00lsn

White to move. Origin: `lichess_cc0_puzzle`. Confidence: **engine_supported**.

Objective: Choose a move within 70cp of the best at BOTH declared budgets. Estimated move quality, not proof of a win.

```text
r n b . r . . k
p p p . . Q b .
. . . p N . . .
. . . . . . . .
. . . P q . . P
. . P . . . . .
P P . . . P . .
R N . . K . R .
  a b c d e f g h
```

FEN: `rnb1r2k/ppp2Qb1/3pN3/8/3Pq2P/2P5/PP3P2/RN2K1R1 w Q - 1 19`

Accepted alternatives: Kd1 (`e1d1`).

Source tags: crushing, defensiveMove, middlegame, short.

Proof type: `two_budget_full_legal_root_analysis`. Verification: `{"requested_nodes_per_pass": [80000, 320000], "actual_nodes_per_pass": [80039, 320257], "seconds": 0.7525204999983544, "exact_proof_nodes": 3, "mate_horizon_plies": null}`.

Illustrative continuation: Kd1 Qh7 Qxe8+ Qg8 Qxg8+ Kxg8 Nxg7 Kh8 Nd2 Nc6.

Verified bad alternative `e1d2`: estimated regret [765, 862]cp at the two budgets; illustrative refutation `e1d2 g7h6 e6g5 c8f5 f7f6 h8g8 f6f7`.

Verified bad alternative `e1f1`: estimated regret [1542, 1338]cp at the two budgets; illustrative refutation `e1f1`.

Source reference: `https://lichess.org/Sb8oEHsM/black#36`. Family: `lichess:Sb8oEHsM`.

## 8. combinations: lichess:01CmR

Black to move. Origin: `lichess_cc0_puzzle`. Confidence: **engine_supported**.

Objective: Choose a move within 70cp of the best at BOTH declared budgets. Estimated move quality, not proof of a win.

```text
. . . . . r . k
. . p . . . p .
p . p p . . . p
. . . . . . . .
P b . P P . . .
. Q . . K P . .
. P . . R . . q
R . B . . . . .
  a b c d e f g h
```

FEN: `5r1k/2p3p1/p1pp3p/8/Pb1PP3/1Q2KP2/1P2R2q/R1B5 b - - 4 25`

Accepted alternatives: Rxf3+ (`f8f3`).

Source tags: advantage, attraction, long, middlegame, sacrifice, skewer.

Proof type: `two_budget_full_legal_root_analysis`. Verification: `{"requested_nodes_per_pass": [80000, 320000], "actual_nodes_per_pass": [80069, 320232], "seconds": 0.5182678999990458, "exact_proof_nodes": 35, "mate_horizon_plies": null}`.

Illustrative continuation: Rxf3+ Kxf3 Qh3+ Kf2 Qxb3 Bf4 Qh3 Re3 Qh4+ Bg3.

Verified bad alternative `a6a5`: estimated regret [1314, 1485]cp at the two budgets; illustrative refutation `a6a5 e2h2 c6c5 e3e2 c5d4`.

Verified bad alternative `b4a3`: estimated regret [1608, 1589]cp at the two budgets; illustrative refutation `b4a3 e2h2 a3b2 b3b2 f8e8 e3d3`.

Source reference: `https://lichess.org/iNxnHQeK#49`. Family: `lichess:iNxnHQeK`.

## 9. mating_patterns: constructed:12f5ed7e811971635e5287c099523572133568fadd3bd8dbfadad303d4f7e393

Black to move. Origin: `constructed_elementary`. Confidence: **exact**.

Objective: Force checkmate against every legal defence within 1 plies.

```text
. . . . . . . .
. . . . . . . .
. . k . . . . .
K . . . . . . .
. . . . . . . .
. . . . q . . .
. . . . . . . .
. . . . . . . .
  a b c d e f g h
```

FEN: `8/8/2k5/K7/8/4q3/8/8 b - - 0 1`

Accepted alternatives: Qa3# (`e3a3`).

Source tags: mateIn1, endgame.

Proof type: `exhaustive_mate_within_1_plies`. Verification: `{"requested_nodes_per_pass": [80000, 320000], "actual_nodes_per_pass": [80016, 320178], "seconds": 0.2413823999959277, "exact_proof_nodes": 31, "mate_horizon_plies": 1}`.

Illustrative continuation: Qa3#.

No separate stable 200cp mistake label was assigned to this record. A failed short-mate objective is not automatically a proved lost game.

## 10. ordinary_negative_control: local:55902851b8830562ba6fa940e202bbb982dc2cc5cc596f44226a0c2a49d3fad4:76:sound

Black to move. Origin: `legal_branch_from_actual_game`. Confidence: **engine_supported**.

Objective: Choose a move within 70cp of the best at BOTH declared budgets. Estimated move quality, not proof of a win.

```text
. . . . . . . .
. . . . R . . .
. . . p . . . r
p . . r . p k .
p . P . . . . p
K . . . . . P .
. . . . B . . .
. . . . . . . .
  a b c d e f g h
```

FEN: `8/4R3/3p3r/p2r1pk1/p1P4p/K5P1/4B3/8 b - - 0 41`

Accepted alternatives: Rc5 (`d5c5`), Rd2 (`d5d2`), Rd4 (`d5d4`), Kf6 (`g5f6`).

Source tags: .

Proof type: `two_budget_full_legal_root_analysis`. Verification: `{"requested_nodes_per_pass": [80000, 320000], "actual_nodes_per_pass": [80025, 320092], "seconds": 0.4357702999986941, "exact_proof_nodes": 18, "mate_horizon_plies": null}`.

Illustrative continuation: Rc5 gxh4+ Rxh4 Bf1 Rf4 Be2 Rd4 Re3.

Illustrative continuation: Rd2 gxh4+ Rxh4 Kxa4 Rh2 Kxa5 Rdxe2 Rg7+ Kf6 Rg8.

Verified bad alternative `d5b5`: estimated regret [871, 925]cp at the two budgets; illustrative refutation `d5b5 c4b5 h4h3 e2f3 h3h2 f3h1 d6d5 a3a4 d5d4 e7e2`.

Verified bad alternative `d5d1`: estimated regret [660, 661]cp at the two budgets; illustrative refutation `d5d1 e2d1 h4g3 d1f3 h6h4 e7g7 g5f4 f3g2 h4h2 g2a8`.

Source reference: `local:docs/evidence/magnus-mixed-20260906-games.json`. Family: `local:55902851b8830562ba6fa940e202bbb982dc2cc5cc596f44226a0c2a49d3fad4`.

## 11. punish_blunder: local:55902851b8830562ba6fa940e202bbb982dc2cc5cc596f44226a0c2a49d3fad4:90:mistake

Black to move. Origin: `legal_branch_from_actual_game`. Confidence: **engine_supported**.

Objective: Choose a move within 70cp of the best at BOTH declared budgets. Estimated move quality, not proof of a win.

```text
. . . . . . . .
. . . . . . . .
. . . . . k . .
K . . . . p . .
. . P . p . . .
. . . B . . . .
. . . . . r . .
. . . . . . . .
  a b c d e f g h
```

FEN: `8/8/5k2/K4p2/2P1p3/3B4/5r2/8 b - - 0 48`

Accepted alternatives: exd3 (`e4d3`).

Source tags: .

Proof type: `two_budget_full_legal_root_analysis`. Verification: `{"requested_nodes_per_pass": [80000, 320000], "actual_nodes_per_pass": [80028, 320019], "seconds": 0.3105307000078028, "exact_proof_nodes": 20, "mate_horizon_plies": null}`.

Illustrative continuation: exd3 Kb4 d2 c5 d1=Q Ka5 Qf3 Ka4 Qa8+ Kb4.

Verified bad alternative `f2c2`: estimated regret [1211, 1372]cp at the two budgets; illustrative refutation `f2c2 d3c2 e4e3 c2d1 f6e5 c4c5 e5d4 c5c6 d4d3 c6c7`.

Verified bad alternative `f2e2`: estimated regret [1242, 1421]cp at the two budgets; illustrative refutation `f2e2 d3e2 f5f4 c4c5 f4f3 e2d1 f6e5 c5c6 e5f4 c6c7`.

Source reference: `local:docs/evidence/magnus-mixed-20260906-games.json`. Family: `local:55902851b8830562ba6fa940e202bbb982dc2cc5cc596f44226a0c2a49d3fad4`.

## 12. quiet_ideas: lichess:01Wbh

Black to move. Origin: `lichess_cc0_puzzle`. Confidence: **engine_supported**.

Objective: Choose a move within 70cp of the best at BOTH declared budgets. Estimated move quality, not proof of a win.

```text
. . . . . r . k
p p p . q . . p
. . . . . . . .
. . . B n . . .
. . . . Q . n .
. . N . . . K .
P P P . . P P .
R . . . . R . .
  a b c d e f g h
```

FEN: `5r1k/ppp1q2p/8/3Bn3/4Q1n1/2N3K1/PPP2PP1/R4R2 b - - 0 21`

Accepted alternatives: Qg7 (`e7g7`).

Source tags: advantage, discoveredAttack, discoveredCheck, middlegame, quietMove, short.

Proof type: `two_budget_full_legal_root_analysis`. Verification: `{"requested_nodes_per_pass": [80000, 320000], "actual_nodes_per_pass": [80049, 320309], "seconds": 0.7520976999949198, "exact_proof_nodes": 46, "mate_horizon_plies": null}`.

Illustrative continuation: Qg7 Qb4 Nxf2+ Kh2 Qh6+ Kg3 Qe3+ Kh2 Neg4+ Kg1.

Verified bad alternative `a7a5`: estimated regret [533, 443]cp at the two budgets; illustrative refutation `a7a5 f2f3 g4f6 e4d4 c7c5 d4h4 e5g6 h4h6 f6h5 h6h5`.

Verified bad alternative `a7a6`: estimated regret [402, 436]cp at the two budgets; illustrative refutation `a7a6 f2f3`.

Source reference: `https://lichess.org/SEynvJja#41`. Family: `lichess:SEynvJja`.

## 13. fundamental_tactics: lichess:00Ngg

Black to move. Origin: `lichess_cc0_puzzle`. Confidence: **engine_supported**.

Objective: Choose a move within 70cp of the best at BOTH declared budgets. Estimated move quality, not proof of a win.

```text
. . . q k . . r
. p . b b p p p
. . . . p n . .
. B P p . n . .
. . . P . . . .
. . . . P N . .
. . . . Q P P P
B N . . K . . R
  a b c d e f g h
```

FEN: `3qk2r/1p1bbppp/4pn2/1BPp1n2/3P4/4PN2/4QPPP/BN2K2R b Kk - 2 15`

Accepted alternatives: Qa5+ (`d8a5`).

Source tags: advantage, fork, middlegame, short.

Proof type: `two_budget_full_legal_root_analysis`. Verification: `{"requested_nodes_per_pass": [80000, 320000], "actual_nodes_per_pass": [80077, 320014], "seconds": 0.7095566999923903, "exact_proof_nodes": 31, "mate_horizon_plies": null}`.

Illustrative continuation: Qa5+ Bc3 Qxb5 Qxb5 Bxb5 Bd2 Ba6 h4 Ne4 Nc3.

Verified bad alternative `b7b6`: estimated regret [1156, 1213]cp at the two budgets; illustrative refutation `b7b6 c5c6 e8g8 c6d7 f5d6 b1c3 d6b5 e2b5 d8d7 b5b2`.

Verified bad alternative `d7b5`: estimated regret [644, 678]cp at the two budgets; illustrative refutation `d7b5 e2b5 d8d7 b1c3 d7b5 c3b5 e8g8 e1e2 h7h5 h1b1`.

Source reference: `https://lichess.org/5oeDyMdB#29`. Family: `lichess:5oeDyMdB`.

## 14. endgame: lichess:018Ap

White to move. Origin: `lichess_cc0_puzzle`. Confidence: **engine_supported**.

Objective: Choose a move within 70cp of the best at BOTH declared budgets. Estimated move quality, not proof of a win.

```text
. . . . . . . .
. . . . . . . .
k . . . . . . p
. . . . . K p .
. . . . P p . .
. . . . . B . .
. . r . . . P P
. . . . . . . .
  a b c d e f g h
```

FEN: `8/8/k6p/5Kp1/4Pp2/5B2/2r3PP/8 w - - 0 48`

Accepted alternatives: e5 (`e4e5`).

Source tags: crushing, endgame, long, master, quietMove.

Proof type: `two_budget_full_legal_root_analysis`. Verification: `{"requested_nodes_per_pass": [80000, 320000], "actual_nodes_per_pass": [80020, 320194], "seconds": 0.40324929999769665, "exact_proof_nodes": 14, "mate_horizon_plies": null}`.

Illustrative continuation: e5 Rc3 e6 Kb6 Kf6 Kc7 e7 Re3.

Verified bad alternative `f3d1`: estimated regret [377, 472]cp at the two budgets; illustrative refutation `f3d1 c2g2 e4e5 g2g1 d1g4 g1g4 e5e6`.

Verified bad alternative `f3e2`: estimated regret [679, 835]cp at the two budgets; illustrative refutation `f3e2 c2e2 e4e5 e2g2 f5g6 f4f3 e5e6 g2e2 h2h4 g5h4`.

Source reference: `https://lichess.org/NE1w79s4/black#94`. Family: `lichess:NE1w79s4`.

## 15. defence: lichess:01312

White to move. Origin: `lichess_cc0_puzzle`. Confidence: **engine_supported**.

Objective: Choose a move within 70cp of the best at BOTH declared budgets. Estimated move quality, not proof of a win.

```text
. . . . . . . .
p p . . . . . .
. . . . . . . .
. . p . . k . P
. . . p . . . .
. . P . . . K .
P P . . . . . .
. . . . . . . .
  a b c d e f g h
```

FEN: `8/pp6/8/2p2k1P/3p4/2P3K1/PP6/8 w - - 0 40`

Accepted alternatives: cxd4 (`c3d4`).

Source tags: crushing, defensiveMove, endgame, pawnEndgame, short.

Proof type: `two_budget_full_legal_root_analysis`. Verification: `{"requested_nodes_per_pass": [80000, 320000], "actual_nodes_per_pass": [80001, 320130], "seconds": 0.4068383000121685, "exact_proof_nodes": 13, "mate_horizon_plies": null}`.

Illustrative continuation: cxd4 cxd4 Kf3 d3 Ke3 Kg5 Kxd3 Kxh5 Kd4 Kg6.

Verified bad alternative `a2a3`: estimated regret [375, 557]cp at the two budgets; illustrative refutation `a2a3 d4d3 g3f2 c5c4 a3a4 b7b6 f2e3 a7a6 b2b3 b6b5`.

Verified bad alternative `a2a4`: estimated regret [305, 298]cp at the two budgets; illustrative refutation `a2a4 d4d3 g3f2 c5c4 f2e3 a7a6 a4a5 f5g5 b2b3 c4b3`.

Source reference: `https://lichess.org/9U62VOsr/black#78`. Family: `lichess:9U62VOsr`.

## 16. combinations: lichess:00gpa

White to move. Origin: `lichess_cc0_puzzle`. Confidence: **engine_supported**.

Objective: Choose a move within 70cp of the best at BOTH declared budgets. Estimated move quality, not proof of a win.

```text
r . b r . . k .
q p . . . p p .
p . . . p . . p
. . . . . . . .
. . . . . . . .
P . . . . . P .
. P B B . . P .
. . R Q . . . K
  a b c d e f g h
```

FEN: `r1br2k1/qp3pp1/p3p2p/8/8/P5P1/1PBB2P1/2RQ3K w - - 1 22`

Accepted alternatives: Be3 (`d2e3`).

Source tags: advantage, fork, middlegame, sacrifice, veryLong.

Proof type: `two_budget_full_legal_root_analysis`. Verification: `{"requested_nodes_per_pass": [80000, 320000], "actual_nodes_per_pass": [80077, 320134], "seconds": 0.5475923000049079, "exact_proof_nodes": 30, "mate_horizon_plies": null}`.

Illustrative continuation: Be3 Rxd1+ Rxd1 Kf8 Bxa7 Rxa7 Rd8+ Ke7 Rxc8 b5.

Verified bad alternative `a3a4`: estimated regret [914, 920]cp at the two budgets; illustrative refutation `a3a4 a7d4 d2a5 d4d1 c2d1 d8d3 a5e1 e6e5 d1f3 c8d7`.

Verified bad alternative `b2b3`: estimated regret [953, 1097]cp at the two budgets; illustrative refutation `b2b3 a7f2 d2f4 d8d1 c2d1 c8d7 d1c2 d7b5`.

Source reference: `https://lichess.org/tgE8FK8D/black#42`. Family: `lichess:tgE8FK8D`.

## 17. mating_patterns: constructed:bbc576224e6fca52ed45c585acc011ba650cafc691ceb72171ed201f81105471

White to move. Origin: `constructed_elementary`. Confidence: **exact**.

Objective: Force checkmate against every legal defence within 1 plies.

```text
. . . . . . . .
. . . . . . . .
k . K . . . . .
. . . . . . . .
. . . . . . . .
. . . . . . . .
. . . . . . . .
. . . . Q . . .
  a b c d e f g h
```

FEN: `8/8/k1K5/8/8/8/8/4Q3 w - - 0 1`

Accepted alternatives: Qa1# (`e1a1`).

Source tags: mateIn1, endgame.

Proof type: `exhaustive_mate_within_1_plies`. Verification: `{"requested_nodes_per_pass": [80000, 320000], "actual_nodes_per_pass": [80037, 320290], "seconds": 0.25688220000301953, "exact_proof_nodes": 26, "mate_horizon_plies": 1}`.

Illustrative continuation: Qa1#.

No separate stable 200cp mistake label was assigned to this record. A failed short-mate objective is not automatically a proved lost game.

## 18. ordinary_negative_control: local:55902851b8830562ba6fa940e202bbb982dc2cc5cc596f44226a0c2a49d3fad4:90

White to move. Origin: `actual_local_game`. Confidence: **engine_supported**.

Objective: Choose a move within 70cp of the best at BOTH declared budgets. Estimated move quality, not proof of a win.

```text
. . . . . . . .
. . . . . . . .
. . . . . k . .
p . . . . p . .
K . P . p . . .
. . . B . . . .
. . . . . r . .
. . . . . . . .
  a b c d e f g h
```

FEN: `8/8/5k2/p4p2/K1P1p3/3B4/5r2/8 w - - 0 48`

Accepted alternatives: Kb3 (`a4b3`), Bb1 (`d3b1`), Bc2 (`d3c2`), Be2 (`d3e2`), Bxe4 (`d3e4`).

Source tags: .

Proof type: `two_budget_full_legal_root_analysis`. Verification: `{"requested_nodes_per_pass": [80000, 320000], "actual_nodes_per_pass": [80008, 320201], "seconds": 0.31476549999206327, "exact_proof_nodes": 10, "mate_horizon_plies": null}`.

Illustrative continuation: Kb3 exd3 Kc3 d2 Kc2 Rh2 c5 Rh7 Kxd2 Rc7.

Illustrative continuation: Bb1 e3 Bd3 e2 Bxe2 Rxe2 Kxa5 Kg5.

Verified bad alternative `a4a5`: estimated regret [326, 335]cp at the two budgets; illustrative refutation `a4a5 e4d3 a5b5 d3d2 b5c6 d2d1q c6c7 d1b3 c4c5 f2d2`.

Source reference: `local:docs/evidence/magnus-mixed-20260906-games.json`. Family: `local:55902851b8830562ba6fa940e202bbb982dc2cc5cc596f44226a0c2a49d3fad4`.

## 19. punish_blunder: local:d7020136ac7d669e0ce235a3a6a1ca63c05cae7147e529ebe227d4a912cd12a2:44:mistake

Black to move. Origin: `legal_branch_from_actual_game`. Confidence: **engine_supported**.

Objective: Choose a move within 70cp of the best at BOTH declared budgets. Estimated move quality, not proof of a win.

```text
. . k . r b . r
. p n . p . . .
p . p . P p . .
P N P p . P . p
. . . P . P n .
. P . B . . . .
. . . Q . . . .
R . . . . R K .
  a b c d e f g h
```

FEN: `2k1rb1r/1pn1p3/p1p1Pp2/PNPp1P1p/3P1Pn1/1P1B4/3Q4/R4RK1 b - - 4 25`

Accepted alternatives: axb5 (`a6b5`), Rg8 (`h8g8`).

Source tags: .

Proof type: `two_budget_full_legal_root_analysis`. Verification: `{"requested_nodes_per_pass": [80000, 320000], "actual_nodes_per_pass": [80002, 320138], "seconds": 1.0841953999915859, "exact_proof_nodes": 20, "mate_horizon_plies": null}`.

Illustrative continuation: axb5 a6 bxa6 Kh1 Bh6 Qa5 Ne3 Rf3 Reg8 Rxe3.

Illustrative continuation: Rg8 Nxc7 Ne3+ Kh1 Nxf1 Bxf1 Kxc7 Qh2 Bh6 Bd3.

Verified bad alternative `b7b6`: estimated regret [350, 356]cp at the two budgets; illustrative refutation `b7b6 b5a7 c8b7 a5b6 c7b5 d3b5 a6b5 g1h1 g4f2 f1f2`.

Verified bad alternative `c7e6`: estimated regret [255, 256]cp at the two budgets; illustrative refutation `c7e6 f5e6 c6b5 g1h1 h8g8 a1c1 f8h6`.

Source reference: `local:docs/evidence/magnus-mixed-20260906-games.json`. Family: `local:d7020136ac7d669e0ce235a3a6a1ca63c05cae7147e529ebe227d4a912cd12a2`.

## 20. quiet_ideas: lichess:010rQ

White to move. Origin: `lichess_cc0_puzzle`. Confidence: **engine_supported**.

Objective: Choose a move within 70cp of the best at BOTH declared budgets. Estimated move quality, not proof of a win.

```text
r . . . k b . r
. p . b . p . .
p . . p p p . p
. . q . . P . B
. . n N P . . .
. . N . . . R .
P . P Q . . P P
. R . . . . K .
  a b c d e f g h
```

FEN: `r3kb1r/1p1b1p2/p2ppp1p/2q2P1B/2nNP3/2N3R1/P1PQ2PP/1R4K1 w kq - 1 20`

Accepted alternatives: Qf2 (`d2f2`).

Source tags: advantage, long, middlegame, pin, quietMove.

Proof type: `two_budget_full_legal_root_analysis`. Verification: `{"requested_nodes_per_pass": [80000, 320000], "actual_nodes_per_pass": [80056, 320119], "seconds": 0.7797704999975394, "exact_proof_nodes": 50, "mate_horizon_plies": null}`.

Illustrative continuation: Qf2 Ke7 Rxb7 Ne5 fxe6 fxe6 Kh1.

Verified bad alternative `a2a3`: estimated regret [1135, 1182]cp at the two budgets; illustrative refutation `a2a3 c4d2 b1d1 c5d4 g1h1 f8e7`.

Verified bad alternative `a2a4`: estimated regret [1125, 1091]cp at the two budgets; illustrative refutation `a2a4 c4d2 b1b7 e8d8 f5e6 f7e6`.

Source reference: `https://lichess.org/vbymThWp/black#38`. Family: `lichess:vbymThWp`.

## 21. fundamental_tactics: lichess:006fF

White to move. Origin: `lichess_cc0_puzzle`. Confidence: **engine_supported**.

Objective: Choose a move within 70cp of the best at BOTH declared budgets. Estimated move quality, not proof of a win.

```text
r . b . . . . r
p p . k . . p .
. . n b . . q p
. B . p . . B .
. . . p . . . Q
. . . . . . . .
P P P . . P P P
. . . R R . K .
  a b c d e f g h
```

FEN: `r1b4r/pp1k2p1/2nb2qp/1B1p2B1/3p3Q/8/PPP2PPP/3RR1K1 w - - 0 18`

Accepted alternatives: Qg4+ (`h4g4`).

Source tags: advantage, discoveredAttack, exposedKing, long, middlegame.

Proof type: `two_budget_full_legal_root_analysis`. Verification: `{"requested_nodes_per_pass": [80000, 320000], "actual_nodes_per_pass": [80075, 320383], "seconds": 0.705359600004158, "exact_proof_nodes": 50, "mate_horizon_plies": null}`.

Illustrative continuation: Qg4+ Kc7 Bd8+ Rxd8 Qxg6 a6 Bd3 Kb6.

Verified bad alternative `a2a3`: estimated regret [1441, 1474]cp at the two budgets; illustrative refutation `a2a3 g6g5 h4d4 d7d8 b5c6`.

Verified bad alternative `a2a4`: estimated regret [1431, 1462]cp at the two budgets; illustrative refutation `a2a4 g6g5 h4d4 d7c7 b5c6 b7c6 c2c4`.

Source reference: `https://lichess.org/mAf9SSin/black#34`. Family: `lichess:mAf9SSin`.

## 22. endgame: lichess:00ME0

White to move. Origin: `lichess_cc0_puzzle`. Confidence: **engine_supported**.

Objective: Choose a move within 70cp of the best at BOTH declared budgets. Estimated move quality, not proof of a win.

```text
. . . . . . . .
. p . . . . . .
p . b . . . . .
. . . . k . . p
. P B . p . . P
P . . . P . K .
. . . . . . . .
. . . . . . . .
  a b c d e f g h
```

FEN: `8/1p6/p1b5/4k2p/1PB1p2P/P3P1K1/8/8 w - - 3 36`

Accepted alternatives: Bf7 (`c4f7`).

Source tags: bishopEndgame, crushing, endgame, short.

Proof type: `two_budget_full_legal_root_analysis`. Verification: `{"requested_nodes_per_pass": [80000, 320000], "actual_nodes_per_pass": [80018, 320332], "seconds": 0.39143309999781195, "exact_proof_nodes": 17, "mate_horizon_plies": null}`.

Illustrative continuation: Bf7 Bb5 Bxh5 Kf5 Bg4+ Ke5 h5 b6 h6 Kf6.

Verified bad alternative `a3a4`: estimated regret [393, 408]cp at the two budgets; illustrative refutation `a3a4 c6a4 c4e2 a4e8 g3f2 e5f6 f2e1 b7b6 e2a6 f6f5`.

Verified bad alternative `b4b5`: estimated regret [426, 486]cp at the two budgets; illustrative refutation `b4b5 c6b5 c4f7 b5e2 f7g6 e2f3 g6e8 b7b5 e8c6 e5d6`.

Source reference: `https://lichess.org/Z2H5mRQg/black#70`. Family: `lichess:Z2H5mRQg`.

## 23. defence: lichess:016Ju

Black to move. Origin: `lichess_cc0_puzzle`. Confidence: **engine_supported**.

Objective: Choose a move within 70cp of the best at BOTH declared budgets. Estimated move quality, not proof of a win.

```text
. . . . R b k .
p . . . . p . p
. . . . . . p .
. . . . . . . .
. P Q . N . . .
. . P . . . . P
. . r q . P P .
. . . . . . K .
  a b c d e f g h
```

FEN: `4Rbk1/p4p1p/6p1/8/1PQ1N3/2P4P/2rq1PP1/6K1 b - - 2 31`

Accepted alternatives: Rc1+ (`c2c1`).

Source tags: crushing, defensiveMove, endgame, veryLong.

Proof type: `two_budget_full_legal_root_analysis`. Verification: `{"requested_nodes_per_pass": [80000, 320000], "actual_nodes_per_pass": [80084, 320388], "seconds": 0.82170459999179, "exact_proof_nodes": 27, "mate_horizon_plies": null}`.

Illustrative continuation: Rc1+ Kh2 Qf4+ g3 Qf3 Rxf8+ Kxf8 Qc5+ Kg8 h4.

Verified bad alternative `a7a5`: estimated regret [1275, 1275]cp at the two budgets; illustrative refutation `a7a5 e4d2 c2d2 f2f3 a5a4 c4e4`.

Verified bad alternative `a7a6`: estimated regret [1251, 1357]cp at the two budgets; illustrative refutation `a7a6 e4d2 c2d2 f2f4 d2g2 g1f1 g2h2 c4a6 h2b2`.

Source reference: `https://lichess.org/l9CpsKKt#61`. Family: `lichess:l9CpsKKt`.

## 24. combinations: lichess:00Kq4

Black to move. Origin: `lichess_cc0_puzzle`. Confidence: **engine_supported**.

Objective: Choose a move within 70cp of the best at BOTH declared budgets. Estimated move quality, not proof of a win.

```text
r . . q k . . .
. . . . . p . r
p . p . p . . .
. p . p P . N .
P . n P . . P n
. . P . . . B .
. . P . . P . .
R . Q R . . K .
  a b c d e f g h
```

FEN: `r2qk3/5p1r/p1p1p3/1p1pP1N1/P1nP2Pn/2P3B1/2P2P2/R1QR2K1 b q - 0 21`

Accepted alternatives: Qxg5 (`d8g5`).

Source tags: advantage, attraction, fork, long, middlegame, sacrifice.

Proof type: `two_budget_full_legal_root_analysis`. Verification: `{"requested_nodes_per_pass": [80000, 320000], "actual_nodes_per_pass": [80028, 320140], "seconds": 0.7839209999947343, "exact_proof_nodes": 38, "mate_horizon_plies": null}`.

Illustrative continuation: Qxg5 Qxg5 Nf3+ Kg2 Nxg5 Rh1 Rxh1 Rxh1 Kd7 Bf4.

Verified bad alternative `a6a5`: estimated regret [1149, 1181]cp at the two budgets; illustrative refutation `a6a5 g5h7`.

Verified bad alternative `a8a7`: estimated regret [1171, 1261]cp at the two budgets; illustrative refutation `a8a7 g5h7 e8d7 c1f4 h4g6 f4f7 d7c8 f7g6`.

Source reference: `https://lichess.org/o4K7aQsT#41`. Family: `lichess:o4K7aQsT`.

## 25. mating_patterns: constructed:df7a832e992ced1bf2aff978cd1a8ccc1553929574f36054c8c4ca4e9329e29c

Black to move. Origin: `constructed_elementary`. Confidence: **exact**.

Objective: Force checkmate against every legal defence within 1 plies.

```text
. . . . . . . .
. . . . . . . .
. . . . . . . .
. . . . . . q .
. . . . . . . .
. . . . . . k .
. . . . . . . .
. . . . . . K .
  a b c d e f g h
```

FEN: `8/8/8/6q1/8/6k1/8/6K1 b - - 0 1`

Accepted alternatives: Qc1# (`g5c1`).

Source tags: mateIn1, endgame.

Proof type: `exhaustive_mate_within_1_plies`. Verification: `{"requested_nodes_per_pass": [80000, 320000], "actual_nodes_per_pass": [80036, 320211], "seconds": 0.23460379999596626, "exact_proof_nodes": 25, "mate_horizon_plies": 1}`.

Illustrative continuation: Qc1#.

No separate stable 200cp mistake label was assigned to this record. A failed short-mate objective is not automatically a proved lost game.

## 26. ordinary_negative_control: local:55902851b8830562ba6fa940e202bbb982dc2cc5cc596f44226a0c2a49d3fad4:90:sound

Black to move. Origin: `legal_branch_from_actual_game`. Confidence: **engine_supported**.

Objective: Choose a move within 70cp of the best at BOTH declared budgets. Estimated move quality, not proof of a win.

```text
. . . . . . . .
. . . . . . . .
. . . . . k . .
p . . . . p . .
. . P . p . . .
. K . B . . . .
. . . . . r . .
. . . . . . . .
  a b c d e f g h
```

FEN: `8/8/5k2/p4p2/2P1p3/1K1B4/5r2/8 b - - 1 48`

Accepted alternatives: a4+ (`a5a4`), exd3 (`e4d3`), Rf3 (`f2f3`), Ke5 (`f6e5`).

Source tags: .

Proof type: `two_budget_full_legal_root_analysis`. Verification: `{"requested_nodes_per_pass": [80000, 320000], "actual_nodes_per_pass": [80069, 320301], "seconds": 0.3663950000045588, "exact_proof_nodes": 21, "mate_horizon_plies": null}`.

Illustrative continuation: a4+ Kb4 exd3 c5 Rc2 Kb5.

Illustrative continuation: exd3 Kc3 d2 Kc2 Rh2 c5 Rg2 c6 d1=Q+ Kxd1.

Verified bad alternative `f2b2`: estimated regret [226, 242]cp at the two budgets; illustrative refutation `f2b2 b3b2 e4d3 b2c3 a5a4 c3d3 a4a3 d3c3 f5f4 c4c5`.

Verified bad alternative `f2c2`: estimated regret [662, 756]cp at the two budgets; illustrative refutation `f2c2 d3c2 f6e5 b3c3 e4e3`.

Source reference: `local:docs/evidence/magnus-mixed-20260906-games.json`. Family: `local:55902851b8830562ba6fa940e202bbb982dc2cc5cc596f44226a0c2a49d3fad4`.

## 27. punish_blunder: local:d7020136ac7d669e0ce235a3a6a1ca63c05cae7147e529ebe227d4a912cd12a2:19:mistake

White to move. Origin: `legal_branch_from_actual_game`. Confidence: **engine_supported**.

Objective: Choose a move within 70cp of the best at BOTH declared budgets. Estimated move quality, not proof of a win.

```text
. . k r . b . r
p p n . p . . p
. . p . b p . n
P . . p P . p .
. . . P . . . .
q P N B . N . .
. . P B . P P P
R . . Q . R K .
  a b c d e f g h
```

FEN: `2kr1b1r/ppn1p2p/2p1bp1n/P2pP1p1/3P4/qPNB1N2/2PB1PPP/R2Q1RK1 w - - 3 13`

Accepted alternatives: Rxa3 (`a1a3`).

Source tags: .

Proof type: `two_budget_full_legal_root_analysis`. Verification: `{"requested_nodes_per_pass": [80000, 320000], "actual_nodes_per_pass": [80075, 320386], "seconds": 1.1817995000019437, "exact_proof_nodes": 40, "mate_horizon_plies": null}`.

Illustrative continuation: Rxa3 fxe5 Nxg5 e4 Nxe6 exd3 Nxf8.

Verified bad alternative `a1b1`: estimated regret [514, 530]cp at the two budgets; illustrative refutation `a1b1 g5g4 b1a1 a3a1 d1a1 g4f3 a5a6`.

Verified bad alternative `a1c1`: estimated regret [481, 524]cp at the two budgets; illustrative refutation `a1c1 f6e5 d4e5 h6f7 a5a6 b7b6`.

Source reference: `local:docs/evidence/magnus-mixed-20260906-games.json`. Family: `local:d7020136ac7d669e0ce235a3a6a1ca63c05cae7147e529ebe227d4a912cd12a2`.

## 28. quiet_ideas: lichess:00iQC

White to move. Origin: `lichess_cc0_puzzle`. Confidence: **engine_supported**.

Objective: Choose a move within 70cp of the best at BOTH declared budgets. Estimated move quality, not proof of a win.

```text
. k . . . b . r
. . . r q . . .
Q B p p . . . .
. . . . p . . .
. . . . P . . p
. . . . . p . .
P . . . . . P P
. . . . R . K .
  a b c d e f g h
```

FEN: `1k3b1r/3rq3/QBpp4/4p3/4P2p/5p2/P5PP/4R1K1 w - - 1 29`

Accepted alternatives: Rb1 (`e1b1`).

Source tags: crushing, discoveredAttack, exposedKing, middlegame, queensideAttack, quietMove, veryLong.

Proof type: `two_budget_full_legal_root_analysis`. Verification: `{"requested_nodes_per_pass": [80000, 320000], "actual_nodes_per_pass": [80069, 320165], "seconds": 0.4851316999993287, "exact_proof_nodes": 36, "mate_horizon_plies": null}`.

Illustrative continuation: Rb1 Rb7 Ba7+ Ka8.

Verified bad alternative `a2a3`: estimated regret [510, 831]cp at the two budgets; illustrative refutation `a2a3 e7g7 g2g3 d7a7 a6a7 g7a7 b6a7 b8a7 e1b1 h4h3`.

Verified bad alternative `a2a4`: estimated regret [624, 965]cp at the two budgets; illustrative refutation `a2a4 e7g7 b6c7 d7c7 e1b1 c7b7 a6b7 g7b7`.

Source reference: `https://lichess.org/Yg1J59NW/black#56`. Family: `lichess:Yg1J59NW`.

## 29. fundamental_tactics: lichess:01ZpR

Black to move. Origin: `lichess_cc0_puzzle`. Confidence: **engine_supported**.

Objective: Choose a move within 70cp of the best at BOTH declared budgets. Estimated move quality, not proof of a win.

```text
. . r q . r k .
. p . . . p p p
p . . . . b . .
n . . . . . . b
. . . P p . . .
P . . . B . . P
. P . N B P P .
. . R Q . R K .
  a b c d e f g h
```

FEN: `2rq1rk1/1p3ppp/p4b2/n6b/3Pp3/P3B2P/1P1NBPP1/2RQ1RK1 b - - 1 18`

Accepted alternatives: Rxc1 (`c8c1`).

Source tags: crushing, opening, short.

Proof type: `two_budget_full_legal_root_analysis`. Verification: `{"requested_nodes_per_pass": [80000, 320000], "actual_nodes_per_pass": [80076, 320096], "seconds": 0.6824041000072611, "exact_proof_nodes": 36, "mate_horizon_plies": null}`.

Illustrative continuation: Rxc1 Qxc1 Bxe2 Nxe4 Bxf1 Qxf1 Bxd4 Bxd4 Qxd4.

Verified bad alternative `a5b3`: estimated regret [1352, 1287]cp at the two budgets; illustrative refutation `a5b3 d2b3 h5e2 d1e2 c8c1 b3c1`.

Verified bad alternative `a5c4`: estimated regret [1320, 1218]cp at the two budgets; illustrative refutation `a5c4 c1c4 c8c4 d2c4 h5e2 d1e2 d8d5 f1c1 f6d8 e2d1`.

Source reference: `https://lichess.org/DHFroHMk#35`. Family: `lichess:DHFroHMk`.

## 30. endgame: lichess:017zX

White to move. Origin: `lichess_cc0_puzzle`. Confidence: **engine_supported**.

Objective: Choose a move within 70cp of the best at BOTH declared budgets. Estimated move quality, not proof of a win.

```text
. . . . . . q k
. p . . . . p .
B . n . . r Q p
. . . p . . . .
. . . . . . . .
. . P . . P . .
P . . . . . . P
. . . . . . R K
  a b c d e f g h
```

FEN: `6qk/1p4p1/B1n2rQp/3p4/8/2P2P2/P6P/6RK w - - 1 30`

Accepted alternatives: Qxf6 (`g6f6`).

Source tags: crushing, discoveredAttack, endgame, long, master.

Proof type: `two_budget_full_legal_root_analysis`. Verification: `{"requested_nodes_per_pass": [80000, 320000], "actual_nodes_per_pass": [80021, 320394], "seconds": 0.6402662999898894, "exact_proof_nodes": 39, "mate_horizon_plies": null}`.

Illustrative continuation: Qxf6 gxf6 Rxg8+ Kxg8 Bxb7 Ne7 a4 Kf7 Kg2 Ke6.

Verified bad alternative `a2a3`: estimated regret [1286, 1311]cp at the two budgets; illustrative refutation `a2a3 f6g6 g1g6 g8f7 a6e2 f7g6 f3f4 g6e4 h1g1`.

Verified bad alternative `a2a4`: estimated regret [1164, 1147]cp at the two budgets; illustrative refutation `a2a4 f6g6`.

Source reference: `https://lichess.org/VCcicFSZ/black#58`. Family: `lichess:VCcicFSZ`.
