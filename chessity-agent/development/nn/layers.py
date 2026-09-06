import numpy as np

from nn.tensor import Parameter


class Dense:
    def __init__(self, inputs, outputs, rng):
        self.weight = Parameter(rng.normal(0, np.sqrt(2 / inputs), (inputs, outputs)))
        self.bias = Parameter(np.zeros(outputs))

    def forward(self, x):
        self.x = x
        return x @ self.weight.value + self.bias.value

    def backward(self, dy):
        self.weight.grad += self.x.T @ dy
        self.bias.grad += dy.sum(axis=0)
        return dy @ self.weight.value.T

    def parameters(self):
        return [self.weight, self.bias]


class ClippedReLU:
    def forward(self, x):
        self.mask = (x > 0) & (x < 1)
        return np.clip(x, 0, 1)

    def backward(self, dy):
        return dy * self.mask

    def parameters(self):
        return []
