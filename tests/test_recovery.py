"""Tests for P3(c): the order-recovery experiment (src/simulate.py, D-030).

What is checked: the general GARCH(p, q) simulator (length, finiteness, agreement with the older
GARCH(1,1) simulator, validation, unit-variance Student-t noise), the true orders read from config, the
nesting / family / standard-error helpers on hand examples, the metrics on a hand-made result table, the
extended experiment function (eval seeds, grid_bic rows), the table builder on a tiny run, and that the
calibration and eval seed ranges are disjoint.
These tests check plumbing and definitions. They do NOT check recovery rates (that is the experiment itself).
All sizes, seeds and tolerances come from config.yaml; no real data.
"""
import copy
import math

import numpy as np
import pandas as pd
import pytest

from src.data import load_config
from src.simulate import (check_seed_ranges, family_match, mc_se, nests_true, order_count_matrix,
                          order_counts, order_recovery_experiment, recovery_metrics, recovery_table,
                          sim_arch1, sim_garch, sim_garch11, simulate_recovery_model, true_spec)

CFG = load_config()
REC = CFG["recovery"]
TST = REC["test"]            # test-only settings (n_small, R, n_var, var_tol)
SEED = CFG["sim"]["seed"]    # seed for the simulator-only checks
EVAL = CFG["eval"]["seed_base"]


def _fast_cfg() -> dict:
    """Copy of the config that runs joblib in-process (n_jobs=1): simpler and deterministic."""
    cfg = copy.deepcopy(CFG)
    cfg["recovery"]["n_jobs"] = 1

    return cfg


def test_every_recovery_model_simulates_a_finite_series_of_the_right_length():
    """Each configured true model gives a finite length-n series, identical for the same seed.

    Inputs: every name in recovery.models, n = recovery.test.n_small, an eval seed. Output checked:
    shape, finiteness, determinism; an unknown name raises ValueError.
    """
    n = TST["n_small"]

    for name in REC["models"]:
        a = simulate_recovery_model(name, n, EVAL, CFG)
        b = simulate_recovery_model(name, n, EVAL, CFG)

        assert a.shape == (n,) and np.isfinite(a).all()    # right length, no NaN or inf
        np.testing.assert_array_equal(a, b)                 # same seed -> same series

    with pytest.raises(ValueError):
        simulate_recovery_model("not_a_model", n, EVAL, CFG)


def test_configured_recovery_models_are_stationary_with_positive_omega():
    """omega = 1 - persistence must be positive for every configured model (unit unconditional variance).

    Inputs: recovery.models. Output: asserts only. A model with persistence >= 1 would make sim_garch raise.
    """
    for name, par in REC["models"].items():
        persistence = sum(par["alphas"]) + sum(par["betas"])

        assert persistence < 1, name
        assert 1.0 - persistence > 0, name


def test_sim_garch_matches_the_older_simulators():
    """The general simulator reproduces sim_garch11 and sim_arch1 for the same seed (up to float rounding).

    Inputs: GARCH(1,1) 0.05 / 0.10 / 0.85 and ARCH(1) 0.20 / 0.40, normal and Student-t, n = n_small.
    Output: arrays equal to a tight relative tolerance (the two codes add the same terms in a different
    order, so the last bits can differ; the tolerance is my choice, unverified until run).
    """
    n = TST["n_small"]

    for dist in ("normal", "t"):
        np.testing.assert_allclose(
            sim_garch(n, 0.05, [0.10], [0.85], SEED, dist=dist, nu=6.0),
            sim_garch11(n, 0.05, 0.10, 0.85, SEED, dist=dist, nu=6.0), rtol=1e-8)
        np.testing.assert_allclose(
            sim_garch(n, 0.20, [0.40], [], SEED, dist=dist, nu=6.0),
            sim_arch1(n, 0.20, 0.40, SEED, dist=dist, nu=6.0), rtol=1e-8)


def test_sim_garch_rejects_bad_inputs():
    """Persistence >= 1, omega <= 0, negative coefficients, an unknown dist and nu <= 2 all raise ValueError."""
    with pytest.raises(ValueError):
        sim_garch(100, 0.05, [0.10], [0.90], SEED)             # persistence exactly 1
    with pytest.raises(ValueError):
        sim_garch(100, 0.05, [0.60], [0.50], SEED)             # persistence 1.1
    with pytest.raises(ValueError):
        sim_garch(100, 0.0, [0.10], [0.85], SEED)              # omega = 0
    with pytest.raises(ValueError):
        sim_garch(100, 0.05, [-0.10], [0.85], SEED)            # negative alpha
    with pytest.raises(ValueError):
        sim_garch(100, 0.05, [0.10], [0.85], SEED, dist="laplace")
    with pytest.raises(ValueError):
        sim_garch(100, 0.05, [0.10], [0.85], SEED, dist="t", nu=2.0)


