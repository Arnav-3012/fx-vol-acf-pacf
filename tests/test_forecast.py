"""Tests for P3(a): the five selectors (src/baselines.py) and the rolling forecast (src/forecast.py).

What is checked: no look-ahead, the row count, the rolling-variance formula, the grid size of the
BIC baseline, that the ACF-only baseline has no escalation, and the D-019 fallback bookkeeping.
All data are simulated with seeds from config.yaml; no real data and no network.
"""
import copy

import numpy as np
import pandas as pd
import pytest

from src import baselines
from src.baselines import acf_only, grid_bic, rolling_var
from src.data import load_config
from src.forecast import COLUMNS, rolling_refit_forecast
from src.simulate import sim_garch11

CFG = load_config()


def _cfg() -> dict:
    """Copy of the config with smoke off and joblib in-process (n_jobs=1), so tests are small and deterministic."""
    cfg = copy.deepcopy(CFG)
    cfg["forecast"]["smoke"] = False
    cfg["forecast"]["n_jobs"] = 1

    return cfg


def _garch(n: int) -> np.ndarray:
    """Simulated GARCH(1,1) shocks of length n, using the demo parameters and sim.seed from config."""
    g = CFG["sim"]["demo"]["garch11"]

    return sim_garch11(n, g["omega"], g["alpha"], g["beta"], seed=CFG["sim"]["seed"])


def _series(n: int) -> pd.Series:
    """Simulated returns as a pd.Series with a business-day index and the name 'SIM' (the 'pair')."""
    idx = pd.bdate_range("2015-01-01", periods=n)

    return pd.Series(_garch(n), index=idx, name="SIM")


@pytest.mark.parametrize("name", ["rolling_var", "fixed_garch11", "acf_only"])
def test_no_look_ahead_forecasts_up_to_k_ignore_later_returns(name):
    """Changing returns AFTER position k leaves every forecast dated <= k identical.

    Inputs: a 300-day simulated series, k inside the second refit block. Output: asserts only.
    The forecast for day i may only use returns[:i]; if any later value leaked in (in the refit
    or in the variance update), the early rows would change.
    """
    cfg = _cfg()
    y = _series(300)                       # test period = last 60 days = positions 240..299
    k = 269                                # inside the block that refits at position 260

    # Perturbed copy: everything after position k is rescaled and shifted (a big change).
    y2 = y.copy()
    y2.iloc[k + 1:] = y2.iloc[k + 1:] * 3.0 + 1.0

    a = rolling_refit_forecast(y, name, cfg)
    b = rolling_refit_forecast(y2, name, cfg)

    early = a["date"] <= y.index[k]
    assert early.sum() == k - 240 + 1      # positions 240..k are forecast days

    # Identical up to and including day k: same forecasts and same targets.
    np.testing.assert_array_equal(a.loc[early, "h"].to_numpy(), b.loc[early, "h"].to_numpy())
    np.testing.assert_array_equal(a.loc[early, "r2"].to_numpy(), b.loc[early, "r2"].to_numpy())

    # Sanity: after k the perturbation does matter, so the test could have failed.
    assert not np.allclose(a.loc[~early, "h"], b.loc[~early, "h"])


def test_forecast_row_count_equals_test_length_and_block_structure():
    """One row per test day, in the documented column order, with one refit_date per 20-day block.

    Inputs: 290 simulated returns. test_fraction 0.2 gives 58 test days = blocks of 20, 20, 18.
    """
    cfg = _cfg()
    y = _series(290)

    out = rolling_refit_forecast(y, "rolling_var", cfg)

    assert len(out) == 58                                          # 290 * 0.2, written by hand
    assert list(out.columns) == COLUMNS
    assert list(out["date"]) == list(y.index[-58:])                # targets are the last 58 days
    assert out["refit_date"].nunique() == 3                        # ceil(58 / 20) refits
    assert (out["refit_date"] < out["date"]).all()                 # a refit never sees its own target
    assert out["models_fitted"].sum() == 0                         # rolling variance fits no model
    assert (out["pair"] == "SIM").all() and (out["selector"] == "rolling_var").all()


def test_smoke_mode_keeps_only_the_last_smoke_days():
    """With forecast.smoke true the output has smoke_days rows (when the test period is longer)."""
    cfg = _cfg()
    cfg["forecast"]["smoke"], cfg["forecast"]["smoke_days"] = True, 30

    out = rolling_refit_forecast(_series(290), "rolling_var", cfg)

    assert len(out) == 30                                          # 58 test days, capped at 30


def test_rolling_var_matches_hand_computed_variance_of_last_window():
    """rolling_var's h_next equals the variance of the last rolling_window values, computed by hand.

    Inputs: 200 iid normal draws (seed from config). Output: asserts only. ddof = 0 as in np.var.
    """
    w = CFG["baselines"]["rolling_window"]
    x = np.random.default_rng(CFG["sim"]["seed"]).standard_normal(200)

    out = rolling_var(x, CFG)

    # By hand: mean of the last w values, then the average squared distance from it.
    last = x[-w:]
    mean = last.sum() / w
    expected = ((last - mean) ** 2).sum() / w

    assert out["h_next"] == pytest.approx(expected)
    assert out["h_next"] == pytest.approx(np.var(x[-w:]))
    assert out["order"] is None and out["models_fitted"] == 0


