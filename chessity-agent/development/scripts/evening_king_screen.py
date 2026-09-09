"""Apply unchanged strict evening practical gates to a qualified king correction."""
import argparse
from pathlib import Path
from scripts import evening_screen as screen
from scripts.evening_common import ROOT,RUN,digest,save

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare',action='store_true')
    args=parser.parse_args()
    screen.SOURCE=RUN/'king-pressure-01'
    screen.OUT=RUN/'king-pressure-screen-01'
    screen.CYCLE_PREFIX='e9-king-pressure-01-'
    if args.prepare:
        screen.prepare()
        import json
        path=screen.OUT/'preparation.json'
        prep=json.loads(path.read_text())
        prep['source_sha256'][str(Path(__file__).relative_to(ROOT))]=digest(Path(__file__))
        save(path,prep)
    else:screen.run()
