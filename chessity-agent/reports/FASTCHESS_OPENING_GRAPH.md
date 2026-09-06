# Fast-chess opening pilot

The graph is an offline training curriculum. It is not included in the competition agent and its training-board recall is reported separately from held-out play.

| Family | Verified own-side nodes |
|---|---:|
| caro_kann | 100 |
| fallback | 48 |
| italian | 100 |
| qgd | 100 |
| queens_gambit | 40 |

Every root decision has full legal alternatives at 80k and 320k Stockfish nodes, explicit mover-relative scores, uncertainty and PGN/reference provenance. Where opponent-reply verification remains unresolved it is marked as such. The graph merges actual transpositions by state and keeps history separately. It is a small selection of decisions; uncovered openings still require normal search.

These are original study prompts and mechanically checked board facts. General plans are not rewards and do not establish positional understanding. Teacher-labelled lookup data remains outside the runtime ZIP.

## Selected training examples

### italian: graph:b7e4f4d1a15b3950507cb0bcd781d7e45a03a64e67bda89575546fec96bebce9

FEN: `r1bqk1nr/pppp1ppp/2n5/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4`

Supported move: **c3**. Sound alternatives: `a2a3, a2a4, b1c3, b2b4, c2c3, c4b3, c4d5, d1e2, d2d3, d2d4, e1g1, h2h3`. Concrete continuation estimate: c3 Nf6 d3 O-O O-O h6 b4 Bb6.

Compare d3 preparation with c3/d4 expansion; check ...d5 and f7 tactics before spending tempi on a knight route.

Current structure: `{"isolated_pawns": {"white": [], "black": []}, "open_files": [], "queens_present": 2, "note": "Mechanically checked current structure; no promise that a specific pawn break or endgame will be reached."}`.

Sample-rare strong replies: `c5b6, d7d6, d8f6, g8f6`. See the graph for full verification and sampled frequencies.

### italian: graph:a4f113d792e04dacd69fadd0e7c815d2cf4974cdec8000c15cd6b79d16e907f6

FEN: `r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQ1RK1 w kq - 6 5`

Supported move: **d3**. Sound alternatives: `b1c3, c4b3, c4b5, c4d5, d1e1, d1e2, d2d3, d2d4, f1e1`. Concrete continuation estimate: d3 h6 Nc3.

Compare d3 preparation with c3/d4 expansion; check ...d5 and f7 tactics before spending tempi on a knight route.

Current structure: `{"isolated_pawns": {"white": [], "black": []}, "open_files": [], "queens_present": 2, "note": "Mechanically checked current structure; no promise that a specific pawn break or endgame will be reached."}`.

Sample-rare strong replies: `a7a5, a7a6, a8b8, c5b6, c5e7, d7d5, d7d6, d8e7, e8g8, h7h6`. See the graph for full verification and sampled frequencies.

### italian: graph:d118e7d024d16f8c22d2d1dd42a1b88b87e40d384a7e4f14c5ad3b24905e9fbf

FEN: `r1bqk1nr/pppp2pp/2n5/2b1pp2/2B1P3/3P1N2/PPP2PPP/RNBQK2R w KQkq - 0 5`

Supported move: **Ng5**. Sound alternatives: `b1c3, f3g5`. Concrete continuation estimate: Ng5 Nf6.

Compare d3 preparation with c3/d4 expansion; check ...d5 and f7 tactics before spending tempi on a knight route.

Current structure: `{"isolated_pawns": {"white": [], "black": []}, "open_files": [], "queens_present": 2, "note": "Mechanically checked current structure; no promise that a specific pawn break or endgame will be reached."}`.

Sample-rare strong replies: `d7d5, d7d6, f5f4`. See the graph for full verification and sampled frequencies.

### italian: graph:1857fccc23380816117d5d921619829dfdc9d2a99a9eb4acd90f060d805bf839

FEN: `r1bqk1nr/ppppbppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4`