def test_grid_bic_fits_the_whole_grid_on_simulated_garch11():
    """grid_bic fits every (p, q), p in 1..grid_max, q in 0..grid_max, and returns a usable fit.

    Inputs: GARCH(1,1) with n = 1500 (seed from config). models_fitted counts ALL fits, valid
    or not, so it equals the grid size by construction; we also check that a valid winner exists.
    """
    gmax = CFG["baselines"]["grid_max"]

    out = grid_bic(_garch(1500), CFG)

    assert out["models_fitted"] == gmax * (gmax + 1)               # 5 * 6 = 30
    assert not out["no_valid_fit"]
    p, q = out["order"]
    assert 1 <= p <= gmax and 0 <= q <= gmax
    assert np.isfinite(out["h_next"]) and out["h_next"] > 0


def test_acf_only_has_no_escalation_and_fits_once():
    """acf_only does a single fit with no gate: no escalation_log key, models_fitted == 1."""
    out = acf_only(_garch(1500), CFG)

    assert "escalation_log" not in out
    assert out["models_fitted"] == 1
    assert out["flagged"] == out["no_valid_fit"]                   # no gate: flagged only through no_valid_fit


def test_no_valid_fit_falls_back_to_rolling_variance_and_is_flagged(monkeypatch):
    """A selector that reports no_valid_fit gets the rolling variance for its whole block (D-019).

    Inputs: a fake selector registered under 'fixed_garch11' (monkeypatch, in-process because
    n_jobs = 1). Output: every h equals the rolling variance of returns[:i], and the flag is set.
    """
    cfg = _cfg()
    y = _series(290)
    w = cfg["baselines"]["rolling_window"]

    def fake(train, cfg):
        """Pretend every fit was rejected."""
        return dict(h_next=rolling_var(train, cfg)["h_next"], order=(1, 1), models_fitted=7,
                    flagged=True, no_valid_fit=True, spec=None)

    monkeypatch.setitem(baselines.SELECTORS, "fixed_garch11", fake)

    out = rolling_refit_forecast(y, "fixed_garch11", cfg)

    assert out["no_valid_fit"].all() and out["flagged"].all()
    assert out["models_fitted"].sum() == 7 * 3                     # 3 refits, 7 fits each, counted once per refit

    # Day by day, h = variance of the last w returns BEFORE the target day.
    pos = {d: i for i, d in enumerate(y.index)}
    for d, h in zip(out["date"], out["h"]):
        assert h == pytest.approx(np.var(y.to_numpy()[: pos[d]][-w:]))


def test_p3b_columns_for_valid_and_rejected_refits(monkeypatch):
    """The P3(b) columns describe the refit in force and repeat on every row of its block (D-028).

    Inputs: rolling_var (no fits) and a fake selector that reports rejected fits (reason
    'persistence>=1-tol', persistence 0.9999995, 7 fits). Output: rolling_var rows are 'valid' with an
    empty reason, 0 fits and NaN persistence; the fake's rows are all 'no_valid_fit' with refit_models 7
    on EVERY row (unlike models_fitted, which is counted once per block).
    """
    cfg = _cfg()
    y = _series(290)

    ok = rolling_refit_forecast(y, "rolling_var", cfg)
    assert (ok["fit_status"] == "valid").all() and (ok["reject_reason"] == "").all()
    assert (ok["refit_models"] == 0).all() and ok["rejected_persistence"].isna().all()

    def fake(train, cfg):
        """Pretend every fit was rejected for sitting on the persistence boundary."""
        return dict(h_next=rolling_var(train, cfg)["h_next"], order=(1, 1), models_fitted=7,
                    flagged=True, no_valid_fit=True, spec=None,
                    reject_reason="persistence>=1-tol", rejected_persistence=0.9999995)

    monkeypatch.setitem(baselines.SELECTORS, "fixed_garch11", fake)
    bad = rolling_refit_forecast(y, "fixed_garch11", cfg)

    assert (bad["fit_status"] == "no_valid_fit").all() and (bad["refit_models"] == 7).all()
    assert (bad["reject_reason"] == "persistence>=1-tol").all()
    assert (bad["rejected_persistence"] == 0.9999995).all()


def test_reject_summary_orders_and_dedups_reasons():
    """_reject_summary keeps first-seen order, drops duplicates and takes the max persistence.

    Inputs: four rejected fits (two reasons, two of them for persistence). Output: the reasons joined
    by ';' and max persistence 0.95; no rejections give '' and NaN.
    """
    from src.baselines import _reject_summary

    reason, pers = _reject_summary([("omega<=0", 0.5), ("persistence>=1-tol", 0.9),
                                    ("omega<=0", 0.4), ("persistence>=1-tol", 0.95)])
    assert reason == "omega<=0;persistence>=1-tol" and pers == 0.95

    reason, pers = _reject_summary([])
    assert reason == "" and np.isnan(pers)


def test_dist_column_is_normal_for_valid_garch_fits_and_empty_without_a_model():
    """The dist column (D-029) holds the error distribution of the model in force, '' when there is none.

    Inputs: rolling_var (no model) and fixed_garch11 (normal errors by fit.dist) on 290 simulated days.
    Output: rolling_var rows all have dist ''; fixed_garch11 rows have 'normal' on every valid row and ''
    on every no_valid_fit row (whichever occurs). The column is observation only, so h is untouched.
    """
    cfg = _cfg()
    y = _series(290)

    none = rolling_refit_forecast(y, "rolling_var", cfg)
    assert (none["dist"] == "").all()

    fixed = rolling_refit_forecast(y, "fixed_garch11", cfg)
    valid = fixed["fit_status"] == "valid"

    assert (fixed.loc[valid, "dist"] == cfg["fit"]["dist"]).all()
    assert (fixed.loc[~valid, "dist"] == "").all()
