import numpy as np
import pytest

from layer2.calibration import fit_scale, win_prob


def test_win_prob_shape():
    p = win_prob([-50, -5, 0, 5, 50], s=20)

    assert p[2] == 0.5
    assert np.all(np.diff(p) > 0)
    assert np.all((p > 0) & (p < 1))


def test_fit_scale_recovers_a_known_scale():
    rng = np.random.default_rng(1)
    margins = rng.normal(0, 30, 20000)
    results = (rng.random(20000) < win_prob(margins, 25.0)).astype(float)

    assert fit_scale(margins, results) == pytest.approx(25.0, rel=0.05)
