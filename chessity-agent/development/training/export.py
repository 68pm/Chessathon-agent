import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from nn.model import Network


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--checkpoint", type=Path, default=Path("runs/value-128/best.npz"))
    p.add_argument("--out", type=Path, default=Path("models/value.npz"))
    a = p.parse_args()
    net = Network.load(a.checkpoint)
    arrays = [p.value for p in net.parameters()]
    arrays[4], arrays[5] = arrays[4][:, :1], arrays[5][:1]
    a.out.parent.mkdir(parents=True, exist_ok=True)
    np.savez(a.out, **{f"p{i}": value for i, value in enumerate(arrays)})
    metadata = {
        "source_checkpoint": str(a.checkpoint),
        "checkpoint_sha256": hashlib.sha256(a.checkpoint.read_bytes()).hexdigest(),
        "weights_sha256": hashlib.sha256(a.out.read_bytes()).hexdigest(),
        "parameters": sum(v.size for v in arrays),
        "bytes": a.out.stat().st_size,
        "format": "NPZ float32 p0..p5; no pickle",
    }
    a.out.with_suffix(".json").write_text(json.dumps(metadata, indent=2))
    print(json.dumps(metadata))


if __name__ == "__main__":
    main()
