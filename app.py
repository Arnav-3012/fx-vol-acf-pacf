"""Streamlit dashboard (tabs: Data, Diagnose, Select, Forecast, Simulate). UI only (D-032, D-034).

This file creates widgets and calls functions in src/; it holds no statistics, no tables and no
figure code (those are src/dashboard.py and src/plots.py), and no numbers, labels or explanation text
(those are config.yaml, section `app`). Run it from the project root:
    .atsa-project/bin/python -m streamlit run app.py

No look-ahead: the sidebar as-of date cuts the data once, and the Data, Diagnose and Select tabs
only ever see the cut series. The Forecast tab shows saved CSVs and ignores the slider.
Rules are frozen (D-023): nothing here can change them.

Streamlit re-runs this whole script top to bottom on every widget change, and st.tabs draws all
five tabs on every run. So anything slow is either cached (st.cache_data, keyed on the widget values)
or sits behind a button. Every figure is a Plotly figure shown with st.plotly_chart(fig, width="stretch")
(`width` is the supported keyword in the installed streamlit 1.65.0, read from its source).
"""
import streamlit as st

from src import plots
from src.baselines import grid_bic
from src.dashboard import (asof_bounds, diagnostic_table, explain_values, grid_comparison, live_recovery,
                           order_shares, rate_specs, rates_table, read_result, render_text, result_mtime,
                           results_table, rule_readout, saved_order_counts, saved_recovery_row,
                           selection_tables, slice_asof, stationarity_table, step_table, summary_table,
                           true_order_label)
from src.data import load_config, load_fx, to_log_returns
from src.evaluate import cumulative_qlike_diff
from src.selector import select_and_fit

# Config is read once per script run (a small YAML file). The cached functions below read it
# themselves, so their cache keys are only the widget values (pair, date, ...), not the whole config.
cfg = load_config()
app = cfg["app"]


# ---------------------------------------------------------------------------------------
# Cached calls: each is one src/ call, cached on the widget values it depends on.
# ---------------------------------------------------------------------------------------

@st.cache_data(show_spinner="Loading prices ...")
def load_series(pair: str):
    """Price and log-return (x100) Series of one pair, from the cached FRED CSV.

    Input: FRED series id. Output: (price, returns). Cached on the pair.
    """
    c = load_config()

    # Prices from data/raw (downloaded once if absent), returns = 100 * diff(log price).
    price = load_fx(pair, c["start"], cfg=c)

    return price, to_log_returns(price)


@st.cache_data(show_spinner="Running the selector (rules, fit, gate, escalation) ...")
def run_selection(pair: str, asof: str):
    """select_and_fit on the returns up to the as-of date. Input: pair, ISO date. Cached on both."""
    _, returns = load_series(pair)

    # Cut first, fit second: the selector never sees a return dated after the as-of day.
    return select_and_fit(slice_asof(returns, asof).to_numpy(), load_config())


@st.cache_data(show_spinner="Fitting the full (p, q) grid, this can take a while ...")
def run_grid(pair: str, asof: str):
    """baselines.grid_bic on the returns up to the as-of date. Input: pair, ISO date. Cached on both."""
    _, returns = load_series(pair)

    return grid_bic(slice_asof(returns, asof).to_numpy(), load_config())


@st.cache_data(show_spinner="Reading saved results ...")
def read_csv(name: str, mtime):
    """A results/ CSV as a DataFrame (None if missing).

    Input: file name and its modified time. `mtime` is not used in the body; it is only part of the
    cache key, so a rewritten or newly created file is re-read instead of served from the cache.
    """
    return read_result(load_config(), name)


@st.cache_data(show_spinner="Running the live Monte Carlo ...")
def run_live(true_model: str, n: int, R: int):
    """Hybrid order-recovery experiment on R simulated series. Input: model, n, R. Cached on all three."""
    return live_recovery(true_model, n, R, load_config())


def saved_csv(name: str):
    """Cached read of results/<name>; the file's modified time is part of the cache key."""
    return read_csv(name, result_mtime(cfg, name))


# ---------------------------------------------------------------------------------------
# Small rendering helpers (widgets only)
# ---------------------------------------------------------------------------------------

def show_missing(name: str) -> None:
    """Tell the user a results file is absent and show the command that writes it."""
    st.warning(f"results/{name} not found.")
    st.code(app["missing_csv_command"], language="bash")


def show_chart(fig) -> None:
    """Show a Plotly figure at the full width of its container."""
    st.plotly_chart(fig, width="stretch")


