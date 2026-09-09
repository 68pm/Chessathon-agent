"""Sixteen-unit independent symmetry and gradient checks for the new architecture."""
import numpy as np
from training.daytime_antisymmetric import forward,opposite_features,loss_and_gradients

def test_sixteen_unit_perspective_identity():
    rng=np.random.default_rng(2026090917)
    x=(rng.random((7,768))<.04).astype(np.float64)
    p=[rng.normal(0,.025,(768,16)),np.full(16,.25),np.array([.3125]*8+[-.3125]*8)]
    assert np.allclose(forward(x,p)[0],-forward(opposite_features(x),p)[0],atol=1e-12)

def test_sixteen_unit_hidden_gradient_finite_difference():
    rng=np.random.default_rng(2026090917)
    x=rng.uniform(0,.1,(4,768));target=np.array([.3,-.5,1.2,-1.3])
    p=[rng.normal(0,.015,(768,16)),np.full(16,.25),np.array([.3125]*8+[-.3125]*8)]
    _,g=loss_and_gradients(x,target,p)
    for part,index in ((0,(2,15)),(0,(495,0)),(1,(9,))):
        old=p[part][index];eps=1e-5
        p[part][index]=old+eps;a=loss_and_gradients(x,target,p)[0]
        p[part][index]=old-eps;b=loss_and_gradients(x,target,p)[0]
        p[part][index]=old
        assert np.isclose(g[part][index],(a-b)/(2*eps),atol=1e-9,rtol=1e-5)
