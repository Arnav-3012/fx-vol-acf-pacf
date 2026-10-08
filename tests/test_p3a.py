"""P3a tests: recovery harness, config-driven mean trigger, no-valid-fit fallback.

Small R and n so the file runs fast. These check plumbing and behaviour at the extremes;
they do NOT check recovery rates (that is the calibration notebook).
"""
import copy

import numpy as np
import pandas as pd
import pytest

from src.data import load_config
from src.rules import mean_order_rule, pacf_cutoff, variance_order_rule
from src.selector import select_and_fit
from src.simulate import (apply_candidates, check_seed_ranges, cutoff_calibration_table,
                          order_recovery_experiment, sim_arch, sim_arch1,
                          simulate_true_model)

CFG = load_config()
CAL = CFG["calibration"]
T = CFG["sim"]["test"]   # test-only settings (n_noise, n_seeds, min_share)

# Columns every experiment row must carry (spec: chosen order, mean m, dist, cost, flags).
COLS = {"seed", "m", "p", "q", "dist", "models_fitted", "flagged", "no_valid_fit"}


def _fast_cfg() -> dict:
    """Copy of the config that runs joblib in-process (n_jobs=1): simpler and deterministic."""
    cfg = copy.deepcopy(CFG)
    cfg["calibration"]["n_jobs"] = 1
    return cfg


def test_experiment_returns_R_rows_and_is_reproducible():
    """order_recovery_experiment gives R rows with the expected columns; same seed_base, same table."""
    cfg, R, n = _fast_cfg(), 3, 500

    a = order_recovery_experiment("garch11", n, R, CAL["seed_base"], cfg)
    b = order_recovery_experiment("garch11", n, R, CAL["seed_base"], cfg)

    assert len(a) == R                                     # one row per replication
    assert COLS <= set(a.columns)
    assert list(a["seed"]) == [CAL["seed_base"] + i for i in range(R)]   # seeds come from config

    pd.testing.assert_frame_equal(a, b)                    # fixed seed -> identical results


def test_simulate_true_model_shapes_and_unknown_name():
    """Every configured true model yields a finite length-n series; an unknown name raises."""
    for name in CAL["models"]:
        x = simulate_true_model(name, 300, CAL["seed_base"], CFG)
        assert x.shape == (300,) and np.isfinite(x).all()

    with pytest.raises(ValueError):
        simulate_true_model("not_a_model", 300, CAL["seed_base"], CFG)


def test_mean_trigger_m1_gives_constant_on_iid():
    """Under M1 (LB only) iid noise gets a constant mean for most seeds, and a strong AR(1) does not.

    A single seed would fail ~5% of the time by chance (LB at alpha = 0.05), so, like the P2
    tests, we require a share of many seeds (sim.test.min_share) instead of one fixed seed.
    """
    cfg = apply_candidates(CFG, mean_trigger="M1")
    assert cfg["mean"]["trigger"] == "lb_only"

    hits = []
    for seed in range(CAL["seed_base"], CAL["seed_base"] + T["n_seeds"]):
        noise = simulate_true_model("iid", T["n_noise"], seed, cfg)
        hits.append(mean_order_rule(noise, cfg)["m"] == 0)

    assert np.mean(hits) >= T["min_share"]

    # Positive control: a clear AR(1) (phi = 0.5) must make the LB test reject "constant".
    rng = np.random.default_rng(CAL["seed_base"])
    e, x = rng.standard_normal(T["n_noise"]), np.zeros(T["n_noise"])
    for t in range(1, len(e)):
        x[t] = 0.5 * x[t - 1] + e[t]

    assert mean_order_rule(x, cfg)["m"] >= 1


