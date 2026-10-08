"""Tests for P3(b): src/evaluate.py (QLIKE, MSE, Diebold-Mariano with Newey-West, result tables).

What is checked: losses against hand-computed numbers, the guards (h <= 0, non-finite), the
Newey-West long-run variance and the DM statistic against hand calculations, the "identical"
status, the sign and size of DM for a clearly better forecaster, and the table builders on a
tiny hand-made forecast table. Random data use the seed and sizes from config.yaml; no real data.
"""
import math

import numpy as np
import pandas as pd
import pytest
from scipy.stats import norm

from src.data import load_config
from src.evaluate import (block_qlike_diff, cumulative_qlike_diff, diebold_mariano, dm_table,
                          loss_table, max_abs_h_diff, mse, newey_west_lrv, nw_lag, qlike)

CFG = load_config()


def test_qlike_hand_values():
    """QLIKE = ln(h) + r2/h on three hand-computed days.

    Inputs: (h, r2) = (2, 4), (1, 0), (4, 2). Output: ln2 + 2, 0, ln4 + 0.5.
    """
    out = qlike([2.0, 1.0, 4.0], [4.0, 0.0, 2.0])

    # (2,4): ln 2 + 4/2 ; (1,0): ln 1 + 0 = 0 (r2 = 0 is allowed) ; (4,2): ln 4 + 2/4.
    assert out == pytest.approx([math.log(2) + 2.0, 0.0, math.log(4) + 0.5])


def test_qlike_is_smallest_at_the_truth_on_average():
    """For a fixed r2 = 3 the QLIKE minimiser over h is h = r2 (derivative 1/h - r2/h^2 = 0).

    Inputs: three h around 3. Output: the middle one (h = r2) has the lowest loss.
    """
    losses = [qlike([h], [3.0])[0] for h in (2.0, 3.0, 4.0)]

    assert losses[1] < losses[0] and losses[1] < losses[2]


def test_mse_hand_values():
    """MSE = (r2 - h)^2 on hand-computed days.

    Inputs: (h, r2) = (2, 4), (1, 0), (3, 3). Output: 4, 1, 0.
    """
    assert mse([2.0, 1.0, 3.0], [4.0, 0.0, 3.0]) == pytest.approx([4.0, 1.0, 0.0])


@pytest.mark.parametrize("loss", [qlike, mse])
@pytest.mark.parametrize("h", [[0.0], [-1.0], [float("nan")], [float("inf")]])
def test_nonpositive_or_nonfinite_h_raises(loss, h):
    """h <= 0 or a non-finite h must raise ValueError for both losses (ln(0) / r2/0 guard).

    Inputs: h = 0, -1, NaN, inf with r2 = 1. Output: ValueError.
    """
    with pytest.raises(ValueError):
        loss(h, [1.0])


def test_negative_r2_and_length_mismatch_raise():
    """A negative squared return and mismatched lengths are also rejected.

    Inputs: r2 = -1; h of length 2 against r2 of length 1. Output: ValueError each time.
    """
    with pytest.raises(ValueError):
        qlike([1.0], [-1.0])
    with pytest.raises(ValueError):
        qlike([1.0, 2.0], [1.0])


def test_newey_west_lrv_matches_hand_calculation():
    """Newey-West LRV on d = [1, 2, 3, 4] with L = 1, worked out by hand.

    dbar = 2.5, deviations = [-1.5, -0.5, 0.5, 1.5]. gamma_0 = (2.25 + 0.25 + 0.25 + 2.25) / 4 = 1.25.
    gamma_1 = ((-0.5)(-1.5) + (0.5)(-0.5) + (1.5)(0.5)) / 4 = 1.25 / 4 = 0.3125.
    Bartlett weight at k = 1 with L = 1 is 1 - 1/2 = 0.5, so LRV = 1.25 + 2 * 0.5 * 0.3125 = 1.5625.
    Second case d = [1, -1, 1, -1], L = 1: gamma_0 = 1, gamma_1 = -3/4, LRV = 1 + 2 * 0.5 * (-0.75) = 0.25.
    Also L = 0 must give just gamma_0.
    """
    assert newey_west_lrv([1, 2, 3, 4], 1) == pytest.approx(1.5625)
    assert newey_west_lrv([1, -1, 1, -1], 1) == pytest.approx(0.25)
    assert newey_west_lrv([1, 2, 3, 4], 0) == pytest.approx(1.25)


