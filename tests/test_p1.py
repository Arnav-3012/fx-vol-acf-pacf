"""P1 tests: deterministic, no network."""
import numpy as np
import pandas as pd
import pytest

from src.correlogram import acf_pacf_band, significant_lags
from src.data import to_log_returns
from src.stat_tests import ljung_box


def test_log_returns_values_and_sum():
    prices = pd.Series([1.0, 1.1, 1.05, 1.2])
    r = to_log_returns(prices)
    expected = 100 * np.log(np.array([1.1 / 1.0, 1.05 / 1.1, 1.2 / 1.05]))
    np.testing.assert_allclose(r.to_numpy(), expected)
    assert r.sum() == pytest.approx(100 * np.log(1.2 / 1.0))


def test_log_returns_nonpositive_raises():
    with pytest.raises(ValueError):
        to_log_returns(pd.Series([1.0, 0.0, 1.1]))


def test_band_matches_normal_quantile():
    x = np.sin(0.1 * np.arange(4000))
    out = acf_pacf_band(x, nlags=5, confidence=0.95)
    assert out["n"] == 4000
    assert out["band"] == pytest.approx(1.96 / np.sqrt(4000), abs=1e-3)
    assert len(out["acf"]) == 5 and len(out["pacf"]) == 5


def test_significant_lags_exact():
    values = np.array([0.5, -0.3, 0.05, -0.2, 0.1])
    assert significant_lags(values, band=0.15) == [1, 2, 4]


def test_ljung_box_shape_and_columns():
    x = np.sin(np.arange(60) * 0.7) + 0.1 * np.cos(np.arange(60) * 2.3)
    out = ljung_box(x, lags=[2, 5, 10])
    assert list(out.columns) == ["lag", "lb_stat", "lb_pvalue"]
    assert out["lag"].tolist() == [2, 5, 10]
