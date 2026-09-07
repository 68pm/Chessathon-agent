"""Extract and test a package in a fresh process; audit runtime side effects."""

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

PROBE = r"""
import sys, os, time, json, random
sys.dont_write_bytecode = True
def audit(event, args):
    if event == 'open':
        mode = args[1]
        flags = args[2]
        if (isinstance(mode, str) and any(x in mode for x in 'wax+')) or (isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC)):
            raise RuntimeError('Runtime file write: ' + str(args[0]))
    if event in ('os.remove', 'os.rename', 'os.rmdir', 'os.mkdir', 'os.chmod', 'os.chown', 'os.utime', 'os.link', 'os.symlink', 'os.truncate'):
        raise RuntimeError('Runtime filesystem mutation: ' + event)
    if event.startswith('socket.') or event in ('subprocess.Popen', 'os.system'):
        raise RuntimeError('Forbidden runtime action: ' + event)
sys.addaudithook(audit)
read_only_checks = {}
for label, attempt in [
    ('create_file', lambda: open('read-only-probe.txt', 'w')),
    ('delete_file', lambda: os.remove('runtime.json')),
    ('create_directory', lambda: os.mkdir('read-only-probe')),
    ('rename_file', lambda: os.rename('runtime.json', 'read-only-probe.json')),
]:
    try:
        attempt()
    except RuntimeError as error:
        assert str(error).startswith('Runtime file')
        read_only_checks[label] = 'blocked'
    else:
        raise AssertionError('Read-only check unexpectedly allowed: ' + label)
start = time.perf_counter()
import agent, chess
init_ms = (time.perf_counter() - start) * 1000
alien_verified = False
selective_alien_verified = False
selective_alien_choice = None
if getattr(agent, '_config', {}).get('opening_style') == 'alien':
    alien = chess.Board()
    for san in ['e4', 'c6', 'd4', 'd5', 'Nd2', 'dxe4', 'Nxe4', 'Nf6', 'Ng5', 'h6']:
        alien.push_san(san)
    assert agent.get_move(alien.fen(), 1000) == 'g5f7'
    alien_verified = True
if getattr(agent, '_config', {}).get('opening_style') == 'alien-selective':
    alien = chess.Board()
    for san in ['e4', 'c6', 'd4', 'd5', 'Nd2', 'dxe4', 'Nxe4', 'Nf6', 'Ng5', 'h6']:
        alien.push_san(san)
    assert agent._opening(alien).uci() == 'g5f7'
    original_run = agent._search.run
    hints = []
    def tracked_run(*args, **kwargs):
        hints.append(kwargs.get('preferred_move'))
        return original_run(*args, **kwargs)
    agent._search.run = tracked_run
    selective_alien_choice = agent.get_move(alien.fen(), 1000)
    agent._search.run = original_run
    assert hints == [chess.Move.from_uci('g5f7')]
    assert chess.Move.from_uci(selective_alien_choice) in alien.legal_moves
    selective_alien_verified = True
b = chess.Board()
elementary_endgames_verified = False
extended_endgames_verified = False
if getattr(agent, '_config', {}).get('elementary_tables'):
    for fen in ['7k/8/5KQ1/8/8/8/8/8 w - - 0 1', '8/4P3/4K3/8/8/8/8/k7 w - - 0 1']:
        elementary = chess.Board(fen)
        answer = chess.Move.from_uci(agent.get_move(fen, 1000))
        assert answer in elementary.legal_moves
    elementary_endgames_verified = True
    if agent._config.get('table_max_pieces', 3) >= 5:
        check_evasion = chess.Board('5R2/7K/2r5/5k2/3b4/8/8/8 b - - 41 65')
        assert agent.get_move(check_evasion.fen(), 1000) == 'd4f6'
        assert agent.get_move(check_evasion.mirror().fen(), 1000) == 'd5f3'
        extended_endgames_verified = True
randomizer = random.Random(20)
times=[]
clock_ms, calls = int(sys.argv[1]), int(sys.argv[2])
policy_calls = 0
if getattr(agent, '_policy', None) is not None:
    original_bonuses = agent._policy.bonuses
    def tracked_bonuses(*args):
        global policy_calls
        policy_calls += 1
        return original_bonuses(*args)
    agent._policy.bonuses = tracked_bonuses
for i in range(calls):
    if b.is_game_over(): b.reset()
    start = time.perf_counter()
    move = chess.Move.from_uci(agent.get_move(b.fen(), clock_ms))
    times.append((time.perf_counter() - start) * 1000)
    assert move in b.legal_moves
    b.push(randomizer.choice(list(b.legal_moves)))
memory = None
if sys.platform == 'win32':
    import ctypes, ctypes.wintypes
    class Counters(ctypes.Structure):
        _fields_ = [('cb', ctypes.wintypes.DWORD), ('PageFaultCount', ctypes.wintypes.DWORD)] + [(name, ctypes.c_size_t) for name in ['PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage']]
    counters= Counters()
    counters.cb=ctypes.sizeof(counters)
    kernel=ctypes.WinDLL('kernel32')
    kernel.GetCurrentProcess.restype=ctypes.wintypes.HANDLE
    psapi=ctypes.WinDLL('psapi')
    psapi.GetProcessMemoryInfo.argtypes=[ctypes.wintypes.HANDLE, ctypes.POINTER(Counters), ctypes.wintypes.DWORD]
    if psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(),ctypes.byref(counters),counters.cb):
        memory=counters.PeakWorkingSetSize
print(json.dumps({'init_ms':init_ms,'legal_calls':calls,'clock_ms':clock_ms,'policy_calls':policy_calls,'alien_verified':alien_verified,'selective_alien_verified':selective_alien_verified,'selective_alien_choice':selective_alien_choice,'elementary_endgames_verified':elementary_endgames_verified,'extended_endgames_verified':extended_endgames_verified,'max_move_ms':max(times),'peak_working_set_bytes':memory,'read_only_checks':read_only_checks,'audit':'no filesystem mutations, network or subprocess'}))
"""


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--zip", type=Path, default=Path("submission.zip"))
    p.add_argument("--out", type=Path, default=Path("runs/package-validation.json"))
    p.add_argument("--clock-ms", type=int, default=80)
    p.add_argument("--calls", type=int, default=100)
    a = p.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(a.zip) as archive:
            assert "agent.py" in archive.namelist()
            assert sum(i.file_size for i in archive.infolist()) < 50_000_000
            for name in archive.namelist():
                assert not Path(name).is_absolute() and ".." not in Path(name).parts
            archive.extractall(tmp)
        result = subprocess.run(
            [sys.executable, "-B", "-c", PROBE, str(a.clock_ms), str(a.calls)],
            cwd=tmp,
            text=True,
            capture_output=True,
            timeout=90,
            check=False,
        )
        if result.returncode:
            raise RuntimeError(f"Package probe exited {result.returncode}: {result.stderr[-6000:]}")
    report = json.loads(result.stdout)
    report["sha256"] = hashlib.sha256(a.zip.read_bytes()).hexdigest()
    assert report["init_ms"] < 90_000
    if report["peak_working_set_bytes"] is not None:
        assert report["peak_working_set_bytes"] < 2_000_000_000
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, indent=2))
    print(json.dumps(report))


if __name__ == "__main__":
    main()