def show_table(df) -> None:
    """Show a DataFrame with plain column headings, one-decimal percentages and 4-digit numbers.

    Headings come from app.columns, percent columns (app.percent_columns, already scaled to 0-100) get one
    decimal, other float columns get app.number_format. The index is hidden.
    """
    config = {}

    for col in df.columns:
        label = app["columns"].get(col, col)

        if col in app["percent_columns"]:
            config[col] = st.column_config.NumberColumn(label, format="%.1f")
        elif df[col].dtype.kind == "f":
            config[col] = st.column_config.NumberColumn(label, format=app["number_format"])
        else:
            config[col] = st.column_config.Column(label)

    st.dataframe(df, hide_index=True, column_config=config)


def fill_explain(box, key: str, values: dict) -> None:
    """Fill the "How to read this tab" expander with the four config parts, numbers filled from `values`."""
    ex = app["explain"]

    with box:
        for part, heading in ex["parts"].items():
            st.markdown(f"**{heading}.** {render_text(ex[key][part], values)}")


# ---------------------------------------------------------------------------------------
# Sidebar: pair, as-of date, glossary
# ---------------------------------------------------------------------------------------

# set_page_config must be the first Streamlit command on the page.
st.set_page_config(page_title=app["page_title"], layout="wide")
st.title(app["page_title"])

# Pair selector: the ids come from config `pairs`, the plain names and units from app.pair_labels / pair_units.
pair = st.sidebar.selectbox("Pair", cfg["pairs"],
                            format_func=lambda p: f"{app['pair_labels'].get(p, p)} ({app['pair_units'].get(p, '')})")
label, unit = app["pair_labels"].get(pair, pair), app["pair_units"].get(pair, "quoted units")
names = app["selector_labels"]

# Full history of the chosen pair; the slider range comes from it (never fewer than min_obs returns).
price, returns = load_series(pair)
first_date, last_date = asof_bounds(returns, app["min_obs"])

# As-of date: default = the last date, i.e. "use everything we have".
asof = st.sidebar.slider("As-of date", min_value=first_date, max_value=last_date, value=last_date,
                         format="YYYY-MM-DD")
asof_text = asof.isoformat()  # text form is a stable cache key

# The one and only cut: everything below in Data, Diagnose and Select uses these two series.
price_a, returns_a = slice_asof(price, asof), slice_asof(returns, asof)
st.sidebar.caption(f"{len(returns_a)} returns, {returns_a.index[0].date()} to {returns_a.index[-1].date()}")
st.sidebar.info(f"Rules frozen, {cfg['frozen']['decision_id']}")

# Glossary of the terms used on the tabs (text from config).
with st.sidebar.expander(app["glossary_title"]):
    for item in app["glossary"]:
        st.markdown(f"**{item['term']}.** {item['text']}")

# Saved results, read once (cached on the file's modified time).
loss_all, dm_all = saved_csv("loss_table.csv"), saved_csv("dm_table.csv")
recovery_all, orders_all = saved_csv("recovery_table.csv"), saved_csv("recovery_orders.csv")
diagnostic_all = saved_csv("diagnostic_arch1.csv")
fc = saved_csv(f"forecasts_{pair}.csv")

tab_data, tab_diag, tab_select, tab_fc, tab_sim = st.tabs(["Data", "Diagnose", "Select", "Forecast", "Simulate"])

# The "How to read this tab" boxes are created at the top of each tab and filled at the very end,
# when every number they quote (from CSVs, data, the live run) is known.
boxes = {}


# ---------------------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------------------

with tab_data:
    boxes["data"] = st.expander(app["explain"]["title"])

    # Rate with a range slider, then the daily return, then the histogram against a normal curve.
    show_chart(plots.price_line(price_a, label, unit))
    show_chart(plots.return_line(returns_a, label))
    show_chart(plots.return_histogram(returns_a, label))

    # One-row summary: n, mean, std, skew, excess kurtosis, zero-return count.
    st.subheader("Summary of the daily returns")
    show_table(summary_table(returns_a))

    # ADF / KPSS on price and on returns.
    st.subheader("Is the series stationary? ADF and KPSS tests")
    show_table(stationarity_table(price_a, returns_a, cfg))
    st.caption(app["captions"]["data"])


# ---------------------------------------------------------------------------------------
# Diagnose
# ---------------------------------------------------------------------------------------

