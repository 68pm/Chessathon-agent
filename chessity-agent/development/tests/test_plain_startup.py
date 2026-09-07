"""The supported diagnostic flag must bypass Colorama initialization, not errors."""
import ast
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FLAG = 'NUMBA_DISABLE_ERROR_MESSAGE_HIGHLIGHTING'


def test_plain_setting_precedes_compiler_import_and_is_the_only_new_statement():
    old = ast.parse((ROOT / 'candidates/compiled-startup-complete-v1/agent.py').read_text())
    new = ast.parse((ROOT / 'candidates/compiled-startup-plain-v1/agent.py').read_text())
    expected = ast.parse(f"os.environ[{FLAG!r}] = '1'").body[0]
    matches = [i for i,node in enumerate(new.body) if ast.dump(node) == ast.dump(expected)]
    assert len(matches) == 1
    compiler = next(i for i,node in enumerate(new.body)
        if isinstance(node,ast.ImportFrom) and node.module == 'engine.compiled_driver')
    assert matches[0] < compiler
    new.body.pop(matches[0])
    assert ast.dump(old) == ast.dump(new)


def test_numba_plain_diagnostics_do_not_initialize_console_conversion():
    code = '''import colorama
def forbidden(*args, **kwargs):
    raise AssertionError('Console conversion must not initialize')
colorama.init = forbidden
from numba.core.errors import termcolor
value = termcolor()
assert value.errmsg('compiler failure remains visible') == 'compiler failure remains visible'
assert type(value).__name__ == 'NOPColorScheme'
print('plain diagnostics verified')
'''
    environment = dict(os.environ)
    environment[FLAG] = '1'
    result = subprocess.run([sys.executable,'-c',code],env=environment,
        capture_output=True,text=True,timeout=30,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == 'plain diagnostics verified'
