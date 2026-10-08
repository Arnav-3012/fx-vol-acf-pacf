"""Tests for the dashboard support code (src/dashboard.py) and a smoke test of app.py (D-032).

Part 1 tests the pure helpers with small hand-made or simulated inputs: the as-of cut (no look-ahead),
the table builders, the rule readout, the CSV readers (on a temporary folder, never the real results/),
and the live Monte Carlo wrapper (a tiny run). Part 2 runs the whole app with streamlit's AppTest on
the default widget values. AppTest exists in the installed streamlit 1.65.0 (its folder streamlit/testing/v1
was listed, not run); the test is skipped with a reason if it is missing or the raw price CSV is absent.
"""
import copy
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src import dashboard
from src.dashboard import (FAIL, PASS, RATES, SKIP, asof_bounds, diagnostic_table, explain_values, grid_comparison,
                           label_values, live_recovery, order_shares, pair_rows, plain_param, rate_specs,
                           rates_table, read_result, render_text, result_mtime, results_table, rule_readout,
                           saved_order_counts, saved_recovery_row, scale_percent, selection_tables, slice_asof,
                           stationarity_table, step_table, summary_table, true_order_label)
from src.data import ROOT, load_config
from src.rules import mean_order_rule, variance_order_rule
from src.selector import _mean_resid
from src.simulate import sim_garch11

CFG = load_config()
SEED = CFG["sim"]["seed"]
SEL = CFG["app"]["selector_labels"]   # plain selector names shown in tables


def _series(n: int = 600) -> pd.Series:
    """A simulated GARCH(1,1) return series (sim.test.garch11 parameters) on business days.

    Input: n length. Output: Series with a DatetimeIndex starting 2020-01-01.
    """
    par = CFG["sim"]["test"]["garch11"]
    x = sim_garch11(n, par["omega"], par["alpha"], par["beta"], SEED)

    return pd.Series(x, index=pd.bdate_range("2020-01-01", periods=n))


# ---------------------------------------------------------------------------------------
# As-of cut and the Data tab
# ---------------------------------------------------------------------------------------

def test_slice_asof_keeps_the_asof_day_and_nothing_later():
    """The cut keeps dates <= as-of (also when as-of is a weekend), and changing later values changes nothing.

    Inputs: a 600-day series, an as-of on a trading day and on a Saturday, and a copy whose later
    values are overwritten. Output checked: last date, length, and equality of the two cuts (no look-ahead).
    """
    s = _series()
    day = s.index[300]

    cut = slice_asof(s, day)
    assert cut.index[-1] == day and len(cut) == 301

    # 2020-01-04 is a Saturday: the cut falls back to Friday 2020-01-03.
    assert slice_asof(s, "2020-01-04").index[-1] == pd.Timestamp("2020-01-03")

    # Overwrite everything after the as-of day: the cut must not notice.
    changed = s.copy()
    changed.iloc[301:] = 999.0
    pd.testing.assert_series_equal(slice_asof(changed, day), cut)


def test_asof_bounds_leave_at_least_min_obs_returns():
    """First allowed date is the min_obs-th return, last is the final date; too little data raises.

    Inputs: 600 returns, min_obs 500, then min_obs 700. Output checked: the two dates, and ValueError.
    """
    s = _series(600)

    first, last = asof_bounds(s, 500)
    assert first == s.index[499].date() and last == s.index[-1].date()
    assert len(slice_asof(s, first)) == 500

    with pytest.raises(ValueError):
        asof_bounds(s, 700)


def test_summary_table_matches_hand_values():
    """n, mean, std and the zero count on a 5-value series computed by hand.

    Input: [0, 0, 1, -1, 2]. By hand: n 5, mean 0.4, sum of squared deviations 5.2, std (ddof 1) sqrt(5.2/4),
    two exact zeros. Output checked: those values and the column names.
    """
    out = summary_table(pd.Series([0.0, 0.0, 1.0, -1.0, 2.0]))

    assert list(out.columns) == ["n", "mean", "std", "skew", "excess_kurtosis", "zero_returns"]
    row = out.iloc[0]
    assert row["n"] == 5 and row["zero_returns"] == 2
    assert math.isclose(row["mean"], 0.4) and math.isclose(row["std"], math.sqrt(1.3))
    assert np.isfinite(row[["skew", "excess_kurtosis"]].astype(float)).all()


