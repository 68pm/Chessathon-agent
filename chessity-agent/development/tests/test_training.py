import subprocess
import sys

import numpy as np

from nn.model import Network
from training.dataset import split_group


def test_resume_matches_uninterrupted(tmp_path):
    rng = np.random.default_rng(7)
    x = rng.random((100, 775), dtype=np.float32)
    y = x[:, :1] * 0.3
    source = tmp_path / "data.npz"
    np.savez(source, x=x, y=y, split=np.array([0] * 80 + [1] * 20))
    full, resumed = tmp_path / "full", tmp_path / "resumed"
    command = [
        sys.executable,
        "-m",
        "training.train",
        "--data",
        str(source),
        "--hidden",
        "8",
        "--batch-size",
        "16",
    ]
    for destination, epochs, extra in [(full, 4, []), (resumed, 2, []), (resumed, 4, ["--resume"])]:
        subprocess.run(
            command + ["--out", str(destination), "--epochs", str(epochs)] + extra,
            check=True,
            capture_output=True,
            timeout=30,
        )
    with np.load(full / "last.npz") as a, np.load(resumed / "last.npz") as b:
        for key in a.files:
            np.testing.assert_array_equal(a[key], b[key])


def test_group_split_stable():
    assert split_group("B20", 42) == split_group("B20", 42)
    assert len({split_group(f"group{i}", 42) for i in range(100)}) == 3


def test_aux_export_has_only_value_head(tmp_path):
    model = Network(outputs=2)
    source, exported = tmp_path / "model.npz", tmp_path / "export.npz"
    model.save(source)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "training.export",
            "--checkpoint",
            str(source),
            "--out",
            str(exported),
        ],
        check=True,
        capture_output=True,
        timeout=15,
    )
    result = Network.load(exported)
    x = np.ones((1, 775), dtype=np.float32) * 0.1
    np.testing.assert_allclose(model.forward(x)[:, :1], result.forward(x), atol=1e-6)
