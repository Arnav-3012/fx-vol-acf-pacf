"""P2 tests: simulator, rules, selector.

Small n, seeds from config. No exact-order asserts (that is the P3 experiment).
"""
import numpy as np
import pytest

from src.data import load_config
from src.rules import mean_order_rule, variance_order_rule
from src.selector import select_and_fit
from src.simulate import sim_arch1, sim_garch11

CFG = load_config()
SIM = CFG["sim"]
T = SIM["test"]   # test-only settings (n, number of noise seeds, parameters)
G = T["garch11"]  # true GARCH(1,1) parameters used for simulation

# Keys every selector result must contain.
KEYS = {"mean_spec", "mean_resid_lb_p", "order", "dist", "params", "persistence", "bic", "gate",
        "escalation_log", "models_fitted", "flagged", "reason"}


def _noise_seeds():
    """Consecutive seeds starting from the config seed."""
    return range(SIM["seed"], SIM["seed"] + T["n_seeds"])


def _garch11_sample():
    """One simulated GARCH(1,1) series with the config seed."""
    return sim_garch11(T["n"], G["omega"], G["alpha"], G["beta"], SIM["seed"], SIM["burn"])


# ---------------------------------------------------------------- simulator

def test_sim_garch11_length_finite_and_deterministic():
    e = _garch11_sample()

    assert e.shape == (T["n"],)       # right length after burn-in
    assert np.isfinite(e).all()       # no NaN / inf from the recursion

    np.testing.assert_array_equal(e, _garch11_sample())  # same seed -> same series


def test_sim_raises_when_not_stationary():
    # alpha + beta = 1 and alpha = 1 (ARCH) both violate alpha + beta < 1.
    with pytest.raises(ValueError):
        sim_garch11(100, G["omega"], 0.5, 0.5, SIM["seed"])

    with pytest.raises(ValueError):
        sim_arch1(100, G["omega"], 1.0, SIM["seed"])


# -------------------------------------------------------------------- rules

def test_mean_rule_constant_on_white_noise():
    # A 5% band spikes by chance, so one seed could fail legitimately.
    # We require the rule to say "constant" for at least min_share of many seeds.
    hits = []
    for seed in _noise_seeds():
        noise = np.random.default_rng(seed).standard_normal(T["n_noise"])
        hits.append(mean_order_rule(noise, CFG)["m"] == 0)

    assert np.mean(hits) >= T["min_share"]


def test_check1_stops_on_iid_noise():
    # Same multi-seed logic: iid noise has no ARCH effect, so Check 1 should stop.
    stops = []
    for seed in _noise_seeds():
        noise = np.random.default_rng(seed).standard_normal(T["n"])
        stops.append(variance_order_rule(noise, CFG)["stop_constant_variance"])

    assert np.mean(stops) >= T["min_share"]


def test_check1_does_not_stop_on_garch11():
    out = variance_order_rule(_garch11_sample(), CFG)

    assert out["stop_constant_variance"] is False

    p, q = out["start_order"]
    assert p >= 1 and q >= 0  # some ARCH structure was proposed (exact order is P3)


# ----------------------------------------------------------------- selector

def _check_result(r):
    """Shared structural checks for a selector result."""
    assert KEYS <= set(r)
    assert r["models_fitted"] >= 1
    assert r["models_fitted"] == len(r["escalation_log"])  # every fit is logged
    assert r["persistence"] < 1                             # NaN would fail here too
    assert isinstance(r["flagged"], bool)
    assert isinstance(r["gate"]["passed"], bool)
    assert len(r["order"]) == 2
    assert r["dist"] in ("normal", "t")


def test_select_and_fit_garch11():
    _check_result(select_and_fit(_garch11_sample(), CFG))


def test_select_and_fit_arch1():
    A = T["arch1"]
    e = sim_arch1(T["n"], A["omega"], A["alpha"], SIM["seed"], SIM["burn"])

    _check_result(select_and_fit(e, CFG))