def test_dm_statistic_matches_hand_calculation():
    """DM = mean(d) / sqrt(LRV / T) with the hand LRV above.

    Inputs: loss_a = [1, 2, 3, 4], loss_b = 0, L = 1. Output: mean_diff 2.5, dm = 2.5 / sqrt(1.5625 / 4)
    = 2.5 / 0.625 = 4, two-sided normal p = 2 * (1 - Phi(4)).
    """
    out = diebold_mariano([1, 2, 3, 4], [0, 0, 0, 0], L=1)

    assert out["status"] == "ok" and out["L"] == 1
    assert out["mean_diff"] == pytest.approx(2.5)
    assert out["dm"] == pytest.approx(4.0)
    assert out["p"] == pytest.approx(2 * norm.sf(4.0))


def test_nw_lag_rule():
    """L = floor(4 * (T/100)^(2/9)): T = 100 gives exactly 4; T = 838 gives floor(6.4) = 6.

    The T = 838 value is my hand arithmetic (4 * 8.38^(2/9) is about 6.42), not a run output.
    """
    assert nw_lag(100, CFG) == 4
    assert nw_lag(838, CFG) == 6


def test_identical_series_give_status_identical():
    """Two identical loss series have a zero-variance differential: status 'identical', no dm or p.

    Inputs: the same QLIKE series twice. Output: status identical, dm and p NaN, mean_diff 0.
    """
    rng = np.random.default_rng(CFG["sim"]["seed"])
    la = qlike(rng.uniform(0.5, 2.0, 200), rng.uniform(0.0, 4.0, 200))

    out = diebold_mariano(la, la.copy(), cfg=CFG)

    assert out["status"] == "identical"
    assert out["mean_diff"] == 0.0
    assert math.isnan(out["dm"]) and math.isnan(out["p"])


def test_lower_loss_by_constant_plus_noise_gives_negative_dm_and_small_p():
    """A is lower than B by a constant shift, both with noise: DM < 0 and a small p.

    Inputs: n, shift, noise_sd from config evaluate.test; seed from config sim.seed. B is noise,
    A is B - shift + extra noise, so d = -shift + noise with sd 1. Output: dm < 0, p < 0.01,
    status ok. Expected dm is around -0.3 / (1 / sqrt(500)) = about -6.7 (my estimate,
    unverified), far inside the p < 0.01 band.
    """
    t = CFG["evaluate"]["test"]
    rng = np.random.default_rng(CFG["sim"]["seed"])

    loss_b = rng.normal(0.0, t["noise_sd"], t["n"])
    loss_a = loss_b - t["shift"] + rng.normal(0.0, t["noise_sd"], t["n"])

    out = diebold_mariano(loss_a, loss_b, cfg=CFG)

    assert out["status"] == "ok"
    assert out["dm"] < 0 and out["p"] < 0.01
    assert out["mean_diff"] < 0


def test_dm_guards():
    """Bad inputs raise: unequal lengths, non-finite losses, bandwidth not shorter than the sample."""
    with pytest.raises(ValueError):
        diebold_mariano([1.0, 2.0, 3.0], [1.0, 2.0], L=1)
    with pytest.raises(ValueError):
        diebold_mariano([1.0, float("nan"), 3.0], [1.0, 2.0, 3.0], L=1)
    with pytest.raises(ValueError):
        diebold_mariano([1.0, 2.0, 3.0], [3.0, 2.0, 1.0], L=3)


def _toy_forecasts() -> dict:
    """Tiny hand-made forecast table for one pair: 40 days, 2 refits of 20, 3 selectors.

    hybrid and grid_bic share the same h (identical); fixed_garch11 differs. grid_bic has a
    fallback on the second refit (no_valid_fit) and a different order there. The hybrid uses
    dist "normal" in block 0 and "t" in block 1; the others always "normal". Returns {"P": df}.
    """
    dates = pd.date_range("2024-01-01", periods=40, freq="B")
    # Evenly spaced r2 with mean exactly 1.25. (A period-4 pattern was avoided on purpose: its
    # long-run variance is about zero, which would trip the nonpositive_lrv guard.)
    r2 = np.linspace(0.5, 2.0, 40)
    rows = []

    for sel, hval, orders, statuses, models in [
        ("hybrid", 1.0, ["(1, 1)", "(1, 1)"], ["valid", "valid"], [1, 3]),
        ("grid_bic", 1.0, ["(1, 1)", "(2, 1)"], ["valid", "no_valid_fit"], [30, 30]),
        ("fixed_garch11", 1.2, ["(1, 1)", "(1, 1)"], ["valid", "valid"], [1, 1]),
    ]:
        for i, d in enumerate(dates):
            b = i // 20                                    # refit block 0 or 1
            rows.append(dict(
                date=d, pair="P", selector=sel, h=hval, r2=r2[i], order=orders[b],
                models_fitted=models[b] if i % 20 == 0 else 0, flagged=False,
                no_valid_fit=statuses[b] == "no_valid_fit", refit_date=dates[b * 20] - pd.Timedelta(days=1),
                refit_models=models[b], fit_status=statuses[b], reject_reason="",
                rejected_persistence=float("nan"),
                dist="t" if (sel == "hybrid" and b == 1) else "normal"))

    return {"P": pd.DataFrame(rows)}


