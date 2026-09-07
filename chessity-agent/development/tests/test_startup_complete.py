"""Reproduce a delayed setup silently skipping root compilation before ready."""
import importlib
import sys
import types
from pathlib import Path

import chess
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_driver(folder, name):
    package = types.ModuleType(name)
    package.__path__ = [str(ROOT / 'candidates' / folder / 'engine')]
    sys.modules[name] = package
    return importlib.import_module(name+'.compiled_driver')


def simulate(driver, monkeypatch, setup_seconds):
    clock, calls = [0.0],[]
    def legal(*args):
        clock[0] += setup_seconds
        return np.array([6 | (37 << 7)],dtype=np.int64)
    def root(*args):
        calls.append(dict(depth=args[2],node_limit=int(args[13][2]),deadline=args[14]))
        return args[3],0,True
    with monkeypatch.context() as patch:
        patch.setattr(driver,'time',types.SimpleNamespace(perf_counter=lambda:clock[0]))
        patch.setattr(driver.core,'legal_moves',legal)
        patch.setattr(driver.core,'position_hash',lambda *args:np.uint64(1))
        patch.setattr(driver.core,'classical',lambda *args:0)
        patch.setattr(driver.core,'root_iteration',root)
        search = driver.CompiledSearch()
        search.warmup()
        result = search.last_result
    return calls,result


@pytest.mark.parametrize('delay',[0.0,70.0])
def test_startup_reaches_root_even_when_setup_exceeds_the_old_soft_deadline(monkeypatch,delay):
    old = load_driver('compiled-qsearch-endgames-v1','startup_reference_'+str(int(delay)))
    fixed = load_driver('compiled-startup-complete-v1','startup_fixed_'+str(int(delay)))
    old_calls,old_result = simulate(old,monkeypatch,delay)
    fixed_calls,fixed_result = simulate(fixed,monkeypatch,delay)
    assert len(old_calls) == (1 if delay < 60 else 0)
    assert old_result.depth == (1 if delay < 60 else 0)
    assert len(fixed_calls) == 1 and fixed_result.depth == 1
    assert fixed_calls[0]['depth'] == 1 and fixed_calls[0]['node_limit'] == 4096
    assert fixed_result.move in chess.Board().legal_moves


def test_only_the_startup_method_changes():
    import ast
    base = ROOT / 'candidates/compiled-qsearch-endgames-v1/engine/compiled_driver.py'
    fixed = ROOT / 'candidates/compiled-startup-complete-v1/engine/compiled_driver.py'
    def runtime_ast(path):
        tree = ast.parse(path.read_text())
        for item in tree.body:
            if isinstance(item,ast.ClassDef) and item.name == 'CompiledSearch':
                item.body = [node for node in item.body if not isinstance(node,ast.FunctionDef) or node.name != 'warmup']
        return ast.dump(tree)
    assert runtime_ast(base) == runtime_ast(fixed)