# ---------------------------------------------------------------------------------------
# Diagnose tab
# ---------------------------------------------------------------------------------------

def test_diagnostic_table_has_one_row_per_gate_lag_and_series_plus_arch_lm():
    """Rows: Ljung-Box at every gate lag for returns and for squares, plus one ARCH-LM row; p in [0, 1].

    Input: 600 simulated returns. Output checked: row count, test labels, lags, p-value range.
    """
    out = diagnostic_table(_series(), CFG)
    lags = CFG["gate"]["lb_lags"]

    assert len(out) == 2 * len(lags) + 1
    assert list(out["test"]).count("Ljung-Box") == 2 * len(lags) and list(out["test"]).count("ARCH-LM") == 1
    assert list(out[out["series"] == "squared returns"]["lag"])[:len(lags)] == lags
    assert out["p_value"].between(0.0, 1.0).all()


def test_rule_readout_passes_the_rules_reason_strings_through_unchanged():
    """The readout's reasons equal what the two rules return directly, and each sentence matches its branch.

    Input: 2000 simulated GARCH returns. Output checked: reasons identical to mean_order_rule /
    variance_order_rule on the same input, the sentence for the branch taken (constant vs AR, stop vs ARCH vs GARCH),
    and the Ljung-Box-only note on a constant mean.
    """
    x = _series(2000).to_numpy()
    out = rule_readout(x, CFG)

    # The same two rule calls made by hand (the mean residual step is the selector's own helper).
    mean = mean_order_rule(x, CFG)
    var = variance_order_rule(_mean_resid(x, mean["m"]), CFG)
    assert out["mean"]["reason"] == mean["reason"] and out["variance"]["reason"] == var["reason"]
    assert out["variance"]["order"] == var["start_order"]

    # Sentence per branch. Which branch is taken depends on the data, so the test follows the output.
    if out["mean"]["m"] == 0:
        assert "constant" in out["mean"]["text"] and "Ljung-Box" in out["mean"]["text"]   # M1 is frozen (D-023): only Ljung-Box decides
    else:
        assert f"AR({out['mean']['m']})" in out["mean"]["text"]

    p, q = out["variance"]["order"]
    if out["variance"]["stop"]:
        assert out["variance"]["text"].startswith("No ARCH effect")
    elif q == 0:
        assert out["variance"]["text"].startswith(f"Start from ARCH({p})")
    else:
        assert out["variance"]["text"].startswith(f"Start from the GARCH({p},{q})")


# ---------------------------------------------------------------------------------------
# Select tab
# ---------------------------------------------------------------------------------------

def _fake_result(valid: bool = True) -> dict:
    """A hand-made select_and_fit result (same keys as selector.select_and_fit) for table tests.

    Input: valid False gives the no-valid-fit shape (empty params and gate, NaN persistence).
    Output: dict. Two log entries: the start fit (gate failed) and a neighbour fit (gate passed).
    """
    nan = float("nan")
    log = [dict(step="start", order=(1, 1), dist="normal", bic=100.0, valid=valid,
                why="ok" if valid else "persistence>=1-tol", persistence=0.95 if valid else 1.0,
                gate_passed=False if valid else None),
           dict(step="neighbour", order=(2, 1), dist="normal", bic=99.0, valid=valid,
                why="ok" if valid else "persistence>=1-tol", persistence=0.96 if valid else 1.0,
                gate_passed=True if valid else None)]

    return dict(mean_spec=dict(m=0, kind="constant", reason="constant: ..."), mean_resid_lb_p=0.5,
                order=(2, 1) if valid else (1, 1), dist="normal",
                params={"mu": 0.01, "omega": 0.02, "alpha[1]": 0.05, "alpha[2]": 0.04, "beta[1]": 0.87} if valid else {},
                persistence=0.96 if valid else nan, bic=99.0 if valid else nan,
                gate=dict(lb_p={5: 0.4, 10: 0.03, 20: 0.7}, lm_p=0.6, passed=False) if valid
                else dict(lb_p={}, lm_p=nan, passed=False),
                escalation_log=log, models_fitted=2, flagged=not valid, no_valid_fit=not valid,
                reason="mean | variance | step")


