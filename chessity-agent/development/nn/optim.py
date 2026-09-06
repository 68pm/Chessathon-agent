import numpy as np


class Adam:
    def __init__(self, parameters, lr=0.001, weight_decay=0.00001):
        self.parameters = list(parameters)
        self.lr, self.weight_decay = lr, weight_decay
        self.t = 0
        self.m = [np.zeros_like(p.value) for p in self.parameters]
        self.v = [np.zeros_like(p.value) for p in self.parameters]

    def zero_grad(self):
        for p in self.parameters:
            p.zero_grad()

    def step(self):
        self.t += 1
        for p, m, v in zip(self.parameters, self.m, self.v):
            grad = p.grad + self.weight_decay * p.value
            m *= 0.9
            m += 0.1 * grad
            v *= 0.999
            v += 0.001 * grad * grad
            p.value -= self.lr * (m / (1 - 0.9**self.t)) / (np.sqrt(v / (1 - 0.999**self.t)) + 1e-8)
