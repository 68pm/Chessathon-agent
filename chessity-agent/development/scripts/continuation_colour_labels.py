"""Add actual Black positions and reserve unused whole Italian games before labels."""
import argparse
import io
import json
import re
import zipfile
from pathlib import Path

import chess
import chess.pgn

from scripts.continuation_common import ROOT,RUN,check_stop,digest,save
from scripts.continuation_gm_labels import active,CURRICULUM
from scripts.continuation_curriculum_finalize import fingerprint
from scripts.overnight_value_labels import duplicate,restore
from scripts.overnight_capacity import wait_for_capacity

OUT=RUN/'gm-colour-values-01'
FIT=RUN/'curriculum-value-02'


def positions(game,group,split,plies):
    board=game.board();rows=[];keys={duplicate(board)}
    for ply,node in enumerate(game.mainline(),1):
        assert node.move in board.legal_moves
        board.push(node.move);keys.add(duplicate(board))
        if ply in plies:
            rows.append(dict(id=f'{group}-{ply}',group=group,split=split,white=board.turn,
                start_fen=game.board().fen(),history=[m.uci() for m in board.move_stack],
                fen=board.fen(),key=duplicate(board)))
    return rows,keys


def prepare():
    check_stop();assert not OUT.exists()
    old=json.loads((RUN/'curriculum-black-check-01/state.json').read_text())
    assert old['status']=='complete' and not old['passed']
    source=CURRICULUM/'state.json';curriculum=json.loads(source.read_text())
    used={r['game_hash'] for r in curriculum['games']}
    corpus=ROOT/'data/three-phase-pack/grandmaster-games.pgn'
    with corpus.open(encoding='utf-8') as stream:
        while (game:=chess.pgn.read_game(stream)) is not None:
            check_stop();assert not game.errors;used.add(fingerprint(game))
    pools={};sources={str(source):digest(source),str(corpus):digest(corpus)}
    archives=json.loads((RUN/'opening-curriculum-02/state.json').read_text())['archives']
    for archive in archives:
        path=RUN/'opening-curriculum-02'/archive['url'].rsplit('/',1)[-1]
        assert digest(path)==archive['sha256'];sources[str(path)]=digest(path)
        with zipfile.ZipFile(path) as pack:
            names=[n for n in pack.namelist() if n.lower().endswith('.pgn')];assert len(names)==1
            stream=io.StringIO(pack.read(names[0]).decode('utf-8-sig',errors='replace'))
        while True:
            offset=stream.tell();headers=chess.pgn.read_headers(stream)
            if headers is None:break
            if not re.fullmatch(r'C5[0-9]',headers.get('ECO','')):continue
            try:ratings=[int(headers.get(k,'0')) for k in ('WhiteElo','BlackElo')]
            except ValueError:continue
            if min(ratings)<2500 or re.search(r'titled|3-0|bullet|blitz|online',headers.get('Event',''),re.I):continue
            end=stream.tell();stream.seek(offset);game=chess.pgn.read_game(stream);stream.seek(end)
            if game is None or game.errors or game.headers.get('Result') not in ('1-0','0-1','1/2-1/2'):continue
            moves=list(game.mainline_moves())
            if len(moves)<84:continue
            gh=fingerprint(game)
            if gh not in used:pools[gh]=(game,archive['url'],archive['sha256'])
    assert len(pools)>=3
    OUT.mkdir(parents=True);(OUT/'local-pgn').mkdir()
    planned=[];protected=set();reserved=[]
    for gh in sorted(pools)[:3]:
        game,url,archive_hash=pools[gh]
        path=OUT/'local-pgn'/f'{gh}.pgn';path.write_text(str(game)+'\n',encoding='utf-8',newline='\n')
        rows,keys=positions(game,gh,'reserved_test',(20,21,32,33,44,45,56,57,68,69,80,81))
        planned+=rows;protected|=keys
        reserved.append(dict(group=gh,headers=dict(game.headers),source=url,archive_sha256=archive_hash,
            pgn_file=str(path.relative_to(OUT)),sha256=digest(path),local_only=True))
    old_protected=set(json.loads((RUN/'gm-values-01/preparation.json').read_text())['reserved_full_game_keys'])
    protected|=old_protected
    for row in curriculum['games']:
        if row['split']!='train':continue
        path=CURRICULUM/row['pgn_file'];assert digest(path)==row['sha256'];sources[str(path)]=digest(path)
        with path.open(encoding='utf-8') as stream:game=chess.pgn.read_game(stream)
        rows,_=positions(game,row['game_hash'],'train',(21,29,37,45,61,81))
        assert all(not r['white'] for r in rows);planned+=rows
    assert len(planned)<=120
    sources.update({str(p):digest(p) for p in (Path(__file__),ROOT/'docs/CONTINUATION_COLOUR_COVERAGE_PLAN_20260909.md')})
    save(OUT/'preparation.json',dict(rows=planned,reserved_games=reserved,protected_full_game_keys=sorted(protected),
        sources=sources,maximum_teacher_nodes=48000000,
        scope='Exposed earlier reservations remain development; three new unused Italian games reserved before labels.'))
    print(json.dumps(dict(planned=len(planned),new_reserved_games=3)),flush=True)