Supported move: **d4**. Sound alternatives: `a2a3, a2a4, b1c3, c2c3, c4b3, c4b5, c4d5, d1e2, d2d3, d2d4, e1g1, h2h3`. Concrete continuation estimate: d4 d6 h3 exd4 Nxd4 Nf6 Nxc6 bxc6.

Compare d3 preparation with c3/d4 expansion; check ...d5 and f7 tactics before spending tempi on a knight route.

Current structure: `{"isolated_pawns": {"white": [], "black": []}, "open_files": [], "queens_present": 2, "note": "Mechanically checked current structure; no promise that a specific pawn break or endgame will be reached."}`.

Sample-rare strong replies: `c6a5, d7d6, e5d4`. See the graph for full verification and sampled frequencies.

### caro_kann: graph:b3dfb2aa4dbf0ca635a70c8775011d996cf24b35b0def3223197b0fc4432a8ae

FEN: `rnbqkbnr/pp2pppp/2p5/3P4/2P5/8/PP1P1PPP/RNBQKBNR b KQkq - 0 3`

Supported move: **Nf6**. Sound alternatives: `a7a6, c6d5, g7g6, g8f6, h7h6`. Concrete continuation estimate: Nf6 Nc3 cxd5 d4 Nc6 Nf3 Bg4 Be2.

Coordinate the light-squared bishop and king safety; compare ...c5/...f6 breaks only when the concrete line supports them.

Current structure: `{"isolated_pawns": {"white": [], "black": []}, "open_files": [], "queens_present": 2, "note": "Mechanically checked current structure; no promise that a specific pawn break or endgame will be reached."}`.

Sample-rare strong replies: `a2a3, a2a4, b1a3, b1c3, b2b3, d1a4, d1b3, d1c2, d2d3, d2d4, d5c6, f1e2, g1f3, g2g3, h2h3, h2h4`. See the graph for full verification and sampled frequencies.

### caro_kann: graph:769b3694906ac682a597843f4d64b4e7e261762acca2b80e881467de19b2d6aa

FEN: `rnbqkbnr/pp2pppp/8/3P4/8/8/PP1P1PPP/RNBQKBNR b KQkq - 0 4`

Supported move: **Nf6**. Sound alternatives: `a7a6, b8d7, c8f5, d8d5, g7g6, g8f6`. Concrete continuation estimate: Nf6 Bc4 Nxd5 Nf3 e6 O-O Be7 Nc3.

Coordinate the light-squared bishop and king safety; compare ...c5/...f6 breaks only when the concrete line supports them.

Current structure: `{"isolated_pawns": {"white": ["d2", "d5"], "black": []}, "open_files": ["c"], "queens_present": 2, "note": "Mechanically checked current structure; no promise that a specific pawn break or endgame will be reached."}`.

Sample-rare strong replies: `a2a3, a2a4, b1a3, b1c3, b2b3, d1a4, d1b3, d1f3, d2d3, d2d4, f1b5, f1c4, f1e2, g1e2, g1f3, g2g3, h2h3, h2h4`. See the graph for full verification and sampled frequencies.

### caro_kann: graph:f2aa2a4bd432c955e9206777e52fe70dfbef94716a07f83e44fb036a9828711d

FEN: `rnbqkbnr/pp2pppp/2p5/3P4/4P3/8/PP1P1PPP/RNBQKBNR b KQkq - 0 3`

Supported move: **cxd5**. Sound alternatives: `a7a6, c6d5, g8f6`. Concrete continuation estimate: cxd5 exd5 Nf6 Bb5+ Nbd7 d4.

Coordinate the light-squared bishop and king safety; compare ...c5/...f6 breaks only when the concrete line supports them.

Current structure: `{"isolated_pawns": {"white": [], "black": []}, "open_files": [], "queens_present": 2, "note": "Mechanically checked current structure; no promise that a specific pawn break or endgame will be reached."}`.

Sample-rare strong replies: `e4d5, e4e5, f1b5`. See the graph for full verification and sampled frequencies.

