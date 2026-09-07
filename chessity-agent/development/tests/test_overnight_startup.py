"""Failed startups must become preserved game records, not lost futures."""
import json

import pytest

from harness.sandbox import AgentFailure
from scripts import overnight_game as game
from scripts.record_fastchess import audit_game


@pytest.mark.parametrize('candidate_white', [True,False])
def test_agent_and_opponent_startup_failures_are_recorded(tmp_path, monkeypatch, candidate_white):
    class BrokenAgent:
        stderr_tail = 'startup diagnostic'
        def start(self, budget):
            assert budget == 90
            raise AgentFailure('init')
        def stop(self):
            pass
    def broken_opponent(*args, **kwargs):
        assert kwargs['timeout'] == 90
        raise TimeoutError('UCI handshake failed')
    monkeypatch.setattr(game,'local',lambda folder:BrokenAgent())
    monkeypatch.setattr(game,'memory',lambda:dict(available_mb=1024))
    monkeypatch.setattr(game.chess.engine.SimpleEngine,'popen_uci',broken_opponent)
    config = dict(base_ms=120000,increment_ms=500,ply_cap=600,workers=1)
    job = dict(id=1,candidate_path='candidates/compiled-qsearch-endgames-v1',
        family='stockfish:2800',elo=2800,pair=0,opening=[],candidate_white=candidate_white)
    result = game.run_game(job,config,tmp_path)
    assert result['termination'] == 'init' and result['moves'] == []
    assert result['failed_colour'] == 'white'
    assert result['score'] == (0.0 if candidate_white else 1.0)
    assert result['failure_detail']['component'] == ('agent_start' if candidate_white else 'opponent_start')
    assert json.loads((tmp_path / 'game-001.json').read_text()) == result
    audit_game(result,config)
