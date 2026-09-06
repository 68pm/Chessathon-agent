from pathlib import Path

import numpy as np

from nn.layers import ClippedReLU, Dense


class Network:
    def __init__(self, inputs=775, hidden=(128, 32), seed=20260905, outputs=1):
        rng = np.random.default_rng(seed)
        self.layers = [
            Dense(inputs, hidden[0], rng),
            ClippedReLU(),
            Dense(hidden[0], hidden[1], rng),
            ClippedReLU(),
            Dense(hidden[1], outputs, rng),
        ]

    def forward(self, x):
        for layer in self.layers:
            x = layer.forward(x)
        return x

    def backward(self, gradient):
        for layer in reversed(self.layers):
            gradient = layer.backward(gradient)
        return gradient

    def parameters(self):
        return [p for layer in self.layers for p in layer.parameters()]

    def save(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        np.savez(path, **{f"p{i}": p.value for i, p in enumerate(self.parameters())})

    @classmethod
    def load(cls, path):
        with np.load(path, allow_pickle=False) as arrays:
            net = cls(
                arrays["p0"].shape[0],
                (arrays["p0"].shape[1], arrays["p2"].shape[1]),
                outputs=arrays["p4"].shape[1],
            )
            for i, p in enumerate(net.parameters()):
                p.value[:] = arrays[f"p{i}"]
        return net
