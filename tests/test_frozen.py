"""Frozen-rules guard (D-023).

The selector rules were frozen on simulated calibration data. These tests pin the frozen values
as read from config.yaml, so any accidental edit (or a candidate left switched on) fails loudly.
Changing a value on purpose needs a new decision entry, a calibration rerun and an eval-seed
recovery rerun; then this file is updated in the same step.
"""
from src.data import load_config

CFG = load_config()


def test_frozen_selector_rules_are_read_from_config():
    """The four frozen values (cut-off rule, fade tolerance, mean trigger, persistence tolerance) match D-023.

    Inputs: none (reads config.yaml through load_config). Output: asserts only.
    """
    # C0: the ARCH order p is the last significant PACF lag of squared residuals.
    assert CFG["variance"]["cutoff_rule"] == "last_significant"

    # F3: up to 3 spurious ACF-of-squares spikes in lags fade_lag..corr_lags are tolerated before "fades" is False.
    assert CFG["variance"]["fade_max_spikes"] == 3

    # M1: the mean model leaves "constant" only when Ljung-Box on the returns fails.
    assert CFG["mean"]["trigger"] == "lb_only"

    # A fit with alpha + beta >= 1 - 1e-6 is rejected as an IGARCH-boundary fit.
    assert CFG["fit"]["persistence_tol"] == 1.0e-6


def test_frozen_marker_records_date_and_decision():
    """The top-level `frozen` key names the freeze date and the decision entry that justifies it.

    Inputs: none. Output: asserts only.
    """
    # The date is a string in config.yaml (quoted), so compare as text.
    assert str(CFG["frozen"]["date"]) == "2026-10-08"

    # The decision ID links the config back to docs/decision.md.
    assert CFG["frozen"]["decision_id"] == "D-023"
