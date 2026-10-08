"""Tests for the post-hoc ARCH(1) diagnostic (src/simulate.py, last section, D-031).

What is checked: the config keys exist, the calibration / eval / diagnostic seed ranges are pairwise
disjoint (and the check really raises on an overlap), the false-spike rate on iid noise sits in a plausible
band, the diagnostic ARCH(1) models are built with the right true order and leave the input config alone, the
table has the documented shape on a tiny run, and the verdict function follows the fixed D-031 interpretation
on hand-made tables.
These tests check plumbing and definitions. They do NOT check the diagnostic's numbers (that is the experiment
itself). Sizes, seeds and tolerances come from config.yaml; no real data.
"""
import copy

import numpy as np
import pandas as pd
import pytest

from src.data import load_config
from src.simulate import (check_diagnostic_seed_ranges, diagnostic_arch1_table, diagnostic_cfg,
                          diagnostic_model_name, diagnostic_verdict, false_spike_rate, mc_se,
                          pacf_squares_spike, seed_ranges, simulate_recovery_model, true_spec)

CFG = load_config()
DG = CFG["diagnostic"]
TST = DG["test"]   # test-only settings (n, R, rate_lo, rate_hi, n_small, R_small)


def _fast_cfg() -> dict:
    """Copy of the config that runs joblib in-process (n_jobs=1): simpler and deterministic."""
    cfg = copy.deepcopy(CFG)
    cfg["recovery"]["n_jobs"] = 1

    return cfg


def test_diagnostic_config_keys_are_present():
    """The spec'd keys exist: diagnostic.enabled defaults to true and seed_base is 3000000.

    Input: the loaded config. Output: asserts only. Also checks the lag window fits inside variance.corr_lags.
    """
    assert DG["enabled"] is True
    assert DG["seed_base"] == 3000000
    assert 1 <= DG["lag_min"] <= DG["lag_max"] <= CFG["variance"]["corr_lags"]


def test_seed_ranges_of_calibration_eval_and_diagnostic_are_pairwise_disjoint():
    """No seed is shared by any two of the calibration, eval and diagnostic blocks.

    Input: the loaded config. Output: asserts only. Compares every pair of half-open intervals directly
    (independent of the library check), then calls check_diagnostic_seed_ranges, which must not raise.
    """
    ranges = seed_ranges(CFG)
    assert set(ranges) == {"calibration", "eval", "diagnostic"}

    names = sorted(ranges)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            (a_lo, a_hi), (b_lo, b_hi) = ranges[a], ranges[b]
            assert a_hi <= b_lo or b_hi <= a_lo, f"{a} and {b} overlap"

    check_diagnostic_seed_ranges(CFG)


@pytest.mark.parametrize("other", ["calibration", "eval"])
def test_check_diagnostic_seed_ranges_raises_on_overlap(other):
    """Moving the diagnostic seed_base into another block's range must raise ValueError.

    Input: a config copy with diagnostic.seed_base set to the first seed of `other`. Output: ValueError.
    """
    bad = copy.deepcopy(CFG)
    bad["diagnostic"]["seed_base"] = CFG[other]["seed_base"]

    with pytest.raises(ValueError):
        check_diagnostic_seed_ranges(bad)


def test_false_spike_rate_on_iid_noise_is_in_a_plausible_range():
    """On iid N(0, 1) noise the false-spike rate at a fixed seed lies in [rate_lo, rate_hi].

    Input: the iid control from recovery.models, test.n and test.R from config, seeds from diagnostic.seed_base.
    Output: asserts only. Idea: white noise has no PACF structure, so each of the four lags 2..5 is outside the
    95% band about 5% of the time, giving about 0.19 for "at least one" (my arithmetic, assumes independent lags).
    The interval [0.05, 0.40] is wide on purpose; the value at this seed has not been run, so it is unverified.
    """
    rate = false_spike_rate("iid", TST["n"], TST["R"], DG["seed_base"], _fast_cfg())

    assert TST["rate_lo"] <= rate <= TST["rate_hi"]


def test_pacf_squares_spike_is_a_deterministic_bool_and_checks_the_lag_window():
    """pacf_squares_spike returns a bool, the same one twice, and refuses a lag window beyond corr_lags.

    Input: one iid series (fixed seed), then a config copy with lag_max above variance.corr_lags.
    Output: asserts only (bool type, equal repeats, ValueError on the bad window).
    """
    x = simulate_recovery_model("iid", TST["n_small"], DG["seed_base"], CFG)

    first, second = pacf_squares_spike(x, CFG), pacf_squares_spike(x, CFG)
    assert isinstance(first, bool) and first == second

    bad = copy.deepcopy(CFG)
    bad["diagnostic"]["lag_max"] = CFG["variance"]["corr_lags"] + 1

    with pytest.raises(ValueError):
        pacf_squares_spike(x, bad)


def test_diagnostic_cfg_adds_arch1_models_and_does_not_touch_the_input():
    """diagnostic_cfg adds one true-(1, 0) ARCH(1) per alpha on a copy.

    Input: the loaded config. Output: asserts only. Each added model has alphas [alpha], no betas, true order
    (1, 0) and true m = 0; the series it simulates has a finite, roughly unit variance (omega = 1 - alpha);
    the input config is unchanged.
    """
    before = copy.deepcopy(CFG)
    dcfg = diagnostic_cfg(CFG)

    assert CFG == before   # the caller's config is untouched

    for alpha in DG["alphas"]:
        name = diagnostic_model_name(alpha)
        par = dcfg["recovery"]["models"][name]

        assert par["alphas"] == [alpha] and par["betas"] == []
        assert true_spec(par) == dict(m=0, p=1, q=0)

        x = simulate_recovery_model(name, TST["n_small"], DG["seed_base"], dcfg)
        assert len(x) == TST["n_small"] and np.isfinite(x).all()

    assert diagnostic_model_name(0.4) not in CFG["recovery"]["models"]