def test_selection_tables_split_a_valid_result():
    """Summary, params, gate and log tables carry the result's numbers; gate pass flags follow gate.alpha.

    Input: the fake valid result. Output checked: start and final order text, params rows, 3 Ljung-Box
    rows plus ARCH-LM, the pass flag of the p = 0.03 row (False), the log rows and the gate column text.
    """
    t = selection_tables(_fake_result(), CFG)
    summary = dict(zip(t["summary"]["item"], t["summary"]["value"]))

    assert summary["start order (p, q)"] == "(1, 1)" and summary["final order (p, q)"] == "(2, 1)"
    assert summary["models fitted"] == "2" and summary["no valid fit"] == "False"
    assert len(t["params"]) == 5 and list(t["params"].columns) == ["parameter", "value"]

    assert len(t["gate"]) == 4
    flags = dict(zip(t["gate"]["test"], t["gate"]["passes"]))
    assert not flags["Squared residuals: Ljung-Box, lag 10"]   # p = 0.03 is below gate.alpha, so it fails
    assert t["gate"]["passes"].tolist() == [p > CFG["gate"]["alpha"] for p in [0.4, 0.03, 0.7, 0.6]]

    assert list(t["log"]["gate"]) == ["Failed", "Passed"] and list(t["log"]["order"]) == ["(1, 1)", "(2, 1)"]


def test_selection_tables_handle_a_result_with_no_valid_fit():
    """No valid fit: empty params and gate tables with their columns, log rows say "Not tested".

    Input: the fake no-valid-fit result. Output checked: table shapes and the log's gate column.
    """
    t = selection_tables(_fake_result(valid=False), CFG)

    assert t["params"].empty and t["gate"].empty
    assert list(t["gate"].columns) == ["test", "p_value", "passes"]
    assert list(t["log"]["gate"]) == ["Not tested", "Not tested"]
    assert dict(zip(t["summary"]["item"], t["summary"]["value"]))["no valid fit"] == "True"


def test_grid_comparison_has_a_row_per_selector():
    """One row for hybrid (from the selection result) and one for grid_bic (from its fit dict).

    Input: the fake valid result and a hand-made grid_bic dict. Output checked: rows, orders, fit counts;
    a grid dict without a spec gives an empty dist.
    """
    grid = dict(order=(1, 1), models_fitted=30, flagged=False, no_valid_fit=False,
                spec=dict(m=0, order=(1, 1), dist="normal", params={"omega": 0.1}))
    out = grid_comparison(_fake_result(), grid, CFG)

    assert list(out["selector"]) == [SEL["hybrid"], SEL["grid_bic"]]
    assert list(out["order"]) == ["(2, 1)", "(1, 1)"] and list(out["models_fitted"]) == [2, 30]

    grid["spec"] = None
    assert grid_comparison(_fake_result(), grid, CFG)["dist"].iloc[1] == ""


# ---------------------------------------------------------------------------------------
# Forecast tab (CSV readers on a temporary folder)
# ---------------------------------------------------------------------------------------

def test_read_result_and_mtime_on_a_temporary_results_folder(tmp_path, monkeypatch):
    """A missing file gives None for both readers; an existing one is read, `date` is parsed, mtime is a float.

    Inputs: dashboard.ROOT pointed at a temp folder (the real results/ is never touched), one CSV written there.
    Output checked: None before, DataFrame and datetime64 dtype after; pair_rows keeps only the asked pair.
    """
    monkeypatch.setattr(dashboard, "ROOT", tmp_path)
    (tmp_path / CFG["paths"]["results_dir"]).mkdir()

    assert read_result(CFG, "x.csv") is None and result_mtime(CFG, "x.csv") is None

    pd.DataFrame({"date": ["2023-01-02", "2023-01-03", "2023-01-04"], "pair": ["A", "B", "A"],
                  "v": [1, 2, 3]}).to_csv(tmp_path / CFG["paths"]["results_dir"] / "x.csv", index=False)

    df = read_result(CFG, "x.csv")
    assert df is not None and pd.api.types.is_datetime64_any_dtype(df["date"])
    assert isinstance(result_mtime(CFG, "x.csv"), float)

    only_a = pair_rows(df, "A")
    assert list(only_a["v"]) == [1, 3] and list(only_a.index) == [0, 1]


