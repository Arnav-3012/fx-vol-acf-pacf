"""Tests for src/plots.py (D-034): every builder returns a Plotly Figure with a plain title and titled axes.

Two kinds of test. (1) One parametrised test runs every builder on small data and checks the house
style: a non-empty title with no raw variable names (no arch1, no "n = ..", no snake_case), and a
non-empty title on every axis. (2) One test per builder checks that the right numbers were drawn
(values, trace counts, error bars, the true-order trace, fallback shading), because a figure with the
right layout but wrong data would pass the style test. Data are small simulated or hand-made series;
nothing is fitted. The whole file is skipped, with a reason, if plotly is not installed in the venv
(it was not when D-034 was written, so these tests are UNVERIFIED until the user has installed it).
"""
import re

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("plotly", reason="plotly is not installed in this environment (pip install -r requirements.txt)")

import plotly.graph_objects as go  # noqa: E402  (must come after the importorskip above)

from src import plots  # noqa: E402
from src.data import load_config  # noqa: E402
from src.simulate import sim_garch11  # noqa: E402

CFG = load_config()
SEED = CFG["sim"]["seed"]   # seed for the simulated series

# Titles must not contain raw variable names: arch1 / garch11, "n = 1000", "R = 20", or snake_case words.
RAW_NAME = re.compile(r"\b(g?arch\d|n\s*=|R\s*=)|[A-Za-z]+_[A-Za-z]+")


def _returns(n: int = 300) -> pd.Series:
    """A simulated GARCH(1,1) return series (notebook demo parameters) on business days.

    Input: n length. Output: Series with a DatetimeIndex starting 2020-01-01.
    """
    par = CFG["sim"]["demo"]["garch11"]
    x = sim_garch11(n, par["omega"], par["alpha"], par["beta"], SEED)

    return pd.Series(x, index=pd.bdate_range("2020-01-01", periods=n))


def _forecast_frame(fallback_days: tuple = ()) -> pd.DataFrame:
    """A tiny forecast table in the forecasts_<pair>.csv layout: 2 selectors x 10 days.

    Input: fallback_days = positions (0-9) on which the hybrid selector had no valid fit.
    Output: DataFrame with date, selector, h, r2 (equal for both selectors, as in the real files), fit_status.
    """
    dates = pd.bdate_range("2023-01-02", periods=10)
    r2 = np.arange(1.0, 11.0)   # |return| = sqrt(1..10)
    rows = [dict(date=d, selector=s, h=h0 * (1 + 0.1 * i), r2=r2[i],
                 fit_status="no_valid_fit" if (s == "hybrid" and i in fallback_days) else "valid")
            for s, h0 in [("hybrid", 2.0), ("rolling_var", 3.0)] for i, d in enumerate(dates)]

    return pd.DataFrame(rows)


def _orders_frame() -> pd.DataFrame:
    """A tiny recovery_orders.csv-style table: two true models at n = 1000 plus one other length.

    Output: DataFrame (true_model, n, selector, start_order, final_order, count); each model's counts at
    n = 1000 add up to 100.
    """
    rows = [("garch11", 1000, "hybrid", "(1, 1)", "(1, 1)", 90), ("garch11", 1000, "hybrid", "(1, 1)", "(2, 1)", 10),
            ("arch1", 1000, "hybrid", "(1, 1)", "(1, 0)", 60), ("arch1", 1000, "hybrid", "(2, 0)", "(2, 0)", 40),
            ("garch11", 500, "hybrid", "(1, 1)", "(1, 1)", 100)]

    return pd.DataFrame(rows, columns=["true_model", "n", "selector", "start_order", "final_order", "count"])


GATE = pd.DataFrame({"test": ["Squared residuals: Ljung-Box, lag 5", "Squared residuals: Ljung-Box, lag 10", "ARCH-LM test, 5 lags"],
                     "p_value": [0.40, 0.03, 0.70], "passes": [True, False, True]})
SAVED = dict(exact=0.6, exact_se=0.02, nesting=0.9, nesting_se=0.01, family=float("nan"), family_se=float("nan"))
LIVE = dict(exact=0.5, exact_se=0.11, nesting=1.0, nesting_se=0.0, family=0.8, family_se=0.09)
RATES = [("exact", "exact_se", "Exact order found"), ("nesting", "nesting_se", "Chosen model contains the true one"),
         ("family", "family_se", "Right model family")]
