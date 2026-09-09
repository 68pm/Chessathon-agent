"""Collect a bounded local-only master-game curriculum from TWIC's free PGNs."""
import hashlib
import io
import json
import re
import urllib.request
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import chess
import chess.pgn

from scripts.continuation_common import ROOT, RUN, check_stop, digest, save

OUT=RUN/'opening-curriculum-02'


def family_of(game):
    eco=game.headers.get('ECO','')
    if re.fullmatch(r'C4[23]',eco):return 'Petroff'
    if re.fullmatch(r'E0[0-9]',eco):return 'Catalan'
    if re.fullmatch(r'C5[0-9]',eco):return 'Italian'
    if re.fullmatch(r'B2[3-6]',eco):return 'Closed Sicilian'
    return None


def run():
    check_stop()
    assert not OUT.exists()
    OUT.mkdir(parents=True)
    failed=RUN/'opening-curriculum-01/state.json'
    old=json.loads(failed.read_text())
    assert old['status']=='failed' and '401' in old['error'] and len(old['preset_positions'])==6
    state=dict(status='collecting',created_utc=datetime.now(timezone.utc).isoformat(),
        source_hashes={str(Path(__file__)):digest(Path(__file__)),str(failed):digest(failed)},
        preset_positions=old['preset_positions'],theory_sources=old['sources'],archives=[],games=[],
        source_notice='TWIC states personal use only. Raw archives and extracted PGNs stay local; '
                      'do not include them in GitHub publication or the submitted ZIP.',
        scope='Factual game records for offline personal training; no article text or runtime teacher lookup.')
    pools={k:[] for k in ('Petroff','Catalan','Italian','Closed Sicilian')}
    seen=set()
    try:
        for issue in (1661,1660):
            check_stop()
            url=f'https://theweekinchess.com/zips/twic{issue}g.zip'
            path=OUT/f'twic{issue}g.zip'
            req=urllib.request.Request(url,headers={'User-Agent':'Chessity personal chess study'})
            with urllib.request.urlopen(req,timeout=30) as response:
                assert response.status==200
                data=response.read(8000001)
            assert len(data)<=8000000
            path.write_bytes(data)
            count=0
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                members=[m for m in archive.infolist() if m.filename.lower().endswith('.pgn')]
                assert len(members)==1 and members[0].file_size<=40000000
                stream=io.StringIO(archive.read(members[0]).decode('utf-8-sig',errors='replace'))
                while True:
                    offset=stream.tell()
                    headers=chess.pgn.read_headers(stream)
                    if headers is None:break
                    count+=1
                    if count%250==0:check_stop()
                    try:ratings=[int(headers.get(k,'0')) for k in ('WhiteElo','BlackElo')]
                    except ValueError:continue
                    if min(ratings)<2500:continue
                    if re.search(r'titled|3-0|bullet|blitz|online',headers.get('Event',''),re.I):continue
                    eco=headers.get('ECO','')
                    if not re.fullmatch(r'C4[23]|E0[0-9]|C5[0-9]|B2[3-6]',eco):continue
                    end=stream.tell()
                    stream.seek(offset)
                    game=chess.pgn.read_game(stream)
                    stream.seek(end)
                    if game is None or game.errors or game.headers.get('Result') not in ('1-0','0-1','1/2-1/2'):continue
                    family=family_of(game)
                    board=game.board()
                    moves=[]
                    structure=False
                    for node in game.mainline():
                        assert node.move in board.legal_moves
                        board.push(node.move)
                        moves.append(node.move.uci())
                        if len(moves)<=30:
                            if family=='Catalan':structure |= board.piece_at(chess.G2)==chess.Piece(chess.BISHOP,chess.WHITE)
                            elif family=='Closed Sicilian':structure |= (board.piece_at(chess.G2)==chess.Piece(chess.BISHOP,chess.WHITE)
                                and board.piece_at(chess.D3)==chess.Piece(chess.PAWN,chess.WHITE))
                            else:structure=True
                    if not structure or len(moves)<42:continue
                    fingerprint=hashlib.sha256(json.dumps([game.board().fen(),moves]).encode()).hexdigest()
                    if fingerprint in seen:continue
                    seen.add(fingerprint)
                    pools[family].append(dict(game_hash=fingerprint,family=family,ratings=ratings,
                        headers=dict(game.headers),archive=url,archive_sha256=digest(path),
                        pgn=str(game)+'\n',split='unassigned'))
            state['archives'].append(dict(url=url,sha256=digest(path),games_scanned=count))
            save(OUT/'state.json',state)
            if all(len(v)>=6 for v in pools.values()):break
        for family,rows in pools.items():
            ordered=sorted(rows,key=lambda r:(-min(r['ratings']),r['game_hash']))[:6]
            # Reserve by hash before any engine label or model output is inspected.
            held=min(ordered,key=lambda r:r['game_hash'])['game_hash'] if len(ordered)>=3 else None
            for row in ordered:
                row['split']='reserved_test' if row['game_hash']==held else 'train'
                path=OUT/(row['game_hash']+'.pgn')
                path.write_text(row.pop('pgn'),encoding='utf-8',newline='\n')
                row['sha256']=digest(path)
                row['pgn_file']=path.name
                state['games'].append(row)
        state.update(status='complete_unlabelled',available_counts={k:len(v) for k,v in pools.items()},
            selected_counts=dict(Counter(r['family'] for r in state['games'])),
            independent_holdout_claim=False,
            holdout_note='Reserved before this fit; verify overlap against prior corpora and exact FEN/mirror keys before use.')
        assert all(state['selected_counts'].get(k,0)>=1 for k in pools), 'Missing family requires more source data.'
    except BaseException as error:
        state.update(status='failed',error=repr(error))
        raise
    finally:
        state['finished_utc']=datetime.now(timezone.utc).isoformat()
        save(OUT/'state.json',state)
    print(json.dumps({k:state[k] for k in ('status','available_counts','selected_counts')}),flush=True)


if __name__=='__main__':run()
