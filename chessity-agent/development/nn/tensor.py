import numpy as np


class Parameter:
    def __init__(self, value):
        self.value = np.asarray(value, dtype=np.float32)
        self.grad = np.zeros_like(self.value)

    def zero_grad(self):
        self.grad.fill(0)