# ---------------------------------------------------------------------------------------
# Simulate tab
# ---------------------------------------------------------------------------------------

def test_true_order_label_reads_the_configured_models():
    """Labels follow recovery.models: p = number of alphas, q = number of betas.

    Inputs: arch1, garch21, garch12, iid. Output checked: "(1, 0)", "(2, 1)", "(1, 2)", "(0, 0)".
    """
    assert [true_order_label(CFG, m) for m in ["arch1", "garch21", "garch12", "iid"]] == \
           ["(1, 0)", "(2, 1)", "(1, 2)", "(0, 0)"]


def test_rates_table_and_saved_row_lookup():
    """rates_table lists plain-named rates in RATES order, in percent, with their SE; saved_recovery_row finds one row or None.

    Inputs: a hand-made metrics dict and a two-row recovery table. Output checked: plain names, the
    percent values (fraction times 100), the row found for (arch1, 500, hybrid), None for a missing combination.
    """
    metrics = {}
    for i, (rate, se) in enumerate(RATES):
        metrics[rate], metrics[se] = i / 10, i / 100

    out = rates_table(metrics, CFG)
    assert list(out["rate"]) == [CFG["app"]["rate_labels"][r] for r, _ in RATES]
    assert list(out.columns) == ["rate", "share", "mc_se"]
    assert math.isclose(out["share"].iloc[2], 20.0) and math.isclose(out["mc_se"].iloc[2], 2.0)

    table = pd.DataFrame([dict(true_model="arch1", n=500, selector="hybrid", R=500, exact=0.658),
                          dict(true_model="arch1", n=1000, selector="hybrid", R=500, exact=0.606)])
    assert saved_recovery_row(table, "arch1", 500, "hybrid")["exact"] == 0.658
    assert saved_recovery_row(table, "arch1", 500, "grid_bic") is None


def test_live_recovery_rejects_r_outside_the_cap_before_computing():
    """R = 0 and R above app.simulate.max_live_R raise ValueError (no simulation is started)."""
    cap = CFG["app"]["simulate"]["max_live_R"]

    for bad in (0, cap + 1):
        with pytest.raises(ValueError):
            live_recovery("garch11", CFG["recovery"]["test"]["n_small"], bad, CFG)


def test_live_recovery_small_run_returns_rates_and_order_counts():
    """A tiny live run (R = recovery.test.R) gives all rates with SEs and counts that add up to R.

    Input: garch11, n = recovery.test.n_small, in-process joblib (n_jobs = 1). Output checked: metrics
    keys, rate range, count total, and that the counts table has the order_counts columns.
    """
    cfg = copy.deepcopy(CFG)
    cfg["recovery"]["n_jobs"] = 1   # run in this process: simpler and deterministic
    R = CFG["recovery"]["test"]["R"]

    metrics, counts = live_recovery("garch11", CFG["recovery"]["test"]["n_small"], R, cfg)

    assert all(rate in metrics and se in metrics for rate, se in RATES)
    assert 0.0 <= metrics["exact"] <= 1.0
    assert list(counts.columns) == ["start_order", "final_order", "count"] and counts["count"].sum() == R


# ---------------------------------------------------------------------------------------
# P4b: plain labels, step table, explanation text (D-034)
# ---------------------------------------------------------------------------------------

def test_label_values_and_scale_percent_change_only_what_they_should():
    """Coded values become plain names, unknown values stay, fractions become percent, the input is untouched.

    Input: a table with a selector column (one known id, one unknown), a fraction column and an unrelated column.
    Output checked: mapped names, unchanged unknown id, x100 on the listed column only, original frame unchanged.
    """
    df = pd.DataFrame({"selector": ["hybrid", "mystery"], "fallback_share": [0.25, 0.5], "refits": [3, 4]})

    out = scale_percent(label_values(df, CFG), ["fallback_share", "not_a_column"])

    assert list(out["selector"]) == [SEL["hybrid"], "mystery"]
    assert list(out["fallback_share"]) == [25.0, 50.0] and list(out["refits"]) == [3, 4]
    assert list(df["selector"]) == ["hybrid", "mystery"] and list(df["fallback_share"]) == [0.25, 0.5]


