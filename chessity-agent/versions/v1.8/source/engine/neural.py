"""Inference-only arrays. Sparse first layer, single-position CPU inference."""

import numpy as np

from engine.features import encode


class NeuralValue:
    def __init__(self, path):
        with np.load(path, allow_pickle=False) as data:
            self.p = [np.array(data[f"p{i}"], dtype=np.float32) for i in range(6)]
        w1, b1, w2, b2, w3, b3 = self.p
        if (
            w1.shape[0] != 775
            or b1.shape != (w1.shape[1],)
            or w2.shape != (w1.shape[1], len(b2))
            or w3.shape != (len(b2), 1)
            or b3.shape != (1,)
        ):
            raise ValueError("Invalid model topology")
        if not all(np.isfinite(p).all() for p in self.p):
            raise ValueError("Non-finite model")

    def predict_features(self, x):
        w1, b1, w2, b2, w3, b3 = self.p
        active = np.flatnonzero(x)
        h1 = np.clip((w1[active] * x[active, None]).sum(axis=0) + b1, 0, 1)
        h2 = np.clip(h1 @ w2 + b2, 0, 1)
        return float((h2 @ w3 + b3)[0])

    def centipawns(self, board):
        value = self.predict_features(encode(board))
        return round(float(600 * np.arctanh(np.clip(value, -0.995, 0.995))))