def test_student_t_innovations_have_approximately_unit_variance():
    """With no GARCH terms and omega = 1 the series IS the scaled-t noise, whose variance must be about 1.

    Inputs: sim_garch(n_var, omega = 1, no alphas, no betas, dist t, nu = 6) and the normal version, seed
    from config. Output: sample variance within recovery.test.var_tol of 1. The tolerance is about 5 Monte
    Carlo SDs (SD of the sample variance of a t(6) is about sqrt(5 / n_var), my arithmetic, unverified),
    so a failure means the rescaling sqrt((nu - 2) / nu) is wrong, not bad luck.
    """
    nu = REC["models"]["garch11_t"]["nu"]

    t_noise = sim_garch(TST["n_var"], 1.0, [], [], SEED, dist="t", nu=nu)
    normal_noise = sim_garch(TST["n_var"], 1.0, [], [], SEED)

    assert abs(t_noise.var() - 1.0) < TST["var_tol"]
    assert abs(normal_noise.var() - 1.0) < TST["var_tol"]

    # The t noise really is heavier-tailed than the normal one, else dist was ignored: over this many
    # draws the largest |value| of a t(6) is far above that of a normal (the sample kurtosis would be
    # too erratic to test, because a t(6) has no finite 8th moment).
    assert np.abs(t_noise).max() > np.abs(normal_noise).max()


def test_true_orders_and_mean_orders_read_from_config():
    """true_spec returns the true (m, p, q) of each configured model by counting alphas and betas.

    Inputs: recovery.models. Output: ARCH(1) = (0, 1, 0), GARCH(1,1) and its t version = (0, 1, 1),
    GARCH(2,1) = (0, 2, 1), GARCH(1,2) = (0, 1, 2), iid = (0, 0, 0), AR(1)+GARCH(1,1) = (1, 1, 1).
    """
    expected = dict(arch1=(0, 1, 0), garch11=(0, 1, 1), garch21=(0, 2, 1), garch12=(0, 1, 2),
                    garch11_t=(0, 1, 1), iid=(0, 0, 0), ar1_garch11=(1, 1, 1))

    for name, (m, p, q) in expected.items():
        assert true_spec(REC["models"][name]) == dict(m=m, p=p, q=q), name


def test_nesting_helper_on_hand_examples():
    """nests_true: a final order nests the truth when final_p >= true_p AND final_q >= true_q.

    Cases (D-030): (2, 0) nests true ARCH(1) = (1, 0); (1, 1) does NOT nest (2, 1); (3, 1) does;
    the true order nests itself; (2, 0) does not nest (1, 1) (q too small); arrays work elementwise.
    """
    assert bool(nests_true(2, 0, 1, 0))          # one extra ARCH lag still contains ARCH(1)
    assert not bool(nests_true(1, 1, 2, 1))      # too few ARCH lags
    assert bool(nests_true(3, 1, 2, 1))          # more ARCH lags contain the truth
    assert bool(nests_true(2, 1, 2, 1))          # the truth contains itself
    assert not bool(nests_true(2, 0, 1, 1))      # no variance lag, truth needs one

    np.testing.assert_array_equal(nests_true(np.array([2, 1, 3]), np.array([0, 1, 1]), 2, 1),
                                  [False, False, True])


def test_family_helper_on_hand_examples():
    """family_match: (start_q >= 1) == (true_q >= 1), i.e. right choice of pure ARCH versus GARCH.

    Cases: true ARCH(1) (q = 0): start q = 0 matches, start q = 1 does not; true GARCH (q = 1 or 2):
    start q = 0 does not match, start q = 1 or 2 matches; arrays work elementwise.
    """
    assert bool(family_match(0, 0)) and not bool(family_match(1, 0))
    assert not bool(family_match(0, 1)) and bool(family_match(1, 1)) and bool(family_match(2, 1))
    assert bool(family_match(1, 2))

    np.testing.assert_array_equal(family_match(np.array([0, 1, 2]), 1), [False, True, True])


def test_mc_se_formula():
    """Monte Carlo SE = sqrt(p (1 - p) / R): 0.05 at p = 0.5 and R = 100, 0 at p = 0 or 1, NaN stays NaN."""
    assert mc_se(0.5, 100) == pytest.approx(0.05)
    assert mc_se(0.0, 100) == 0.0 and mc_se(1.0, 100) == 0.0
    assert mc_se(0.25, 4) == pytest.approx(math.sqrt(0.25 * 0.75 / 4))
    assert math.isnan(mc_se(float("nan"), 100))


