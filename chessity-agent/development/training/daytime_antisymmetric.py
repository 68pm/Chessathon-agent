"""A positional residual from both piece perspectives; no synthetic labels."""
import numpy as np

PERMUTATION = np.concatenate((np.arange(384,768),np.arange(384))).reshape(12,8,8)[:,::-1,:].reshape(768)


def opposite_features(x):
    assert x.shape[-1] == 768
    return x[...,PERMUTATION]


def forward(x, parameters):
    weights, bias, output = parameters
    pre = x @ weights + bias
    reverse_pre = opposite_features(x) @ weights + bias
    hidden, reverse_hidden = np.clip(pre,0.,1.), np.clip(reverse_pre,0.,1.)
    return .5*(hidden-reverse_hidden) @ output, (pre,reverse_pre), (hidden,reverse_hidden)


def loss_and_gradients(x, target, parameters):
    prediction, (pre,reverse_pre), (hidden,reverse_hidden) = forward(x,parameters)
    error = prediction-target
    loss = np.mean(np.where(abs(error)<=1., .5*error**2, abs(error)-.5))
    derivative = np.clip(error,-1.,1.)/len(x)
    own = .5*derivative[:,None]*parameters[2][None,:]*((pre>0)&(pre<1))
    other = -.5*derivative[:,None]*parameters[2][None,:]*((reverse_pre>0)&(reverse_pre<1))
    return float(loss), [x.T @ own + opposite_features(x).T @ other,
        (own+other).sum(axis=0), .5*(hidden-reverse_hidden).T @ derivative]


def gradients(x, target, parameters):
    return loss_and_gradients(x,target,parameters)[1]