def test_plain_param_names():
    """arch parameter names become plain text; a lag index is spelled out; an unknown name is returned as is."""
    labels = CFG["app"]["param_labels"]

    assert plain_param("alpha[2]", CFG) == f"{labels['alpha']}, lag 2"
    assert plain_param("omega", CFG) == labels["omega"] and plain_param("Const", CFG) == labels["Const"]
    assert plain_param("mystery", CFG) == "mystery"


def test_results_table_filters_the_pair_scales_percent_and_labels_values():
    """One pair's rows without the pair column; fractions x100 (app.percent_columns); plain selector and outcome names.

    Input: a 3-row loss-style table for two pairs. Output checked: row count, dropped column, percent value,
    selector and status labels.
    """
    df = pd.DataFrame({"pair": ["A", "A", "B"], "selector": ["hybrid", "grid_bic", "hybrid"],
                       "fallback_share": [0.5, 0.0, 1.0], "status": ["ok", "identical", "ok"]})

    out = results_table(df, "A", CFG)

    assert len(out) == 2 and "pair" not in out.columns
    assert list(out["fallback_share"]) == [50.0, 0.0]
    assert list(out["selector"]) == [SEL["hybrid"], SEL["grid_bic"]]
    assert list(out["status"]) == [CFG["app"]["value_labels"]["status"]["ok"], CFG["app"]["value_labels"]["status"]["identical"]]


def test_config_labels_cover_everything_the_ui_can_show():
    """No snake_case in the UI: every selector, model, rate, table column and tab has a plain label in the config.

    Input: config.yaml and the columns of every table the app shows (real helper outputs on simulated data,
    the fake select result, and the loss / dm table headers as written by P3(b2)). Output checked: each name
    is a key of the matching app.* map; each tab has the four explanation parts; the glossary lists the
    required terms.
    """
    from src.baselines import SELECTORS

    app = CFG["app"]
    assert set(SELECTORS) <= set(app["selector_labels"])
    assert set(CFG["recovery"]["models"]) <= set(app["model_labels"])
    assert {r for r, _ in RATES} <= set(app["rate_labels"]) and set(app["simulate"]["chart_rates"]) <= set(app["rate_labels"])

    r = _series(600)
    shown = [summary_table(r), stationarity_table(np.exp(r.cumsum() / 100), r, CFG), diagnostic_table(r, CFG),
             rates_table({k: 0.5 for pair in RATES for k in pair}, CFG), step_table(_fake_result(), CFG),
             grid_comparison(_fake_result(), dict(order=(1, 1), models_fitted=1, flagged=False, no_valid_fit=False, spec=None), CFG),
             *selection_tables(_fake_result(), CFG).values()]
    loss_cols = ["selector", "qlike", "mse", "models_fitted", "refits", "escalation_rate", "modal_order_share",
                 "agree_grid", "n_both_valid", "fallback_share", "valid_day_qlike"]
    dm_cols = ["loss", "sample", "A", "B", "mean_diff", "dm", "p", "L", "status", "n_days", "dm_L20", "p_L20"]

    columns = {c for df in shown for c in df.columns} | set(loss_cols) | set(dm_cols)
    assert columns <= set(app["columns"]), sorted(columns - set(app["columns"]))
    assert set(app["percent_columns"]) <= set(app["columns"])

    for tab in ["data", "diagnose", "select", "forecast", "simulate"]:
        assert set(app["explain"][tab]) == set(app["explain"]["parts"]) == {"what", "how", "look", "caveats"}

    terms = {g["term"] for g in app["glossary"]}
    assert {"ACF", "PACF", "Band", "GARCH(p,q)", "Gate", "Escalation", "Nesting", "Family", "QLIKE",
            "Diebold-Mariano", "Fallback"} <= terms


def _fake_tables() -> dict:
    """Hand-made stand-ins for the four results CSVs that explain_values reads.

    Output: dict(diagnostic, recovery, loss, dm) of small DataFrames with the real column names and
    values chosen so each expected placeholder text can be worked out by hand.
    """
    return dict(
        diagnostic=pd.DataFrame({"alpha": [0.2, 0.2, 0.4, 0.4], "n": [500, 4000, 500, 4000],
                                 "false_spike_rate": [0.2, 0.25, 0.3, 0.5]}),
        recovery=pd.DataFrame({"n": [1000, 1000, 1000], "selector": ["hybrid", "hybrid", "grid_bic"],
                               "mean_fits": [1.0, 2.0, 30.0]}),
        loss=pd.DataFrame({"pair": ["P", "P", "Q"], "selector": ["hybrid", "fixed_garch11", "hybrid"],
                           "fallback_share": [0.5, 0.25, 0.9]}),
        dm=pd.DataFrame({"pair": ["P", "P"], "sample": ["all", "common_valid"], "n_days": [838, 200]}))