def test_apply_candidates_does_not_mutate_input():
    """apply_candidates changes only the copy; the original config keeps its frozen values (F3, M1, D-023).

    Inputs: none (uses the module config). Output: asserts only.
    """
    # Switch to F2 and M0, i.e. candidates that differ from the frozen ones, so a leak into CFG would show.
    out = apply_candidates(CFG, fade="F2", mean_trigger="M0")

    # The copy carries the requested candidates.
    assert out["variance"]["fade_max_spikes"] == CAL["candidates"]["fade"]["F2"]
    assert out["mean"]["trigger"] == CAL["candidates"]["mean_trigger"]["M0"]

    # The original is untouched and still holds the frozen F3 and M1.
    assert CFG["variance"]["fade_max_spikes"] == CAL["candidates"]["fade"]["F3"]
    assert CFG["mean"]["trigger"] == CAL["candidates"]["mean_trigger"]["M1"]


def test_no_valid_fit_returns_key_without_raising():
    """An impossible persistence_tol rejects every fit; the selector reports it instead of raising.

    tol = 2 makes the cut-off 1 - 2 = -1, and persistence >= -1 for every fit, so all are invalid.
    """
    cfg = _fast_cfg()
    cfg["fit"]["persistence_tol"] = 2.0

    x = simulate_true_model("garch11", 500, CAL["seed_base"], cfg)
    r = select_and_fit(x, cfg)                       # must not raise

    assert r["no_valid_fit"] is True
    assert r["flagged"] is True
    assert np.isnan(r["persistence"])
    assert r["models_fitted"] == len(r["escalation_log"]) >= 1
    assert all(not e["valid"] for e in r["escalation_log"])
    assert all("persistence" in e for e in r["escalation_log"])   # rejected value is recorded


def test_no_valid_fit_key_is_consistent_with_persistence():
    """With the real tolerance, no_valid_fit is a bool that agrees with persistence being NaN.

    We do not assert False: a short series can legitimately land on the IGARCH boundary.
    """
    x = simulate_true_model("garch11", 1000, CAL["seed_base"], CFG)
    r = select_and_fit(x, CFG)

    assert isinstance(r["no_valid_fit"], bool)
    assert r["no_valid_fit"] == bool(np.isnan(r["persistence"]))


def test_calibration_and_eval_seed_ranges_are_disjoint():
    """The configured calibration and eval seeds do not overlap, and an overlap would be caught."""
    check_seed_ranges(CFG)   # raises if the configured ranges overlap

    bad = copy.deepcopy(CFG)
    bad["eval"]["seed_base"] = bad["calibration"]["seed_base"]
    with pytest.raises(ValueError):
        check_seed_ranges(bad)


# ---------------------------------------------------------------------------------------
# D-022: sim_arch, the PACF cut-off helper, and the cut-off candidate switch.
# ---------------------------------------------------------------------------------------

def test_sim_arch_length_finite_and_reproducible():
    """sim_arch returns a finite series of the requested length, identical for the same seed.

    Input: the arch2 parameters from config. Output checked: shape, finiteness, determinism.
    """
    par = CAL["models"]["arch2"]

    x = sim_arch(400, par["omega"], par["alphas"], CAL["seed_base"])
    y = sim_arch(400, par["omega"], par["alphas"], CAL["seed_base"])

    assert x.shape == (400,) and np.isfinite(x).all()   # burn-in is dropped, nothing blew up
    np.testing.assert_array_equal(x, y)                  # fixed seed -> identical series


def test_sim_arch_raises_when_alphas_sum_to_one_or_more():
    """A non-stationary ARCH (sum of alphas >= 1) must raise, as must a negative or missing alpha."""
    with pytest.raises(ValueError):
        sim_arch(100, 0.2, [0.5, 0.5], seed=1)     # sum exactly 1: infinite variance
    with pytest.raises(ValueError):
        sim_arch(100, 0.2, [0.7, 0.6], seed=1)     # sum above 1
    with pytest.raises(ValueError):
        sim_arch(100, 0.2, [0.3, -0.1], seed=1)    # negative alpha would allow negative variance
    with pytest.raises(ValueError):
        sim_arch(100, 0.2, [], seed=1)             # no alphas at all