def _hand_result() -> pd.DataFrame:
    """Four hand-made replications against a true GARCH(2,1) (m = 0).

    r0: final (2,1), valid, 1 fit, gate passed.   r1: final (3,1), valid, 2 fits, gate passed.
    r2: final (1,1) with AR(1), valid, 3 fits, gate passed.   r3: final (2,1) but NO valid fit, 4 fits, flagged.
    All four started at (2, 1) except r2, which started at (1, 1).
    """
    return pd.DataFrame(dict(
        seed=[0, 1, 2, 3], m=[0, 0, 1, 0], p=[2, 3, 1, 2], q=[1, 1, 1, 1],
        start_p=[2, 2, 1, 2], start_q=[1, 1, 1, 1], dist=["normal"] * 4,
        models_fitted=[1, 2, 3, 4], flagged=[False, False, False, True],
        no_valid_fit=[False, False, False, True], gate_passed=[True, True, True, False]))


def test_recovery_metrics_on_a_hand_made_table():
    """recovery_metrics on four hand-made rows (true GARCH(2,1)), every rate worked out by hand.

    exact: r0 only (r3 has the right order but no valid fit) = 0.25. nesting: r0, r1 = 0.50 (r2 has p = 1 < 2;
    r3 excluded). family: all start with q = 1 = true family = 1.0. any_ar: r2 = 0.25. gate_pass: 3 of 4 = 0.75.
    escalation: models_fitted > 1 in r1, r2, r3 = 0.75. flagged 0.25, no_valid_fit 0.25, mean_fits 2.5.
    SE = sqrt(p (1 - p) / 4). For grid_bic the family, gate_pass and escalation entries are NaN.
    """
    out = recovery_metrics(_hand_result(), "garch21", CFG, "hybrid")

    assert out["exact"] == 0.25 and out["nesting"] == 0.5 and out["family"] == 1.0
    assert out["any_ar_rate"] == 0.25 and out["gate_pass"] == 0.75 and out["escalation_rate"] == 0.75
    assert out["flagged"] == 0.25 and out["no_valid_fit"] == 0.25 and out["mean_fits"] == 2.5

    assert out["exact_se"] == pytest.approx(math.sqrt(0.25 * 0.75 / 4))
    assert out["family_se"] == 0.0                            # a share of exactly 1 has no sampling spread
    assert out["gate_pass_se"] == pytest.approx(math.sqrt(0.75 * 0.25 / 4))

    grid = recovery_metrics(_hand_result(), "garch21", CFG, "grid_bic")
    assert grid["exact"] == 0.25 and grid["nesting"] == 0.5
    assert all(math.isnan(grid[k]) for k in ("family", "gate_pass", "escalation_rate", "family_se"))


def test_seed_ranges_are_disjoint_and_the_experiment_uses_eval_seeds():
    """Calibration and eval seed ranges do not overlap; an overlap is caught; smoke R fits inside sim.R.

    Inputs: calibration.seed_base / R, eval.seed_base, sim.R, recovery.smoke_R. Output: asserts only.
    """
    cal, ev, R = CFG["calibration"], CFG["eval"], CFG["sim"]["R"]

    # Half-open intervals [base, base + R) must not intersect.
    assert cal["seed_base"] + cal["R"] <= ev["seed_base"] or ev["seed_base"] + R <= cal["seed_base"]
    check_seed_ranges(CFG)

    assert REC["smoke_R"] <= R              # the smoke run uses the first smoke_R eval seeds only

    bad = copy.deepcopy(CFG)
    bad["eval"]["seed_base"] = bad["calibration"]["seed_base"] + 1
    with pytest.raises(ValueError):
        check_seed_ranges(bad)


def test_extended_experiment_hybrid_rows_use_eval_seeds_and_are_reproducible():
    """order_recovery_experiment with model_set='recovery' returns R rows on eval seeds, same table twice.

    Inputs: true model garch11, n_small, R = recovery.test.R, hybrid. Output: columns include gate_passed,
    seeds are eval.seed_base + i (none inside the calibration range), start orders are present,
    and two runs are identical.
    """
    cfg, R, n = _fast_cfg(), TST["R"], TST["n_small"]

    a = order_recovery_experiment("garch11", n, R, EVAL, cfg, selector="hybrid", model_set="recovery")
    b = order_recovery_experiment("garch11", n, R, EVAL, cfg, selector="hybrid", model_set="recovery")

    assert len(a) == R
    assert {"seed", "m", "p", "q", "start_p", "start_q", "dist", "models_fitted", "flagged",
            "no_valid_fit", "gate_passed"} <= set(a.columns)
    assert list(a["seed"]) == [EVAL + i for i in range(R)]

    cal = CFG["calibration"]
    assert not a["seed"].between(cal["seed_base"], cal["seed_base"] + cal["R"] - 1).any()
    assert a["start_p"].notna().all()

    pd.testing.assert_frame_equal(a, b)