with tab_diag:
    boxes["diagnose"] = st.expander(app["explain"]["title"])

    # ACF/PACF of returns and squares, with the shaded 95% band.
    show_chart(plots.correlogram_grid(returns_a, cfg["eda"]["nlags"], cfg["band_confidence"]))

    # The test numbers behind the plots (same lags as the gate).
    st.subheader("Ljung-Box and ARCH-LM tests")
    show_table(diagnostic_table(returns_a, cfg))

    # What the frozen rules read off the correlograms, in words (the rules' reason strings, unchanged).
    readout = rule_readout(returns_a, cfg)
    st.subheader("What the rules read")
    st.markdown(f"**Mean.** {readout['mean']['text']}")
    st.caption(f"Rule reason: `{readout['mean']['reason']}`")
    st.markdown(f"**Variance.** {readout['variance']['text']}")
    st.caption(f"Rule reason: `{readout['variance']['reason']}`")
    st.caption(app["captions"]["diagnose"])


# ---------------------------------------------------------------------------------------
# Select
# ---------------------------------------------------------------------------------------

with tab_select:
    boxes["select"] = st.expander(app["explain"]["title"])

    # Run (or fetch from cache) the full selector on data <= as-of, then split it into tables.
    result = run_selection(pair, asof_text)
    tables = selection_tables(result, cfg)

    # Headline numbers first.
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Mean model", result["mean_spec"]["kind"])
    col_b.metric("Final order (p, q)", str(result["order"]))
    col_c.metric("Models fitted", result["models_fitted"])

    # Say plainly when the result is not a trustworthy fit.
    if result["no_valid_fit"]:
        st.error("No valid fit: every fitted model was rejected. The order shown is the rule's proposal, not a fitted model.")
    elif result["flagged"]:
        st.warning("Flagged: the gate still failed after escalation; this is the lowest-BIC valid fit.")

    # Step-by-step trace with pass / fail icons, then the gate p-values as a bar chart.
    st.subheader("What the selector did, step by step")
    show_table(step_table(result, cfg))

    # The gate tests the residuals of a VALID model. With no valid fit there are no p-values, so an
    # empty chart would only show bare axes; say why there is nothing to draw instead.
    if result["no_valid_fit"]:
        st.info("No gate chart: every model was rejected before the diagnostic gate could test it "
                "(see steps 4 and 5 above, and the escalation log below for each fit's persistence).")
    else:
        show_chart(plots.gate_pvalue_bars(tables["gate"], cfg["gate"]["alpha"]))

    # Every model fitted, the chosen model's parameters, and the summary.
    st.subheader("Every model fitted (the escalation log)")
    show_table(tables["log"])
    st.subheader("Parameters of the chosen model")
    show_table(tables["params"])
    st.subheader("Summary")
    show_table(tables["summary"])

    # The full grid costs many fits, so it runs only on a click; the result stays visible while the
    # pair and date stay the same (session_state remembers which settings were clicked).
    key = (pair, asof_text)
    if st.button("Compare with full-grid BIC"):
        st.session_state["grid_key"] = key

    if st.session_state.get("grid_key") == key:
        show_table(grid_comparison(result, run_grid(*key), cfg))

    st.caption(app["captions"]["select"])


# ---------------------------------------------------------------------------------------
# Forecast (saved CSVs only, nothing recomputed)
# ---------------------------------------------------------------------------------------

with tab_fc:
    boxes["forecast"] = st.expander(app["explain"]["title"])

    if fc is None:
        show_missing(f"forecasts_{pair}.csv")
    else:
        # Which selectors to draw (legend clicks also toggle them) and whose fallback days to shade.
        ids = fc["selector"].unique().tolist()
        default = [s for s in app["forecast_default_selectors"] if s in ids]
        chosen = st.multiselect("Selectors to draw", ids, default=default, format_func=lambda s: names.get(s, s))
        shade_default = app["forecast_fallback_default"]
        shade = st.selectbox("Shade the days this selector used the rolling-variance fallback",
                             [None] + ids, index=ids.index(shade_default) + 1 if shade_default in ids else 0,
                             format_func=lambda s: "No shading" if s is None else names.get(s, s))

        show_chart(plots.forecast_lines(fc, chosen, label, names, fallback_selector=shade, order=ids))

        # Cumulative loss difference against the baseline named in evaluate.figure_baseline.
        base = cfg["evaluate"]["figure_baseline"]
        show_chart(plots.cumulative_qlike_lines(cumulative_qlike_diff(fc, cfg), names.get(base, base), label,
                                                names, order=ids))

    # The pair's rows of the two summary tables (all pairs live in one file each), with plain labels.
    for name, title, table in [("loss_table.csv", "Losses of each selector (QLIKE is the headline; lower is better)", loss_all),
                               ("dm_table.csv", "Diebold-Mariano tests: is one selector better than another?", dm_all)]:
        st.subheader(title)

        if table is None:
            show_missing(name)
        else:
            show_table(results_table(table, pair, cfg))

    # Limitations: proxy noise, no multiplicity correction, and the INR fallback note for that pair.
    st.caption(app["captions"]["forecast"])
    if pair in app["pair_notes"]:
        st.caption(app["pair_notes"][pair])


