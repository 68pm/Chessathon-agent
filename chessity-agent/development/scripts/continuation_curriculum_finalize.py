"""Retain fresh TWIC games and fill the rare Closed Sicilian from existing GM data."""
import hashlib
import io
import json
import re
import shutil
from collections import Counter
from pathlib import Path

import chess
import chess.pgn

from scripts.continuation_common import ROOT, RUN, check_stop, digest, save

OUT=RUN/'opening-curriculum-03'


def fingerprint(game):
    board=game.board()
    moves=[]
    for node in game.mainline():
        assert node.move in board.legal_moves
        board.push(node.move)
        moves.append(node.move.uci())
    return hashlib.sha256(json.dumps([game.board().fen(),moves]).encode()).hexdigest()


def run():
    check_stop()
    assert not OUT.exists()
    OUT.mkdir(parents=True)
    prior=RUN/'opening-curriculum-02'
    state=json.loads((prior/'state.json').read_text())
    assert state['status']=='failed' and state['selected_counts']=={'Petroff':4,'Catalan':5,'Italian':6}
    corpus=ROOT/'data/three-phase-pack/grandmaster-games.pgn'
    rows=[]
    prior_hashes=set()
    with corpus.open(encoding='utf-8') as stream:
        while (game:=chess.pgn.read_game(stream)) is not None:
            assert not game.errors
            gh=fingerprint(game)
            prior_hashes.add(gh)
            if not re.fullmatch(r'B2[3-6]',game.headers.get('ECO','')):continue
            ratings=[int(game.headers.get(k,'0')) for k in ('WhiteElo','BlackElo')]
            assert min(ratings)>=2500
            path=OUT/(gh+'.pgn')
            path.write_text(str(game)+'\n',encoding='utf-8',newline='\n')
            rows.append(dict(game_hash=gh,family='Closed Sicilian',ratings=ratings,
                headers=dict(game.headers),source=str(corpus.relative_to(ROOT)),source_sha256=digest(corpus),
                split='train',pgn_file=path.name,sha256=digest(path),previously_available=True))
    for row in state['games']:
        source=prior/row['pgn_file']
        assert digest(source)==row['sha256']
        target=OUT/row['pgn_file']
        shutil.copyfile(source,target)
        assert digest(target)==row['sha256']
        item=dict(row,previously_available=row['game_hash'] in prior_hashes)
        if item['split']=='reserved_test' and item['previously_available']:
            item['split']='train'
            item['reservation_exclusion']='Full-game duplicate in earlier three-phase corpus'
        rows.append(item)
    result=dict(status='complete_unlabelled',games=rows,preset_positions=state['preset_positions'],
        theory_sources=state['theory_sources'],source_notice=state['source_notice'],
        counts=dict(Counter(r['family'] for r in rows)),
        source_sha256={str(p):digest(p) for p in (Path(__file__),prior/'state.json',corpus)},
        reservation_note='Three fresh game groups reserved before labels; Closed Sicilian examples are reused training only. '
            'Full-game overlap checked against the earlier three-phase corpus. FEN/mirror checks still required against the actual fit.',
        independent_holdout_claim=False)
    assert result['counts']=={'Closed Sicilian':2,'Petroff':4,'Catalan':5,'Italian':6}
    assert sum(r['split']=='reserved_test' for r in rows)==3
    save(OUT/'state.json',result)
    print(json.dumps({'status':result['status'],'counts':result['counts'],'reserved_games':3}),flush=True)


if __name__=='__main__':run()