MODEL_NAMES = {"arch1": "ARCH(1)", "garch11": "GARCH(1,1)"}
TRUE_ORDERS = {"arch1": "(1, 0)", "garch11": "(1, 1)"}

# One zero-argument builder per plots function, run by the style test below.
BUILDERS = {
    "price_line": lambda: plots.price_line(np.exp(_returns().cumsum() / 100), "EUR/USD", "US dollars per euro"),
    "return_line": lambda: plots.return_line(_returns(), "EUR/USD"),
    "return_histogram": lambda: plots.return_histogram(_returns(), "EUR/USD"),
    "correlogram_grid": lambda: plots.correlogram_grid(_returns(400), 20, 0.95),
    "gate_pvalue_bars": lambda: plots.gate_pvalue_bars(GATE, 0.05),
    "forecast_lines": lambda: plots.forecast_lines(_forecast_frame((2, 3)), ["hybrid"], "EUR/USD",
                                                   {"hybrid": "Hybrid"}, fallback_selector="hybrid"),
    "cumulative_qlike_lines": lambda: plots.cumulative_qlike_lines(
        pd.DataFrame({"hybrid": np.linspace(0, -1, 10)}, index=pd.bdate_range("2023-01-02", periods=10)),
        "Fixed GARCH(1,1)", "EUR/USD", {"hybrid": "Hybrid"}),
    "recovery_bars": lambda: plots.recovery_bars(LIVE, SAVED, RATES, 20, 500),
    "order_choice_bars": lambda: plots.order_choice_bars(
        pd.Series({"(1, 1)": 90.0, "(2, 1)": 10.0}), pd.Series({"(1, 1)": 80.0, "(1, 2)": 20.0}), 500, 20, "(1, 1)", 8),
    "order_heatmap": lambda: plots.order_heatmap(_orders_frame(), 1000, "hybrid", MODEL_NAMES, TRUE_ORDERS),
}


@pytest.mark.parametrize("name", list(BUILDERS))
def test_every_figure_has_a_plain_title_and_titled_axes(name):
    """Each builder returns a go.Figure whose title and every axis title are non-empty and free of raw names.

    Input: the builder's small test data. Output checked: Figure type, title text, no arch1 / "n = " /
    "R = " / snake_case in the title, and a non-empty title.text on every xaxis*/yaxis* of the layout.
    """
    fig = BUILDERS[name]()
    layout = fig.to_dict()["layout"]

    assert isinstance(fig, go.Figure)
    title = layout["title"]["text"]
    assert title.strip() and not RAW_NAME.search(title), title

    axes = [k for k in layout if re.fullmatch(r"[xy]axis\d*", k)]
    assert axes
    for k in axes:
        assert layout[k]["title"]["text"].strip(), f"{k} has no title"


def test_price_line_has_a_range_slider_and_exact_values_in_the_hover():
    """The rate line carries every point, a range slider underneath and a hover text with the value."""
    price = np.exp(_returns().cumsum() / 100)
    fig = plots.price_line(price, "EUR/USD", "US dollars per euro")

    np.testing.assert_allclose(fig.data[0].y, price.to_numpy())
    assert fig.layout.xaxis.rangeslider.visible is True
    assert "%{y" in fig.data[0].hovertemplate


def test_return_histogram_overlays_a_normal_curve_and_has_scale_buttons():
    """Bars plus a normal density with the data's mean and spread (area about 1), and two scale buttons.

    Input: 300 simulated returns. Output checked: trace types, curve area by the trapezoid rule within
    0.02 of 1 (the grid spans the data range, so a little tail mass is missing), the curve peak at the sample mean,
    and the linear / log buttons.
    """
    r = _returns()
    fig = plots.return_histogram(r, "EUR/USD")

    assert [type(t).__name__ for t in fig.data] == ["Histogram", "Scatter"]
    x, y = np.asarray(fig.data[1].x), np.asarray(fig.data[1].y)
    assert abs(np.trapezoid(y, x) - 1.0) < 0.02
    assert abs(x[np.argmax(y)] - r.mean()) < (x[1] - x[0]) * 1.5

    assert [b.label for b in fig.layout.updatemenus[0].buttons][0].startswith("Linear")
    assert len(fig.layout.updatemenus[0].buttons) == 2