# ---------------------------------------------------------------------------------------
# Simulate
# ---------------------------------------------------------------------------------------

with tab_sim:
    boxes["simulate"] = st.expander(app["explain"]["title"])
    sim = app["simulate"]
    models = list(cfg["recovery"]["models"])
    lengths = cfg["sim"]["n"]

    # Three controls: which true model, how long a series, how many replications (capped for live use).
    col_m, col_n, col_r = st.columns(3)
    true_model = col_m.selectbox("True model", models, index=models.index(sim["default_model"]),
                                 format_func=lambda m: app["model_labels"].get(m, m))
    n = col_n.selectbox("Series length (days)", lengths, index=lengths.index(sim["default_n"]))
    R = col_r.number_input("Number of simulated series (live)", min_value=1, max_value=sim["max_live_R"],
                           value=sim["default_R"], step=1)
    true_order = true_order_label(cfg, true_model)
    st.caption(f"The i-th simulated series uses random seed {cfg['eval']['seed_base']} + i (fixed in the project "
               f"configuration, so runs are repeatable). Selector: hybrid with the frozen rules. True order: {true_order}.")

    # Same pattern as the grid button: run on click, keep showing while the settings stay the same.
    sim_key = (true_model, int(n), int(R))
    if st.button("Run live experiment"):
        st.session_state["sim_key"] = sim_key

    live_metrics, live_counts = run_live(*sim_key) if st.session_state.get("sim_key") == sim_key else (None, None)

    # The saved big run for the same model and length, to compare with the small live one.
    saved_row = (saved_recovery_row(recovery_all, true_model, int(n), sim["saved_selector"])
                 if recovery_all is not None else None)
    saved_counts = (saved_order_counts(orders_all, true_model, int(n), sim["saved_selector"])
                    if orders_all is not None else None)
    if saved_counts is not None and saved_counts.empty:
        saved_counts = None

    # Numbers for the explanation texts (and the live note) come from the CSVs and the live run.
    values = explain_values(cfg, pair, returns_a,
                            dict(diagnostic=diagnostic_all, recovery=recovery_all, loss=loss_all, dm=dm_all),
                            live_metrics=live_metrics, live_R=int(R) if live_metrics else None, saved_row=saved_row)

    if recovery_all is None:
        show_missing("recovery_table.csv")
    if live_metrics is None and saved_row is None:
        st.info("Press the button to run a live experiment.")
    else:
        # Chart 1: exact / nesting / family, saved run next to the live run, with error bars.
        saved_R = int(saved_row["R"]) if saved_row else None
        show_chart(plots.recovery_bars(live_metrics, saved_row, rate_specs(cfg, sim["chart_rates"]), int(R), saved_R))
        if live_metrics is not None:
            st.info(render_text(sim["live_note"], values))

    # Chart 2: which order was chosen, in percent of runs, true order highlighted.
    if live_counts is not None or saved_counts is not None:
        show_chart(plots.order_choice_bars(
            order_shares(saved_counts) if saved_counts is not None else None,
            order_shares(live_counts) if live_counts is not None else None,
            int(saved_counts["count"].sum()) if saved_counts is not None else None, int(R),
            true_order, sim["max_orders"]))

    # Chart 3: heatmap of every true model against the order chosen (saved run, this series length).
    if orders_all is None:
        show_missing("recovery_orders.csv")
    else:
        true_orders = {m: true_order_label(cfg, m) for m in models}
        show_chart(plots.order_heatmap(orders_all, int(n), sim["saved_selector"], app["model_labels"], true_orders))

    # All measures as tables (plain names, percent with one decimal).
    live_col, saved_col = st.columns(2)
    with live_col:
        st.subheader("Live run: all measures")
        if live_metrics is None:
            st.info("Press the button to run.")
        else:
            show_table(rates_table(live_metrics, cfg))
    with saved_col:
        st.subheader("Saved run: all measures")
        if saved_row is None:
            st.info("No saved row for this model and length.")
        else:
            show_table(rates_table(saved_row, cfg))

    st.caption(app["captions"]["simulate"])


# ---------------------------------------------------------------------------------------
# "How to read this tab": filled last, now that every number is known
# ---------------------------------------------------------------------------------------

for tab_key, box in boxes.items():
    fill_explain(box, tab_key, values)
