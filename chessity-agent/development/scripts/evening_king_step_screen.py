"""Strict practical comparison after both speed and teacher-quality gates."""
import argparse
import json
from pathlib import Path
from scripts import evening_screen as screen
from scripts.evening_common import ROOT,RUN,digest,save

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--prepare',action='store_true')
    args=parser.parse_args()
    screen.SOURCE=RUN/'king-step-buffers-01'
    screen.OUT=RUN/'king-step-buffers-screen-01'
    screen.CYCLE_PREFIX='e9-king-step-buffers-01-'
    quality=RUN/'king-step-buffers-quality-01'
    if args.prepare:
        state=json.loads((quality/'state.json').read_text())
        assert state['status']=='complete' and state['passed'] and state['frozen_candidates']
        screen.prepare()
        path=screen.OUT/'preparation.json';prep=json.loads(path.read_text())
        for p in (Path(__file__),quality/'preparation.json',quality/'state.json'):
            prep['source_sha256'][str(p.relative_to(ROOT))]=digest(p)
        save(path,prep)
    else:screen.run()