def test_correlogram_grid_has_four_panels_and_marks_spikes_in_the_hover():
    """Each of the 4 panels has band + inside + outside traces; spike bars say "yes", others "no", and are hatched.

    Input: an AR(1) series (phi 0.8, seeded), 10 lags: the top-left ACF has a spike at lag 1 for certain.
    Output checked: 12 traces, legend entries only from the first panel, every lag drawn once, the
    outside-band customdata, the hatch pattern and the hover text.
    """
    rng = np.random.default_rng(SEED)
    e, x = rng.standard_normal(500), np.zeros(500)
    for t in range(1, 500):
        x[t] = 0.8 * x[t - 1] + e[t]   # AR(1): lag-1 autocorrelation about 0.8, far outside the band

    fig = plots.correlogram_grid(x, 10, 0.95)

    assert len(fig.data) == 12
    assert sum(bool(t.showlegend) for t in fig.data) == 3   # band, inside, outside: first panel only

    band, inside, outside = fig.data[0], fig.data[1], fig.data[2]   # top-left panel
    assert len(inside.x) + len(outside.x) == 10 and 1 in list(outside.x)
    assert set(outside.customdata) == {"yes"} and set(inside.customdata) <= {"no"}
    assert outside.marker.pattern.shape == "/" and not inside.marker.pattern.shape
    assert "Outside band" in outside.hovertemplate and "Lag" in outside.hovertemplate
    assert band.fill == "toself"


def test_gate_bars_split_pass_and_fail_and_draw_the_threshold_line():
    """Passing and failing p-values are separate bar traces; a dashed line sits at the threshold; empty input works.

    Input: three gate tests (p 0.40, 0.03, 0.70) and alpha 0.05. Output checked: bar values per trace, the
    hatch on the failing trace, the line height, and that an empty table still builds a Figure.
    """
    fig = plots.gate_pvalue_bars(GATE, 0.05)
    passes, fails = fig.data[0], fig.data[1]

    assert list(passes.y) == [0.40, 0.70] and list(fails.y) == [0.03]
    assert fails.marker.pattern.shape == "/"
    assert fig.layout.shapes[0].y0 == 0.05 and fig.layout.shapes[0].line.dash == "dash"

    empty = plots.gate_pvalue_bars(GATE.iloc[0:0], 0.05)
    assert isinstance(empty, go.Figure)


def test_forecast_lines_draw_sqrt_h_and_abs_return_and_shade_fallback_runs():
    """Lines carry sqrt(h) and |return|; fallback days become one shaded band per run, with a legend entry.

    Input: tiny table where the hybrid had no valid fit on positions 2, 3 and 7. Output checked: line
    values, 2 shaded runs (days 2-3 and day 7), the legend entry, no shading when fallback_selector is None,
    a range slider, and ValueError for an unknown selector.
    """
    fc = _forecast_frame(fallback_days=(2, 3, 7))
    dates = pd.bdate_range("2023-01-02", periods=10)
    fig = plots.forecast_lines(fc, ["hybrid", "rolling_var"], "EUR/USD", {"hybrid": "Hybrid"}, fallback_selector="hybrid")

    by_name = {t.name: t for t in fig.data}
    np.testing.assert_allclose(by_name["Realised size of the day's move (|return|)"].y, np.sqrt(np.arange(1.0, 11.0)))
    np.testing.assert_allclose(by_name["Hybrid"].y, np.sqrt(fc[fc["selector"] == "hybrid"]["h"].to_numpy()))
    assert any("fallback" in t.name for t in fig.data)

    assert len(fig.layout.shapes) == 2
    assert pd.Timestamp(fig.layout.shapes[0].x0) == dates[2] and pd.Timestamp(fig.layout.shapes[1].x0) == dates[7]
    assert fig.layout.xaxis.rangeslider.visible is True

    assert len(plots.forecast_lines(fc, ["hybrid"], "EUR/USD", {}, fallback_selector=None).layout.shapes) == 0

    with pytest.raises(ValueError):
        plots.forecast_lines(fc, ["nope"], "EUR/USD", {})


