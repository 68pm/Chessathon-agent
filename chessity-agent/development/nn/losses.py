import numpy as np


def mse(prediction, target):
    difference = prediction - target
    return float(np.mean(difference**2)), 2 * difference / difference.size


def huber(prediction, target, delta=0.25):
    difference = prediction - target
    absolute = np.abs(difference)
    loss = np.where(absolute <= delta, 0.5 * difference**2, delta * (absolute - 0.5 * delta))
    return float(loss.mean()), np.clip(difference, -delta, delta) / difference.size