def test_sim_arch_one_alpha_matches_sim_arch1():
    """With a single alpha the hand-rolled ARCH(p) recursion must equal sim_arch1 (same seed, same noise)."""
    a = sim_arch(300, 0.2, [0.4], seed=7)
    b = sim_arch1(300, 0.2, 0.4, seed=7)

    np.testing.assert_allclose(a, b)


def test_pacf_cutoff_c0_gives_3_and_c1_gives_1_for_spikes_1_and_3():
    """PACF spikes at lags {1, 3} only: C0 reads p = 3 (last spike), C1 reads p = 1 (run breaks at 2)."""
    spikes, max_p = [1, 3], CFG["variance"]["pacf_cut_max_p"]

    assert pacf_cutoff(spikes, max_p, "last_significant") == 3
    assert pacf_cutoff(spikes, max_p, "contiguous") == 1


def test_pacf_cutoff_edge_cases():
    """No spike -> 0 under both rules; no spike at lag 1 -> C1 gives 0 (fallback); the cap is respected."""
    for rule in ("last_significant", "contiguous"):
        assert pacf_cutoff([], 3, rule) == 0
        assert pacf_cutoff([1, 2, 3, 4, 5], 3, rule) == 3   # spikes above max_p are ignored

    assert pacf_cutoff([2, 3], 3, "contiguous") == 0        # no lag 1 -> no unbroken run
    assert pacf_cutoff([2, 3], 3, "last_significant") == 3

    with pytest.raises(ValueError):
        pacf_cutoff([1], 3, "not_a_rule")


def test_default_config_reproduces_current_cutoff_rule():
    """The shipped default is C0 and pacf_cutoff(default) equals the pre-D-022 formula on every spike set.

    The old rule was: p = max of the spikes <= pacf_cut_max_p, else 0. We check all subsets of lags 1..6.
    """
    vc = CFG["variance"]
    assert vc["cutoff_rule"] == CAL["candidates"]["cutoff"]["C0"] == "last_significant"

    for mask in range(2 ** 6):
        spikes = [lag for lag in range(1, 7) if mask >> (lag - 1) & 1]
        small = [lag for lag in spikes if lag <= vc["pacf_cut_max_p"]]
        old = max(small) if small else 0

        assert pacf_cutoff(spikes, vc["pacf_cut_max_p"], vc["cutoff_rule"]) == old


def test_variance_rule_default_equals_explicit_c0_on_simulated_series():
    """variance_order_rule gives the same answer under the default config and under C0 switched on explicitly."""
    c0 = apply_candidates(CFG, cutoff="C0")

    for model in ("arch1", "arch2", "garch11"):
        x = simulate_true_model(model, 1000, CAL["seed_base"], CFG)

        assert variance_order_rule(x, CFG) == variance_order_rule(x, c0)


def test_apply_candidates_cutoff_switch_and_grid_table_shape():
    """cutoff='C1' sets variance.cutoff_rule on the copy only; the grid table has the spec's columns and rows."""
    out = apply_candidates(CFG, cutoff="C1")

    assert out["variance"]["cutoff_rule"] == "contiguous"
    assert CFG["variance"]["cutoff_rule"] == "last_significant"   # original untouched

    # Tiny grid run: R = 2, in-process, to check plumbing only (not recovery rates).
    cfg = _fast_cfg()
    cfg["calibration"]["R"], cfg["calibration"]["n"] = 2, 500
    table, orders = cutoff_calibration_table(cfg)

    grid = cfg["calibration"]["cutoff_grid"]
    n_rows = len(cfg["calibration"]["candidates"]["cutoff"]) * len(grid["fade"]) * len(grid["models"])

    assert list(table.columns) == ["cutoff", "fade", "true_model", "exact_order", "flagged_rate"]
    assert list(orders.columns) == ["cutoff", "fade", "true_model", "start_order", "final_order", "count"]
    assert len(table) == n_rows
    assert orders.groupby(["cutoff", "fade", "true_model"])["count"].sum().eq(2).all()   # R rows per cell
