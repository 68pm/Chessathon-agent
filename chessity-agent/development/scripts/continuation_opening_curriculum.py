"""Public master-game curriculum for sound openings actually present in the field."""
import csv
import hashlib
import io
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import chess
import chess.pgn

from scripts.continuation_common import ROOT, RUN, check_stop, digest, save

OUT=RUN/'opening-curriculum-01'
FAMILIES={
    'Petroff': 'e4 e5 Nf3 Nf6 Nxe5 d6 Nf3 Nxe4 d4 d5',
    'Catalan': 'd4 Nf6 c4 e6 Nf3 d5 g3 Be7 Bg2 O-O',
    'Italian': 'e4 e5 Nf3 Nc6 Bc4 Nf6 d3',
    'Closed Sicilian': 'e4 c5 Nc3 Nc6 g3 g6 Bg2 Bg7 d3 d6',
}
REACH={
    ('own',83):('Petroff','e4 e5 Nf3 Nf6 Nxe5 d6 Nf3 Nxe4 d4 d5 Be2 Bd6 O-O c6 c4'),
    ('own',82):('Catalan','d4 d5 c4 e6 Nf3 Nf6 g3 Be7 Bg2 O-O O-O b6 b3 c6'),
    ('own',81):('Closed Sicilian','e4 c5 Nc3 Nc6 g3 g6 Bg2 Bg7 d3 d6 f4'),
    ('leader',83):('Closed Sicilian','e4 c5 Nc3 Nc6 g3 g6 Bg2 Bg7 d3 d6 Nf3 Nf6'),
    ('leader',82):('Catalan','d4 Nf6 c4 e6 Nf3 d5 g3 Be7 Bg2 O-O Na3'),
    ('leader',81):('Italian','e4 e5 Nf3 Nc6 Bc4 Nf6 d3 Be7 O-O O-O Nc3 d6 a4'),
}


def key(board):return ' '.join(board.fen().split()[:4])


def replay(san):
    board=chess.Board()
    for token in san.split():board.push_san(token)
    return board


def fetch(url,path):
    check_stop()
    req=urllib.request.Request(url,headers={'User-Agent':'Chessity offline opening training',
                                           'Accept':'application/json, application/x-chess-pgn'})
    with urllib.request.urlopen(req,timeout=25) as response:
        assert response.status==200
        data=response.read(2000001)
    assert len(data)<=2000000
    path.write_bytes(data)
    time.sleep(.5)
    return data.decode('utf-8')


def run():
    check_stop()
    assert not OUT.exists()
    OUT.mkdir(parents=True)
    state=dict(status='collecting',created_utc=datetime.now(timezone.utc).isoformat(),
        code_sha256=digest(Path(__file__)),preset_positions=[],observations=[],games=[],
        sources=['https://lichess.org/api','https://github.com/lichess-org/chess-openings',
            'https://www.chess.com/article/view/perfect-chess-opening-repertoire-white',
            'https://www.chess.com/article/view/perfect-chess-opening-repertoire-black',
            'https://www.chess.com/article/view/making-a-plus-in-the-petroff',
            'https://www.chess.com/article/view/attack-with-the-catalan',
            'https://www.chess.com/article/view/vassily-smyslov-and-the-closed-sicilian'],
        scope='Offline training data and explanation only; no runtime teacher move/evaluation lookup.')
    save(OUT/'state.json',state)
    try:
        reference=ROOT/'data/three-phase-pack/opening-reference.tsv'
        state['reference_sha256']=digest(reference)
        index={}
        with reference.open(encoding='utf-8-sig',newline='') as stream:
            for row in csv.DictReader(stream,delimiter='\t'):
                index.setdefault(key(chess.Board(row['fen'])),[]).append({k:row[k] for k in ('eco','name')})
        for side in ('own','leader'):
            path=RUN/'field-review-01'/f'{side}-games.json'
            for record in json.loads(path.read_text())['games']:
                game=chess.pgn.read_game(io.StringIO(record['pgn']))
                family,line=REACH[(side,record['id'])]
                reconstructed=replay(line)
                assert key(reconstructed)==key(game.board())
                named=[]
                board=chess.Board()
                for san in line.split():
                    board.push_san(san)
                    if key(board) in index:named=index[key(board)]
                state['preset_positions'].append(dict(side=side,round=record['id'],family=family,
                    fen=game.board().fen(),candidate_white=record['candidate_white'],
                    named_ancestor=named,legal_reaching_line=line,
                    note='One legal reaching line verifies the opening family, not the actual preset move order. '
                         'Keep the PGN start FEN and clocks; do not fabricate pregame history.'))
        seen=set()
        for family,line in FAMILIES.items():
            board=replay(line)
            slug=family.lower().replace(' ','-')
            params=urllib.parse.urlencode(dict(play=','.join(m.uci() for m in board.move_stack),
                                              since=2015,moves=8,topGames=6))
            url='https://explorer.lichess.org/masters?'+params
            path=OUT/(slug+'-masters.json')
            document=json.loads(fetch(url,path))
            observation=dict(family=family,url=url,sha256=digest(path),
                games_available=sum(document[k] for k in ('white','draws','black')),game_ids=[])
            for row in document.get('topGames',[]):
                gid=row['id']
                assert re.fullmatch(r'[A-Za-z0-9]{8}',gid)
                if gid in seen:continue
                pgn_url='https://explorer.lichess.org/masters/pgn/'+gid
                pgn_path=OUT/(gid+'.pgn')
                pgn=fetch(pgn_url,pgn_path)
                game=chess.pgn.read_game(io.StringIO(pgn))
                assert game is not None and not game.errors
                legal=game.board()
                contains=False
                moves=[]
                for node in game.mainline():
                    assert node.move in legal.legal_moves
                    legal.push(node.move)
                    moves.append(node.move.uci())
                    contains |= key(legal)==key(board)
                ratings=[int(game.headers.get(k,'0')) for k in ('WhiteElo','BlackElo')]
                eligible=contains and min(ratings)>=2500 and game.headers['Result'] in ('1-0','0-1','1/2-1/2')
                state['games'].append(dict(id=gid,family=family,url=pgn_url,sha256=digest(pgn_path),
                    game_hash=hashlib.sha256(json.dumps([game.board().fen(),moves]).encode()).hexdigest(),
                    ratings=ratings,headers=dict(game.headers),contains_family_anchor=contains,
                    source_eligible=eligible,split='unassigned',value_labels=None))
                observation['game_ids'].append(gid)
                seen.add(gid)
                save(OUT/'state.json',state)
            state['observations'].append(observation)
            save(OUT/'state.json',state)
        for family in FAMILIES:
            rows=sorted((r for r in state['games'] if r['family']==family and r['source_eligible']),
                        key=lambda r:r['game_hash'])
            assert len(rows)>=3, 'Insufficient source games; retain partial collection without fitting.'
            for i,row in enumerate(rows):row['split']='reserved_test' if i==0 else 'train'
        state['status']='complete_unlabelled'
    except BaseException as error:
        state.update(status='failed',error=repr(error))
        raise
    finally:
        state['finished_utc']=datetime.now(timezone.utc).isoformat()
        save(OUT/'state.json',state)
    print(json.dumps(dict(status=state['status'],presets=[dict(side=r['side'],round=r['round'],family=r['family'])
        for r in state['preset_positions']],games=len(state['games']),
        train=sum(r['split']=='train' for r in state['games']),
        reserved=sum(r['split']=='reserved_test' for r in state['games']))),flush=True)


if __name__=='__main__':run()