def test_extended_experiment_grid_bic_row_has_no_start_order_or_gate():
    """grid_bic rows: the whole grid is fitted (30 fits), start order and gate verdict are NaN, order text is n/a.

    Inputs: true model garch11, n_small, one replication, selector grid_bic. Output: models_fitted equals
    (grid_max) x (grid_max + 1) = 30 for the default grid (p in 1..5, q in 0..5), gate_passed and start_p NaN,
    order_counts writes start_order 'n/a'. An unknown selector name raises.
    """
    cfg, n = _fast_cfg(), TST["n_small"]
    gmax = cfg["baselines"]["grid_max"]

    df = order_recovery_experiment("garch11", n, 1, EVAL, cfg, selector="grid_bic", model_set="recovery")

    assert df["models_fitted"].iloc[0] == gmax * (gmax + 1)
    assert df["gate_passed"].isna().all() and df["start_p"].isna().all()
    assert list(order_counts(df)["start_order"]) == ["n/a"]

    with pytest.raises(ValueError):
        order_recovery_experiment("garch11", n, 1, EVAL, cfg, selector="not_a_selector", model_set="recovery")


def test_recovery_table_smoke_shape_and_order_counts_add_up():
    """recovery_table on a tiny run: one hybrid row per true model, orders sum to R, columns as specified.

    Inputs: smoke mode with R = recovery.test.R, n = n_small, no grid length (grid_n empty so the test
    stays fast), in-process joblib. Output: len(models) rows, every selector hybrid, every orders cell sums
    to R, rates within [0, 1], no_valid_fit rows never counted as exact.
    """
    cfg = _fast_cfg()
    cfg["recovery"].update(smoke=True, smoke_R=TST["R"], smoke_n=[TST["n_small"]], grid_n=[])

    table, orders = recovery_table(cfg)

    assert list(table["true_model"]) == list(REC["models"]) and (table["selector"] == "hybrid").all()
    assert (table["R"] == TST["R"]).all() and (table["n"] == TST["n_small"]).all()
    assert list(orders.columns) == ["true_model", "n", "selector", "start_order", "final_order", "count"]
    assert (orders.groupby(["true_model", "n", "selector"])["count"].sum() == TST["R"]).all()

    # Every rate has a Monte Carlo SE column; rates are shares in [0, 1] and SEs are non-negative.
    se_of = dict(exact="exact_se", nesting="nesting_se", family="family_se", any_ar_rate="any_ar_se",
                 gate_pass="gate_pass_se", escalation_rate="escalation_se", flagged="flagged_se",
                 no_valid_fit="no_valid_fit_se")

    for rate, se in se_of.items():
        assert table[rate].between(0.0, 1.0).all(), rate
        assert (table[se] >= 0.0).all(), se

    assert (table["exact"] <= table["nesting"]).all()        # exact is a special case of nesting


def test_recovery_table_refuses_R_above_sim_R():
    """R larger than sim.R would use eval seeds the overlap check never looked at: it must raise before running."""
    cfg = _fast_cfg()
    cfg["recovery"].update(smoke=True, smoke_R=CFG["sim"]["R"] + 1)

    with pytest.raises(ValueError):
        recovery_table(cfg)


def test_order_count_matrix_on_a_hand_example():
    """order_count_matrix lays final-order counts on a (p x q) grid and refuses orders outside it.

    Inputs: counts (1,1) x 3, (2,0) x 2 for one cell, plus a row for another model that must be ignored.
    Output: a 4 x 3 grid (pmax 3, qmax 2) with 3 at p = 1, q = 1 and 2 at p = 2, q = 0 and zeros elsewhere;
    pmax = 1 raises because (2, 0) falls outside the grid.
    """
    orders = pd.DataFrame(dict(
        true_model=["arch1", "arch1", "garch11"], n=[1000, 1000, 1000], selector=["hybrid"] * 3,
        start_order=["(1, 1)", "(1, 0)", "(1, 1)"], final_order=["(1, 1)", "(2, 0)", "(3, 2)"], count=[3, 2, 9]))

    mat = order_count_matrix(orders, "arch1", 1000, "hybrid", 3, 2)

    assert mat.shape == (4, 3)
    assert mat.loc[1, 1] == 3 and mat.loc[2, 0] == 2 and mat.to_numpy().sum() == 5

    with pytest.raises(ValueError):
        order_count_matrix(orders, "arch1", 1000, "hybrid", 1, 2)