def test_explain_values_come_from_the_tables_and_missing_sources_print_na():
    """Placeholder numbers are computed from the given tables (hand-checked), and a missing source gives "n/a".

    Input: the fake tables, a saved row (R 500, exact 0.658, nesting 0.994) and a live run (SE 0.0707 for exact).
    Output checked: spike rates of the larger alpha at the shortest and longest length (30.0%, 50.0%) and of the
    smaller alpha at the longest (25.0%), mean fits at the grid length (hybrid 1.5, grid 30.0), fallback shares
    of pair P only (50.0%, 25.0%), 838 test days, saved and live texts, and "n/a" when tables are None.
    """
    r = _series(600)
    saved = dict(R=500, exact=0.658, nesting=0.994)
    live = dict(exact_se=0.0707)

    v = explain_values(CFG, "DEXUSEU", r, _fake_tables(), live_metrics=live, live_R=20, saved_row=saved)

    assert (v["spike_rate_small_n"], v["spike_rate_large_n"], v["spike_rate_low_alpha"]) == ("30.0%", "50.0%", "25.0%")
    assert (v["alpha_high"], v["alpha_low"], v["n_small"], v["n_large"]) == ("0.4", "0.2", "500", "4,000")
    assert (v["hybrid_fits"], v["grid_fits"]) == ("1.5", "30.0")

    v_p = explain_values(CFG, "P", r, _fake_tables())
    assert (v_p["fallback_hybrid"], v_p["fallback_fixed"], v_p["n_days"]) == ("50.0%", "25.0%", "838")

    assert (v["saved_R"], v["saved_exact"], v["saved_nesting"]) == ("500", "65.8%", "99.4%")
    assert v["live_R"] == "20" and v["live_se_exact"] == "+/- 7.1 percentage points"
    assert v["pair_label"] == CFG["app"]["pair_labels"]["DEXUSEU"] and v["n_obs"] == "600"

    none = explain_values(CFG, "DEXUSEU", r, dict(diagnostic=None, recovery=None, loss=None, dm=None))
    assert "spike_rate_large_n" not in none and render_text("x {spike_rate_large_n} y", none) == "x n/a y"


def test_every_placeholder_in_the_config_text_is_filled_when_all_sources_exist():
    """Each {placeholder} used in app.explain and app.simulate.live_note is a key explain_values can produce.

    Input: all explanation texts, the live note, and explain_values called with every source present.
    Output checked: the set of placeholders is a subset of the returned keys (a typo in the config would
    otherwise silently print "n/a").
    """
    app = CFG["app"]
    texts = [t for tab in ["data", "diagnose", "select", "forecast", "simulate"] for t in app["explain"][tab].values()]
    texts.append(app["simulate"]["live_note"])
    used = set(re.findall(r"\{(\w+)\}", " ".join(texts)))

    tables = _fake_tables()
    tables["loss"]["pair"] = "DEXUSEU"
    tables["dm"]["pair"] = "DEXUSEU"
    v = explain_values(CFG, "DEXUSEU", _series(600), tables, live_metrics=dict(exact_se=0.05), live_R=20,
                       saved_row=dict(R=500, exact=0.6, nesting=0.9))

    assert used and used <= set(v), sorted(used - set(v))