### caro_kann: graph:df0d5342bf6198825b2f2a8557a87b843363a7051736aa4fd42780e3c7dcec92

FEN: `rnbqkbnr/pp2pppp/2p5/3P4/8/5N2/PPPP1PPP/RNBQKB1R b KQkq - 0 3`

Supported move: **cxd5**. Sound alternatives: `c6d5, d8d5`. Concrete continuation estimate: cxd5 d4 Nc6 Ne5 e6 Bb5 Bd7 Nxd7.

Coordinate the light-squared bishop and king safety; compare ...c5/...f6 breaks only when the concrete line supports them.

Current structure: `{"isolated_pawns": {"white": [], "black": []}, "open_files": [], "queens_present": 2, "note": "Mechanically checked current structure; no promise that a specific pawn break or endgame will be reached."}`.

Sample-rare strong replies: `a2a3, a2a4, b1a3, b1c3, b2b3, b2b4, c2c3, c2c4, d1e2, d2d3, d2d4, f1b5, f1d3, f1e2, f3d4, f3e5, f3g1, g2g3, h1g1, h2h3, h2h4`. See the graph for full verification and sampled frequencies.

### qgd: graph:0cb887278c543fa96f9a4ced9336b490ef4052476f39695e5ba6ce4192fa4cd8

FEN: `rnbqkb1r/ppp2ppp/4pn2/3p2B1/2PP4/5N2/PP2PPPP/RN1QKB1R b KQkq - 1 4`

Supported move: **dxc4**. Sound alternatives: `a7a5, a7a6, b7b6, b8a6, b8c6, b8d7, c7c5, c7c6, c8d7, d5c4, f8b4, f8d6, f8e7, g7g6, h7h6`. Concrete continuation estimate: dxc4 Nc3 a6 e3 b5 a4 c6 axb5.

Preserve central tension or release it with justified ...c5/...e5; watch the c-file, minority attack and isolated-pawn transitions.

Current structure: `{"isolated_pawns": {"white": [], "black": []}, "open_files": [], "queens_present": 2, "note": "Mechanically checked current structure; no promise that a specific pawn break or endgame will be reached."}`.

Sample-rare strong replies: `a2a4, b1c3, b1d2, d1a4, d1c1, d1c2, e2e3, e2e4, g2g3, g5f6`. See the graph for full verification and sampled frequencies.

### qgd: graph:36fb9275c7ed2cc0b156f137ec5651587fc50b8f3c9f6eb470f7c1b8bfafc7a9

FEN: `rnbqkb1r/pp3ppp/2p1pn2/3p2B1/2PP4/5N2/PP1NPPPP/R2QKB1R b KQkq - 1 5`

Supported move: **dxc4**. Sound alternatives: `a7a5, a7a6, b7b6, b8a6, b8d7, c6c5, c8d7, d5c4, d8a5, d8b6, f8b4, f8d6, f8e7, h7h6`. Concrete continuation estimate: dxc4 Nxc4 c5 dxc5 Qxd1+ Rxd1 Bxc5.

Preserve central tension or release it with justified ...c5/...e5; watch the c-file, minority attack and isolated-pawn transitions.

Current structure: `{"isolated_pawns": {"white": [], "black": []}, "open_files": [], "queens_present": 2, "note": "Mechanically checked current structure; no promise that a specific pawn break or endgame will be reached."}`.

Sample-rare strong replies: `d2c4, e2e4, g5f6`. See the graph for full verification and sampled frequencies.

### qgd: graph:3736565f2096fc5f3ecc65b3822a5362b5d537d9b1c5d1e60e882c1f1ea661f8

FEN: `rnbqkbnr/pp2pppp/2p5/3p4/2PP4/5N2/PP2PPPP/RNBQKB1R b KQkq - 1 3`

