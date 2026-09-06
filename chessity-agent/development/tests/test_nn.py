import chess
import numpy as np

from engine.features import encode
from engine.neural import NeuralValue
from nn.layers import ClippedReLU, Dense
from nn.losses import huber, mse
from nn.model import Network
from nn.optim import Adam


def test_dense_gradient():
    rng = np.random.default_rng(4)
    layer = Dense(3, 2, rng)
    x, target = rng.random((5, 3), dtype=np.float32), rng.random((5, 2), dtype=np.float32)
    _, gradient = mse(layer.forward(x), target)
    layer.backward(gradient)
    for param in layer.parameters():
        for index in np.ndindex(param.value.shape):
            original = param.value[index].copy()
            param.value[index] = original + 0.001
            positive = mse(layer.forward(x), target)[0]
            param.value[index] = original - 0.001
            negative = mse(layer.forward(x), target)[0]
            param.value[index] = original
            assert abs((positive - negative) / 0.002 - param.grad[index]) < 0.0003


def test_activation_and_huber():
    layer = ClippedReLU()
    x = np.array([-0.5, 0.3, 1.5])
    np.testing.assert_allclose(layer.forward(x), [0, 0.3, 1])
    np.testing.assert_allclose(layer.backward(np.ones(3)), [0, 1, 0])
    target = np.zeros(3)
    _, grad = huber(x, target)
    for i in range(3):
        plus, minus = x.copy(), x.copy()
        plus[i] += 0.0001
        minus[i] -= 0.0001
        numeric = (huber(plus, target)[0] - huber(minus, target)[0]) / 0.0002
        assert abs(numeric - grad[i]) < 1e-5


def test_training_decreases_loss():
    rng = np.random.default_rng(2)
    x = rng.random((64, 3), dtype=np.float32)
    y = x[:, :1] * 0.4 - x[:, 1:2] * 0.2
    net, opt = Network(3, (12, 6), seed=3), None
    opt = Adam(net.parameters(), lr=0.01)
    before = mse(net.forward(x), y)[0]
    for _ in range(150):
        opt.zero_grad()
        _loss, gradient = mse(net.forward(x), y)
        net.backward(gradient)
        opt.step()
    assert mse(net.forward(x), y)[0] < before * 0.15


def test_export_and_feature_parity(tmp_path):
    net = Network()
    path = tmp_path / "net.npz"
    net.save(path)
    runtime = NeuralValue(path)
    b = chess.Board()
    for uci in ["e2e4", "c7c5", "g1f3", "b8c6"]:
        b.push_uci(uci)
        x = encode(b)
        np.testing.assert_array_equal(x, encode(b.mirror()))
        assert abs(float(net.forward(x[None])[0, 0]) - runtime.predict_features(x)) < 1e-6