def test_step_table_shows_the_right_icons_for_three_kinds_of_result():
    """Seven steps; icons follow the result: normal pass with escalation, no valid fit, constant variance.

    Input: (a) the fake valid result with gate passed and one extra fit, (b) the fake no-valid-fit result,
    (c) a constant-variance result (single log entry). Output checked: row count, icon of each decisive step,
    and that escalation steps are named in plain words.
    """
    a = _fake_result()
    a["gate"]["passed"], a["flagged"] = True, False
    t = step_table(a, CFG)
    assert len(t) == 7
    assert t["result"][3].startswith(PASS) and t["result"][4].startswith(PASS) and t["result"][5].startswith(PASS)
    assert t["result"][6].startswith(PASS) and CFG["app"]["value_labels"]["step"]["neighbour"] in t["detail"][6]

    b = step_table(_fake_result(valid=False), CFG)
    assert b["result"][3].startswith(FAIL) and b["result"][4].startswith(FAIL)
    assert b["result"][5].startswith(SKIP) and b["result"][6].startswith(FAIL)

    c = _fake_result()
    c["escalation_log"] = c["escalation_log"][:1]
    c["escalation_log"][0].update(step="constant_variance", order=(0, 0))
    c["gate"]["passed"], c["models_fitted"] = True, 1
    tc = step_table(c, CFG)
    assert tc["result"][1].startswith(SKIP) and tc["result"][2].startswith(SKIP) and tc["result"][6].startswith(SKIP)


def test_order_shares_are_percentages_and_saved_counts_select_one_cell():
    """Shares add to 100 and start orders are summed away; saved_order_counts picks (model, n, selector).

    Input: counts with two start orders ending on (1, 1), and a three-row orders table. Output checked:
    shares 70 / 30, the selected rows, and rate_specs pairing each key with its SE key and plain label.
    """
    counts = pd.DataFrame({"start_order": ["(1, 1)", "(2, 0)", "(1, 1)"], "final_order": ["(1, 1)", "(1, 1)", "(2, 1)"],
                           "count": [5, 2, 3]})
    s = order_shares(counts)
    assert math.isclose(s["(1, 1)"], 70.0) and math.isclose(s["(2, 1)"], 30.0) and math.isclose(s.sum(), 100.0)

    orders = pd.DataFrame({"true_model": ["arch1", "arch1", "garch11"], "n": [500, 1000, 500],
                           "selector": ["hybrid", "hybrid", "hybrid"], "final_order": ["(1, 0)"] * 3, "count": [1, 2, 3]})
    assert list(saved_order_counts(orders, "arch1", 1000, "hybrid")["count"]) == [2]

    assert rate_specs(CFG, ["exact"]) == [("exact", "exact_se", CFG["app"]["rate_labels"]["exact"])]


# ---------------------------------------------------------------------------------------
# Whole app (AppTest)
# ---------------------------------------------------------------------------------------

def test_app_runs_on_default_widgets_without_exception():
    """app.py runs end to end on its defaults: no exception, five tabs, the fixed frozen-rules note.

    Input: AppTest.from_file("app.py") with default widget values (first pair, last as-of date); this runs
    one select_and_fit on the full sample, hence the long timeout (app.test.timeout_s). Output checked:
    no st.exception element, the five tab labels, the sidebar note "Rules frozen, D-023", five "How to read
    this tab" expanders, the sidebar glossary and at least five Plotly charts.
    Skipped (with a reason) if streamlit.testing.v1 is missing or the first pair's raw CSV is absent
    (the app would try to download it). Needs plotly installed (the app imports it through src/plots.py).
    """
    testing = pytest.importorskip("streamlit.testing.v1",
                                  reason="streamlit.testing.v1 (AppTest) not available in this streamlit version")

    raw = ROOT / CFG["paths"]["raw_dir"] / f"{CFG['pairs'][0]}.csv"
    if not raw.exists():
        pytest.skip(f"{raw} missing: the app would download it, and tests must not use the network")

    at = testing.AppTest.from_file(str(Path(ROOT) / "app.py"), default_timeout=CFG["app"]["test"]["timeout_s"])
    at.run()

    assert len(at.exception) == 0, [e.message for e in at.exception]
    assert [t.label for t in at.tabs] == ["Data", "Diagnose", "Select", "Forecast", "Simulate"]
    assert any(f"Rules frozen, {CFG['frozen']['decision_id']}" in i.value for i in at.sidebar.info)

    # P4b: a "How to read this tab" expander on every tab, a sidebar glossary, and the Plotly charts that are
    # always drawn (3 on Data, 1 on Diagnose, 1 on Select). "plotly_chart" as the AppTest element name is an
    # assumption (unverified).
    assert [e.label for e in at.expander].count(CFG["app"]["explain"]["title"]) == 5
    assert CFG["app"]["glossary_title"] in [e.label for e in at.sidebar.expander]
    assert len(at.get("plotly_chart")) >= 5
