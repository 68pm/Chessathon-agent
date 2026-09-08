"""Run student then teacher serially with headroom and owned process-tree limits."""
import json

from scripts.alien_rating_ladder import sha256
from scripts.improvement_quiet_check_gate import child
from scripts.overnight_capacity import wait_for_capacity
from training.fastchess_data import ROOT


def main():
    out = ROOT / 'runs/improvement-loop-20260907/cycle-22'
    prep = json.loads((out / 'preparation.json').read_text())
    for name, digest in prep['source_files'].items():
        assert sha256(ROOT / name) == digest
    wait_for_capacity(out / 'student-capacity.json')
    child(['-m', 'scripts.king_defence_trace', 'student', '--out', str(out)], out / 'student.log', 300)
    wait_for_capacity(out / 'teacher-capacity.json')
    child(['-m', 'scripts.king_defence_trace', 'teacher', '--out', str(out)], out / 'teacher.log', 180)
    for name, digest in prep['source_files'].items():
        assert sha256(ROOT / name) == digest


if __name__ == '__main__':
    main()