def _toy_cfg() -> dict:
    """Config copy whose comparisons fit the toy table."""
    cfg = {k: (dict(v) if isinstance(v, dict) else v) for k, v in CFG.items()}
    cfg["evaluate"] = dict(CFG["evaluate"], comparisons=[["hybrid", "grid_bic"], ["hybrid", "fixed_garch11"]])

    return cfg


def test_loss_table_columns_and_values():
    """loss_table on the toy data: hand-checkable counts and shares (D-029 definitions).

    Output: grid_bic has 2 refits, 60 fits, escalation_rate NaN (it always fits many models),
    fallback_share 0.5, and agrees with itself on its 1 valid refit (n_both_valid 1);
    hybrid escalates in 1 of 2 refits (3 fits > 1), and agrees with grid_bic on the 1 refit where
    both were valid (block 0, both (1, 1)), so agree_grid is 1.0 on n_both_valid 1 (the second refit,
    where they differ, is excluded because grid_bic had no valid fit there). Its QLIKE on valid days
    equals its overall QLIKE (no fallback).
    """
    tab = loss_table(_toy_forecasts(), _toy_cfg()).set_index("selector")

    assert list(loss_table(_toy_forecasts(), _toy_cfg()).columns) == [
        "pair", "selector", "qlike", "mse", "models_fitted", "refits", "escalation_rate",
        "modal_order_share", "agree_grid", "n_both_valid", "fallback_share", "valid_day_qlike"]

    g = tab.loc["grid_bic"]
    assert g["refits"] == 2 and g["models_fitted"] == 60
    assert math.isnan(g["escalation_rate"])                       # NaN by definition for the grid selector
    assert g["fallback_share"] == 0.5 and g["agree_grid"] == 1.0 and g["n_both_valid"] == 1

    h = tab.loc["hybrid"]
    assert h["escalation_rate"] == 0.5 and h["modal_order_share"] == 1.0
    assert h["agree_grid"] == 1.0 and h["n_both_valid"] == 1      # block 1 is excluded (grid had no valid fit)
    assert h["valid_day_qlike"] == pytest.approx(h["qlike"])

    # QLIKE of h = 1 is ln 1 + mean(r2) = mean of linspace(0.5, 2, 40) = 1.25.
    assert h["qlike"] == pytest.approx(1.25)


def test_dm_table_identical_and_common_valid():
    """dm_table on the toy data: identical h gives status identical; common_valid halves the days.

    Output: hybrid vs grid_bic is 'identical' in both samples (same h); the common_valid sample
    has 20 days (grid_bic is in fallback for the second block); n_days is 40 for 'all'.
    """
    tab = dm_table(_toy_forecasts(), _toy_cfg())
    hg = tab[(tab["B"] == "grid_bic") & (tab["loss"] == "qlike")].set_index("sample")

    assert (hg["status"] == "identical").all()
    assert hg.loc["all", "n_days"] == 40 and hg.loc["common_valid", "n_days"] == 20
    assert tab["dm"][tab["status"] == "identical"].isna().all()

    # Different h: the test runs (status ok) and the columns are the specified ones.
    hf = tab[(tab["B"] == "fixed_garch11") & (tab["sample"] == "all") & (tab["loss"] == "qlike")]
    assert (hf["status"] == "ok").all()
    assert list(tab.columns) == ["pair", "loss", "sample", "A", "B", "mean_diff", "dm", "p", "L",
                                 "status", "n_days", "dm_L20", "p_L20"]

    # The sensitivity columns are empty exactly where there is no primary test (identical rows).
    assert tab.loc[tab["status"] == "identical", ["dm_L20", "p_L20"]].isna().all().all()


def test_cumulative_diff_and_regression_check():
    """cumulative_qlike_diff ends at the summed difference; max_abs_h_diff is 0 for equal runs.

    Output: hybrid minus fixed_garch11 cumulative QLIKE after 40 days equals the sum of daily
    differences; max_abs_h_diff of a table with itself is 0, and 0.1 after nudging one h by 0.1.
    """
    fc = _toy_forecasts()["P"]
    cfg = _toy_cfg()
    cfg["evaluate"]["figure_baseline"] = "fixed_garch11"

    cum = cumulative_qlike_diff(fc, cfg)
    expected = (qlike(np.full(40, 1.0), fc[fc.selector == "hybrid"]["r2"])
                - qlike(np.full(40, 1.2), fc[fc.selector == "hybrid"]["r2"])).sum()
    assert "fixed_garch11" not in cum.columns
    assert cum["hybrid"].iloc[-1] == pytest.approx(expected)

    assert max_abs_h_diff(fc, fc.copy()) == 0.0
    bumped = fc.copy()
    bumped.loc[0, "h"] += 0.1
    assert max_abs_h_diff(bumped, fc) == pytest.approx(0.1)