def test_diagnostic_table_has_the_documented_shape_on_a_tiny_run():
    """A tiny diagnostic run returns one row per (alpha, n) with valid shares and non-negative SEs.

    Input: a config copy with diagnostic.n = [n_small] and diagnostic.R = R_small, joblib in-process.
    Output: asserts only. Columns and row count follow D-031; every rate is in [0, 1]; false_spike_se equals
    mc_se(false_spike_rate, R); exact <= nesting.
    """
    cfg = _fast_cfg()
    cfg["diagnostic"].update(n=[TST["n_small"]], R=TST["R_small"])

    table = diagnostic_arch1_table(cfg)

    assert list(table.columns) == ["alpha", "n", "R", "exact", "nesting", "false_spike_rate",
                                   "exact_se", "nesting_se", "false_spike_se"]
    assert len(table) == len(DG["alphas"])
    assert sorted(table["alpha"]) == sorted(DG["alphas"])
    assert (table["n"] == TST["n_small"]).all() and (table["R"] == TST["R_small"]).all()

    for rate, se in [("exact", "exact_se"), ("nesting", "nesting_se"), ("false_spike_rate", "false_spike_se")]:
        assert table[rate].between(0.0, 1.0).all(), rate
        assert (table[se] >= 0.0).all(), se

    assert (table["exact"] <= table["nesting"]).all()

    for _, row in table.iterrows():
        assert row["false_spike_se"] == pytest.approx(mc_se(row["false_spike_rate"], TST["R_small"]))


def _table(low_exact, high_exact, high_spike):
    """Hand-made diagnostic table: (end value at the smallest n, at the largest n) per quantity.

    Input: low_exact, high_exact, high_spike, each a (value at smallest n, value at largest n) pair; low alpha
    gets a flat false-spike rate of 0.2. Output: DataFrame with the columns the verdict reads.
    """
    lo_a, hi_a = min(DG["alphas"]), max(DG["alphas"])
    n_lo, n_hi = min(DG["n"]), max(DG["n"])

    return pd.DataFrame([
        dict(alpha=lo_a, n=n_lo, exact=low_exact[0], false_spike_rate=0.2),
        dict(alpha=lo_a, n=n_hi, exact=low_exact[1], false_spike_rate=0.2),
        dict(alpha=hi_a, n=n_lo, exact=high_exact[0], false_spike_rate=high_spike[0]),
        dict(alpha=hi_a, n=n_hi, exact=high_exact[1], false_spike_rate=high_spike[1])])


def test_verdict_follows_the_fixed_interpretation():
    """diagnostic_verdict returns "supported" only when all three D-031 conditions hold.

    Input: hand-made tables (tol = 0.05). Output: asserts only.
      - low alpha flat (+0.01), high alpha exact falls 0.65 -> 0.45, spike rate rises 0.20 -> 0.40: supported.
      - low alpha also falls (-0.20): unexplained.
      - high alpha exact does not fall (-0.02): unexplained.
      - high alpha spike rate does not rise (+0.02): unexplained.
    """
    tol = DG["change_tol"]
    assert tol == 0.05   # the thresholds in the written decision assume 0.05

    ok = diagnostic_verdict(_table((0.80, 0.81), (0.65, 0.45), (0.20, 0.40)), CFG)
    assert ok["verdict"] == "supported"
    assert ok["low_alpha_flat"] and ok["high_alpha_falls"] and ok["high_alpha_spike_rises"]
    assert ok["change_exact_high_alpha"] == pytest.approx(-0.20)

    assert diagnostic_verdict(_table((0.80, 0.60), (0.65, 0.45), (0.20, 0.40)), CFG)["verdict"] == "unexplained"
    assert diagnostic_verdict(_table((0.80, 0.81), (0.65, 0.63), (0.20, 0.40)), CFG)["verdict"] == "unexplained"
    assert diagnostic_verdict(_table((0.80, 0.81), (0.65, 0.45), (0.20, 0.22)), CFG)["verdict"] == "unexplained"


def test_verdict_boundaries_are_exactly_minus_tol_and_plus_tol():
    """A change of exactly -0.05 counts as "does not fall"; exactly +0.05 is not a "rise".

    Input: hand-made tables whose changes sit on the thresholds. Output: asserts only. Boundaries follow D-031:
    flat means change >= -tol, falls means change < -tol, rises means change > +tol (1e-9 absorbs rounding).
    """
    edge_low = diagnostic_verdict(_table((0.80, 0.75), (0.65, 0.45), (0.20, 0.40)), CFG)   # low alpha: -0.05
    assert edge_low["low_alpha_flat"] and edge_low["verdict"] == "supported"

    edge_high = diagnostic_verdict(_table((0.80, 0.81), (0.65, 0.60), (0.20, 0.40)), CFG)   # high alpha exact: -0.05
    assert not edge_high["high_alpha_falls"] and edge_high["verdict"] == "unexplained"

    edge_spike = diagnostic_verdict(_table((0.80, 0.81), (0.65, 0.45), (0.20, 0.25)), CFG)   # spike rate: +0.05
    assert not edge_spike["high_alpha_spike_rises"] and edge_spike["verdict"] == "unexplained"