Supported move: **Nf6**. Sound alternatives: `a7a5, a7a6, b8d7, c8d7, c8e6, c8f5, d5c4, d8a5, d8b6, d8c7, d8d6, e7e6, g7g6, g8f6, h7h5, h7h6`. Concrete continuation estimate: Nf6 e3 Bf5 cxd5 cxd5 Qb3 Qc7 Nc3.

Preserve central tension or release it with justified ...c5/...e5; watch the c-file, minority attack and isolated-pawn transitions.

Current structure: `{"isolated_pawns": {"white": [], "black": []}, "open_files": [], "queens_present": 2, "note": "Mechanically checked current structure; no promise that a specific pawn break or endgame will be reached."}`.

Sample-rare strong replies: `a2a3, a2a4, b1a3, b1c3, b1d2, b2b3, c1d2, c1e3, c1f4, c1g5, c4c5, c4d5, d1a4, d1b3, d1c2, d1d2, d1d3, e2e3, f3d2, f3e5, g2g3, h2h3, h2h4`. See the graph for full verification and sampled frequencies.

### qgd: graph:a712166a416e38b0c59c3dc2bcdbf0d0b735ab62eacdfccb79c41cbd0c9d889e

FEN: `rnbqkb1r/pp2pppp/2p2n2/3p4/2PP4/4PN2/PP3PPP/RNBQKB1R b KQkq - 0 4`

Supported move: **Bg4**. Sound alternatives: `a7a5, a7a6, b7b6, b8a6, b8d7, c8d7, c8e6, c8f5, c8g4, d8a5, d8b6, d8c7, d8d6, d8d7, e7e6, f6d7, f6e4, f6g4, f6g8, f6h5, g7g6, h7h5, h7h6`. Concrete continuation estimate: Bg4 Qb3 Qc7 Ne5 Be6 Nc3 Nbd7 cxd5.

Preserve central tension or release it with justified ...c5/...e5; watch the c-file, minority attack and isolated-pawn transitions.

Current structure: `{"isolated_pawns": {"white": [], "black": []}, "open_files": [], "queens_present": 2, "note": "Mechanically checked current structure; no promise that a specific pawn break or endgame will be reached."}`.

Sample-rare strong replies: `a2a3, a2a4, b1a3, b1c3, b1d2, b2b3, b2b4, c1d2, c4c5, c4d5, d1a4, d1b3, d1c2, d1d2, d1d3, d1e2, f1d3, f1e2, g2g3, h1g1, h2h3, h2h4`. See the graph for full verification and sampled frequencies.

### queens_gambit: graph:d23691b4dcfa3ab605f2d4a10be0576531621b93e1af5f6f82b537119c4e3915

FEN: `rnbqkb1r/pppp1ppp/4pn2/8/2PP4/8/PP2PPPP/RNBQKBNR w KQkq - 0 3`

Supported move: **Nc3**. Sound alternatives: `a2a3, a2a4, b1a3, b1c3, b1d2, b2b3, c1d2, c1e3, c1f4, c1g5, c4c5, d1a4, d1b3, d1c2, d1d2, d1d3, d4d5, e2e3, f2f4, g1f3, g1h3, g2g3, g2g4, h2h3, h2h4`. Concrete continuation estimate: Nc3 d5 Bg5 Be7 Nf3 h6 Bxf6 Bxf6.

Compare central expansion with queenside play; first identify accepted, declined, Slav or Indian structures.

Current structure: `{"isolated_pawns": {"white": [], "black": []}, "open_files": [], "queens_present": 2, "note": "Mechanically checked current structure; no promise that a specific pawn break or endgame will be reached."}`.

Sample-rare strong replies: `b8c6, d7d5, d7d6`. See the graph for full verification and sampled frequencies.

### queens_gambit: graph:3c6f429bd2f61f96ed0b44362ef1ce336a86a15095936e1c6c7b57cdd1879221

FEN: `rnbqkb1r/ppp2ppp/4pn2/3p4/2PP4/5N2/PP2PPPP/RNBQKB1R w KQkq - 0 4`