def test_dm_L20_sensitivity_matches_direct_call_and_is_pinned_to_refit_every():
    """dm_L20 / p_L20 equal diebold_mariano with L = forecast.refit_every, while dm / p keep the formula L (D-029).

    Inputs: the toy table, comparison hybrid vs fixed_garch11, QLIKE, sample 'all' (T = 40, so
    L = 20 < T). Output: dm_L20 and p_L20 match a direct diebold_mariano(..., L=20) call (both NaN if
    that call is not 'ok'); the primary L column is the formula value nw_lag(40), not 20.
    Also pins forecast.refit_every = 20, because the column names say 20.
    """
    assert CFG["forecast"]["refit_every"] == 20

    fc = _toy_forecasts()["P"]
    cfg = _toy_cfg()
    row = dm_table({"P": fc}, cfg)
    row = row[(row["B"] == "fixed_garch11") & (row["loss"] == "qlike") & (row["sample"] == "all")].iloc[0]

    h = fc[fc.selector == "hybrid"]
    f = fc[fc.selector == "fixed_garch11"]
    direct = diebold_mariano(qlike(h["h"], h["r2"]), qlike(f["h"], f["r2"]), L=20)

    expected = (direct["dm"], direct["p"]) if direct["status"] == "ok" else (float("nan"), float("nan"))
    np.testing.assert_allclose([row["dm_L20"], row["p_L20"]], expected, equal_nan=True)
    assert row["L"] == nw_lag(40, cfg) and row["L"] != 20


def test_dm_L20_is_nan_when_the_bandwidth_is_not_shorter_than_the_sample():
    """With T = 20 days (common_valid hybrid vs grid_bic is identical anyway) a non-identical pair has no L = 20 test.

    Inputs: the toy table restricted so that hybrid vs fixed_garch11 has T = 20 days (min_days is 20,
    so the primary test runs, but L = 20 is not < 20). Output: dm_L20 and p_L20 are NaN, dm is a number.
    """
    fc = _toy_forecasts()["P"]
    fc = fc[fc["refit_date"] == fc["refit_date"].min()]           # keep only refit block 0 (20 days)
    cfg = _toy_cfg()
    cfg["evaluate"] = dict(cfg["evaluate"], comparisons=[["hybrid", "fixed_garch11"]], samples=["all"])

    row = dm_table({"P": fc}, cfg)
    row = row[row["loss"] == "qlike"].iloc[0]

    assert row["n_days"] == 20 and row["status"] == "ok" and np.isfinite(row["dm"])
    assert np.isnan(row["dm_L20"]) and np.isnan(row["p_L20"])


def test_block_qlike_diff_hand_values_shares_and_filters():
    """block_qlike_diff splits the QLIKE difference by refit block with hand-computable sums (D-029).

    Inputs: the toy table (h hybrid = 1.0, h fixed = 1.2, r2 = linspace(0.5, 2, 40), two blocks of 20).
    Output: two rows; block value = (1 - 1/1.2) * sum(r2 in block) - 20 * ln(1.2); shares add to 1;
    the hybrid's dist is normal then t; n_days 20 each. For hybrid vs grid_bic the h are identical,
    grid_bic has no valid fit in block 1, so one row remains, its difference is exactly 0 and its
    share is NaN (total 0). A table without a dist column is refused.
    """
    fc = _toy_forecasts()["P"]
    r2 = np.linspace(0.5, 2.0, 40)

    cfg = _toy_cfg()
    cfg["evaluate"] = dict(cfg["evaluate"], block_compare=["hybrid", "fixed_garch11"])
    out = block_qlike_diff(fc, cfg)

    expected = [(1 - 1 / 1.2) * r2[s].sum() - 20 * math.log(1.2) for s in (slice(0, 20), slice(20, 40))]
    assert list(out.columns) == ["refit_date", "hybrid_order", "hybrid_dist", "fixed_garch11_order",
                                 "n_days", "block_qlike_diff", "share_of_total"]
    assert out["block_qlike_diff"].to_numpy() == pytest.approx(expected)
    assert out["share_of_total"].sum() == pytest.approx(1.0)
    assert list(out["hybrid_dist"]) == ["normal", "t"] and list(out["n_days"]) == [20, 20]

    cfg["evaluate"] = dict(cfg["evaluate"], block_compare=["hybrid", "grid_bic"])
    same = block_qlike_diff(fc, cfg)
    assert len(same) == 1 and same["block_qlike_diff"].iloc[0] == 0.0 and np.isnan(same["share_of_total"].iloc[0])

    with pytest.raises(ValueError):
        block_qlike_diff(fc.drop(columns="dist"), cfg)