def label(partition):
    from training import game_feedback
    check_stop();path=OUT/(partition+'.json');assert not path.exists()
    prep=json.loads((OUT/'preparation.json').read_text())
    assert all(digest(Path(p))==h for p,h in prep['sources'].items())
    used=set(prep['protected_full_game_keys']) if partition=='train' else set()
    frozen=None
    if partition=='reserved_test':
        fit=json.loads((FIT/'state.json').read_text());gate=json.loads((FIT/'exposed-development.json').read_text())
        assert fit['status']=='weights_frozen_before_reserved_labels' and gate['passed']
        frozen=fit['model_sha256'];assert digest(FIT/'value.npz')==frozen
        used={r['key'] for r in json.loads((FIT/'preparation.json').read_text())['rows']}
        used|=set(json.loads((RUN/'gm-values-01/preparation.json').read_text())['reserved_full_game_keys'])
    wait_for_capacity(OUT/(partition+'-capacity.json'),minimum_memory_mb=1400,wait_seconds=0)
    game_feedback.stop_check=check_stop
    teacher=game_feedback.CachedTeacher(ROOT/'data/postgame-feedback/cache-v1',OUT)
    state=dict(status='running',rows=[],model_sha256=frozen,preparation_sha256=digest(OUT/'preparation.json'))
    try:
        for row in prep['rows']:
            if row['split']!=partition:continue
            check_stop();board=restore(row);item=dict(row,eligible=False)
            if row['key'] not in used and active(board):
                labels=[teacher.analyse(board,n) for n in (80000,320000)]
                cp=[r['cp'] for r in labels]
                finite=all(v is not None for v in cp) and all(r['mate'] is None for r in labels)
                eligible=finite and max(map(abs,cp))<=1500 and abs(cp[0]-cp[1])<=100
                item.update(teacher=labels,eligible=bool(eligible),target_stm_cp=sum(cp)/2 if eligible else None)
                used.add(row['key'])
            else:item['exclusion']='overlap/check/terminal/repetition/draw clock'
            state['rows'].append(item);save(path,state)
        state.update(status='complete',eligible=sum(r['eligible'] for r in state['rows']))
    except BaseException as error:
        state.update(status='failed',error=repr(error));raise
    finally:
        teacher.close();state['requested_teacher_nodes']=teacher.requested_nodes
        assert teacher.requested_nodes<=48000000
        if frozen:assert digest(FIT/'value.npz')==frozen
        save(path,state)
    print(json.dumps({k:v for k,v in state.items() if k!='rows'}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=['prepare','train','reserved_test'],required=True)
    mode=parser.parse_args().mode
    prepare() if mode=='prepare' else label(mode)