Supported move: **Nc3**. Sound alternatives: `a2a3, a2a4, b1a3, b1c3, b1d2, b2b3, c1d2, c1e3, c1f4, c1g5, c4c5, c4d5, d1a4, d1b3, d1c2, d1d2, d1d3, e2e3, f3e5, g2g3, g2g4, h2h3, h2h4`. Concrete continuation estimate: Nc3 c5 cxd5 cxd4 Qxd4 exd5 Bg5 Be7.

Compare central expansion with queenside play; first identify accepted, declined, Slav or Indian structures.

Current structure: `{"isolated_pawns": {"white": [], "black": []}, "open_files": [], "queens_present": 2, "note": "Mechanically checked current structure; no promise that a specific pawn break or endgame will be reached."}`.

Sample-rare strong replies: `a7a5, a7a6, b7b6, b8a6, b8c6, b8d7, c7c5, c7c6, c8d7, d5c4, d8d7, f6e4, f8b4, f8d6, g7g6, h7h6`. See the graph for full verification and sampled frequencies.

### queens_gambit: graph:19ad5b132cb30eb622b216701b1037273f75442c03cb82ce8e0590d5c2ebb1b4

FEN: `rnbqkb1r/pp3ppp/2p1pn2/3p2B1/2PP4/5N2/PP2PPPP/RN1QKB1R w KQkq - 0 5`

Supported move: **e3**. Sound alternatives: `a2a4, b1c3, b1d2, c4d5, d1a4, d1b3, d1c1, d1c2, d1d3, e2e3, g2g3, g5f6`. Concrete continuation estimate: e3 h6 Bh4 Be7 Nc3 O-O Be2.

Compare central expansion with queenside play; first identify accepted, declined, Slav or Indian structures.

Current structure: `{"isolated_pawns": {"white": [], "black": []}, "open_files": [], "queens_present": 2, "note": "Mechanically checked current structure; no promise that a specific pawn break or endgame will be reached."}`.

Sample-rare strong replies: `a7a5, a7a6, b7b6, b8a6, b8d7, c8d7, d5c4, d8a5, d8b6, d8c7, d8d6, d8d7, f8b4, f8d6, f8e7, g7g6, h7h6`. See the graph for full verification and sampled frequencies.

### queens_gambit: graph:91ec6a511742e713c9fb77de84dff32172dafc4ae7e2abf254b64df187c9808e

FEN: `r1bqkb1r/pp1n1ppp/2p1pn2/3p2B1/2PP4/5N2/PP1NPPPP/R2QKB1R w KQkq - 2 6`

Supported move: **e3**. Sound alternatives: `a1b1, a1c1, a2a3, a2a4, b2b3, c4c5, c4d5, d1a4, d1b1, d1b3, d1c1, d1c2, e2e3, f3e5, g2g3, g5f4, g5f6, g5h4, h2h3, h2h4`. Concrete continuation estimate: e3 h6 Bh4 g5 Bg3 Nh5 Be5.

Compare central expansion with queenside play; first identify accepted, declined, Slav or Indian structures.

Current structure: `{"isolated_pawns": {"white": [], "black": []}, "open_files": [], "queens_present": 2, "note": "Mechanically checked current structure; no promise that a specific pawn break or endgame will be reached."}`.

Sample-rare strong replies: `a7a5, a7a6, a8b8, c6c5, d5c4, d7b6, d8a5, d8b6, f8b4, f8d6, f8e7, g7g6, h7h6`. See the graph for full verification and sampled frequencies.

### fallback: graph:111dfb260feec4ac881032098c4f315e716449ca296f8ae5e7a22aeb980efe52

FEN: `rnbq1rk1/pp2ppbp/3p1np1/2pP4/2P1P3/2N2N2/PP2BPPP/R1BQK2R b KQ - 3 7`

Supported move: **e6**. Sound alternatives: `a7a6, b7b5, b7b6, b8a6, b8d7, c8d7, c8g4, d8a5, d8c7, e7e6, f6e8, f8e8, h7h6`. Concrete continuation estimate: e6 Bf4 exd5 cxd5 Bg4 O-O Re8 Nd2.

