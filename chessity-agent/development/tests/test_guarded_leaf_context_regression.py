"""A fullmove-dependent evaluator must not reuse an opening-only cached score."""

import numpy as np
import pytest

from experiments import overnight_guarded_leaf_core as core


def check_context(module, monkeypatch, includes_fullmove):
    board = np.zeros(142, dtype=np.int64)
    board[4], board[116] = 6, -6
    state = np.asarray([1, 0, -1, 0, 4, 116, 10], dtype=np.int64)
    key, context = 1234, 123
    mask = (1 << 64) - 1
    cached_context = (context ^ ((2 * 11400714819323198485) & mask)
                      ^ ((10 * 15485907386658061715) & mask))
    if includes_fullmove:
        cached_context ^= (10 * 0xd6e8feb86659fd93) & mask
    ttkey = np.zeros(16, dtype=np.uint64)
    ttcontext = np.zeros(16, dtype=np.uint64)
    ttdata = np.zeros((16, 5), dtype=np.int64)
    ttkey[key & 15], ttcontext[key & 15] = key, cached_context
    ttdata[key & 15] = [5, 12345, 0, 0, 0]
    monkeypatch.setattr(module, 'attacked', lambda *args: False)
    monkeypatch.setattr(module, 'insufficient', lambda *args: False)

    def miss(*args):
        raise LookupError('Fresh search required')

    monkeypatch.setattr(module, 'generate', miss)
    args = dict(board=board, state=state, depth=1, alpha=-100, beta=100, ply=1, qdepth=0,
        hashes=np.asarray([key], dtype=np.uint64), hlen=1, context=np.uint64(context),
        ttkey=ttkey, ttcontext=ttcontext, ttdata=ttdata, killers=np.zeros((100, 2), dtype=np.int64),
        history=np.zeros((2, 128, 128), dtype=np.int64), control=np.asarray([0, 0, 100]), deadline=0,
        weights=np.zeros((768, 64)), bias=np.zeros(64), output=np.zeros(64),
        rule_weights=np.zeros((13, 64)), blend=.5, conversion=False, reductions=False,
        accumulator=np.zeros((2, 64)), extensions_left=2, quiet_checks_left=4, quiet_attacker=0)
    with np.errstate(over='ignore'):
        assert module.search.py_func(**args) == 12345
        state[6] = 20
        args['control'][0] = 0
        with pytest.raises(LookupError, match='Fresh search required'):
            module.search.py_func(**args)


def test_original_guarded_draft_must_separate_fullmove_context(monkeypatch):
    check_context(core, monkeypatch, includes_fullmove=False)