def test_cumulative_qlike_lines_have_one_line_per_selector_and_name_the_baseline():
    """One line per column with the same values, a zero line, and the baseline's plain name in the title."""
    idx = pd.bdate_range("2023-01-02", periods=10)
    diff = pd.DataFrame({"hybrid": np.linspace(0, -1, 10), "grid_bic": np.linspace(0, 0.5, 10)}, index=idx)

    fig = plots.cumulative_qlike_lines(diff, "Fixed GARCH(1,1)", "EUR/USD", {"hybrid": "Hybrid"})

    assert [t.name for t in fig.data] == ["Hybrid", "grid_bic"]   # an unnamed selector keeps its id
    np.testing.assert_allclose(fig.data[0].y, diff["hybrid"].to_numpy())
    assert "Fixed GARCH(1,1)" in fig.layout.title.text and fig.layout.shapes[0].y0 == 0


def test_recovery_bars_show_percent_with_monte_carlo_error_bars():
    """Saved and live bars are in percent, error bars are the SE in percent, NaN rates are left out.

    Input: SAVED (family NaN) and LIVE dicts. Output checked: saved trace first with 2 bars, live trace with
    3, y and error_y values times 100, the hatch on the live trace, and that live=None drops that trace.
    """
    fig = plots.recovery_bars(LIVE, SAVED, RATES, 20, 500)
    saved, live = fig.data

    assert "500" in saved.name and "20" in live.name
    assert list(saved.x) == ["Exact order found", "Chosen model contains the true one"]
    np.testing.assert_allclose(saved.y, [60.0, 90.0])
    np.testing.assert_allclose(saved.error_y.array, [2.0, 1.0])
    np.testing.assert_allclose(live.y, [50.0, 100.0, 80.0])
    np.testing.assert_allclose(live.error_y.array, [11.0, 0.0, 9.0])
    assert live.marker.pattern.shape == "/" and not saved.marker.pattern.shape

    assert len(plots.recovery_bars(None, SAVED, RATES, 20, 500).data) == 1


def test_order_choice_bars_mark_the_true_order_by_colour_label_and_legend():
    """The true order gets a green band, a "(true)" tick label and a trace named "True order"; the bar count is capped.

    Input: saved shares {(1, 1) 90, (2, 1) 10}, live shares {(1, 1) 80, (1, 2) 20}, true order (1, 1), then a
    true order that was never chosen with max_orders 2. Output checked: trace names, one shaded band, tick
    text, bar heights, the cap, the forced inclusion of the true order, and ValueError with no data.
    """
    fig = plots.order_choice_bars(pd.Series({"(1, 1)": 90.0, "(2, 1)": 10.0}),
                                  pd.Series({"(1, 1)": 80.0, "(1, 2)": 20.0}), 500, 20, "(1, 1)", 8)

    assert any("true" in t.name.lower() for t in fig.data)
    assert len(fig.layout.shapes) == 1
    assert list(fig.layout.xaxis.ticktext) == ["(1, 1) (true)", "(1, 2)", "(2, 1)"]
    assert list(fig.data[0].y) == [90.0, 0.0, 10.0] and list(fig.data[1].y) == [80.0, 20.0, 0.0]

    capped = plots.order_choice_bars(pd.Series({"(1, 1)": 60.0, "(2, 0)": 30.0, "(2, 1)": 10.0}), None, 500, 20, "(1, 0)", 2)
    assert list(capped.layout.xaxis.tickvals) == ["(1, 0)", "(1, 1)"]   # true order kept, then the most frequent

    with pytest.raises(ValueError):
        plots.order_choice_bars(None, None, None, 20, "(1, 1)", 8)


def test_order_heatmap_rows_are_percentages_and_true_orders_are_marked():
    """Every row of the heatmap sums to 100 and uses the plain model names; true orders get an outlined marker.

    Input: the tiny orders table at n = 1000. Output checked: row order from model_names, z values of the
    ARCH(1) row (60 / 0 / 40 / 0 over the sorted columns), row sums, the marker trace and its positions.
    """
    fig = plots.order_heatmap(_orders_frame(), 1000, "hybrid", MODEL_NAMES, TRUE_ORDERS)
    heat, marks = fig.data

    assert list(heat.y) == ["ARCH(1)", "GARCH(1,1)"]
    assert list(heat.x) == ["(1, 0)", "(1, 1)", "(2, 0)", "(2, 1)"]
    np.testing.assert_allclose(np.asarray(heat.z)[0], [60.0, 0.0, 40.0, 0.0])
    np.testing.assert_allclose(np.asarray(heat.z).sum(axis=1), [100.0, 100.0])

    assert "true" in marks.name.lower()
    assert list(marks.x) == ["(1, 0)", "(1, 1)"] and list(marks.y) == ["ARCH(1)", "GARCH(1,1)"]