Develop and contest the centre while checking the opponent's actual threats; depart from the planned family when their moves require it.

Current structure: `{"isolated_pawns": {"white": [], "black": []}, "open_files": [], "queens_present": 2, "note": "Mechanically checked current structure; no promise that a specific pawn break or endgame will be reached."}`.

Sample-rare strong replies: `a1b1, a2a3, a2a4, c1d2, c1e3, c1f4, c1g5, d1b3, d1c2, d5e6, e1g1, e2d3, f3d2, h2h3`. See the graph for full verification and sampled frequencies.

### fallback: graph:1b83315333b5802cc165d0037d9552ae00f929eefe22a5b5fe68b2275ffb43ef

FEN: `2r3k1/p1q1ppbp/6p1/2P3B1/8/P2Q4/5PPP/5RK1 b - - 0 21`

Supported move: **Qxc5**. Sound alternatives: `a7a5, c7b7, c7c5, c7e5, c8a8, c8b8, c8d8, c8e8, g7b2, g7e5, g7f6, g7h8, g8f8, h7h5, h7h6`. Concrete continuation estimate: Qxc5 Be3 Qa5 Rd1 Bf6 Qd7 Rc7.

Develop and contest the centre while checking the opponent's actual threats; depart from the planned family when their moves require it.

Current structure: `{"isolated_pawns": {"white": ["a3", "c5"], "black": ["a7"]}, "open_files": ["b", "d"], "queens_present": 2, "note": "Mechanically checked current structure; no promise that a specific pawn break or endgame will be reached."}`.

Sample-rare strong replies: `d3d7, g5e3, h2h4`. See the graph for full verification and sampled frequencies.

### fallback: graph:854f4c33b94056a09cad6d39d9e041b373164582902152aa3de2dd83f2a51e2a

FEN: `r3kb1r/1b1n1p2/1q2p2p/p2pP3/1ppP4/2P2N2/PPQNBPP1/KR5R b kq - 1 22`

Supported move: **Ba6**. Sound alternatives: `a8b8, b6c6, b7a6, b7c6, d7b8, e8e7, f8e7, h8g8`. Concrete continuation estimate: Ba6 Bd1 Nb8 Ng5 Nc6 Nh7 Be7 Rxh6.

Develop and contest the centre while checking the opponent's actual threats; depart from the planned family when their moves require it.

Current structure: `{"isolated_pawns": {"white": [], "black": ["h6"]}, "open_files": [], "queens_present": 2, "note": "Mechanically checked current structure; no promise that a specific pawn break or endgame will be reached."}`.

Sample-rare strong replies: `a2a3, b1d1, b1e1, b1f1, b1g1, c2c1, c2d1, e2d1, f3e1, f3g1, f3g5, f3h2, f3h4, g2g3, g2g4, h1h3`. See the graph for full verification and sampled frequencies.

### fallback: graph:0cbd1d7e4e7100505a18516e92fd85877cf62e11a23b447b144cdc3a93033f10

FEN: `1r2k2r/p3pp2/4b1p1/4P1Pp/3nB3/2N5/PP4P1/2R2RK1 b k - 2 21`

Supported move: **Rxb2**. Sound alternatives: `b8b2, b8b4, b8d8, e6g4, e8g8`. Concrete continuation estimate: Rxb2 Rfd1 Ne2+ Nxe2 Rxe2 Rd4 O-O Rc7.

Develop and contest the centre while checking the opponent's actual threats; depart from the planned family when their moves require it.

Current structure: `{"isolated_pawns": {"white": ["g2", "e5", "g5"], "black": ["a7"]}, "open_files": ["c", "d"], "queens_present": 0, "note": "Mechanically checked current structure; no promise that a specific pawn break or endgame will be reached."}`.

Sample-rare strong replies: `f1d1`. See the graph for full verification and sampled frequencies.
