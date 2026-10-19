# Architecture

Module contracts are design, adjustable via docs/decision.md.

## Structure
```
fx-vol-acf-pacf/
  CLAUDE.md  README.md  config.yaml  requirements.txt  .gitignore  app.py
  docs/        logs.md phaseplan.md decision.md mistakes.md architecture.md
               wiki/ (teaching wiki, D-035: 00-index..05-experiments, phases/, concepts/, code/)
  data/        raw/ processed/
  src/         __init__ data stat_tests correlogram rules selector
               baselines simulate forecast evaluate plots dashboard
  notebooks/
  tests/       __init__
  report/
```

## Layers
- Data: data.py
- Statistics: stat_tests.py, correlogram.py
- Decision: rules.py, selector.py
- Evaluation: baselines.py, forecast.py, evaluate.py, simulate.py
- Presentation: app.py, plots.py, dashboard.py, notebooks, report

## Data flow
prices -> log returns -> ADF/KPSS -> mean rule -> ARCH check -> variance rule -> fit -> gate -> escalate/refit -> rolling forecast -> QLIKE/DM

## Module contracts
- data.load_config(path="config.yaml") -> dict
- data.load_fx(series_id, start, end=None, cfg=None) -> Series (cached at paths.raw_dir)
- data.to_log_returns(price) -> Series
- stat_tests.adf_kpss(x, alpha=0.05) -> dict
- stat_tests.ljung_box(x, lags, model_df=0) -> DataFrame[lag, lb_stat, lb_pvalue]
- stat_tests.arch_lm(x, nlags) -> dict
- correlogram.acf_pacf_band(x, nlags, confidence=0.95) -> dict(acf, pacf, band, n)
- correlogram.significant_lags(values, band) -> list[int]
- rules.mean_order_rule(returns, cfg) -> int
- rules.variance_order_rule(resid, cfg) -> (p, q, reason)
- selector.select_and_fit(returns, cfg) -> SelectionResult(m, p, q, dist, fit, gate_passed, gate_pvalues, models_fitted, path)
- baselines.* each (train_returns, horizon) -> float
- simulate.sim_garch11(n, mu, omega, alpha, beta, burn, seed) -> (returns, true_var)
- forecast.rolling_refit_forecast(returns, selector_fn, refit_every, start) -> DataFrame
- evaluate.qlike, evaluate.mse, evaluate.diebold_mariano(l_a, l_b, lag) -> dict

## Config keys added in P1
- fred.url_template (unverified), pairs_optional, eda.nlags, eda.sig_window, paths.raw_dir, paths.processed_dir
- stat_tests.py is the module name (no rename needed; already stat_tests in the structure).

## P2 contracts (supersede the earlier rules/selector/simulate lines)
- simulate.sim_garch11(n, omega, alpha, beta, seed, burn=500, dist="normal", nu=8.0) -> ndarray (zero-mean shocks, length n; raises if alpha+beta>=1)
- simulate.sim_arch1(n, omega, alpha, seed, burn=500, dist="normal", nu=8.0) -> ndarray
- rules.mean_order_rule(x, cfg) -> dict(m, reason)
- rules.variance_order_rule(resid, cfg) -> dict(stop_constant_variance, start_order=(p, q), reason)
- selector.select_and_fit(returns, cfg) -> dict(mean_spec, order, dist, params, persistence, bic, gate=dict(lb_p, lm_p, passed), escalation_log, models_fitted, flagged, reason)
- Private in selector: _mean_resid, _fit, _persistence, _valid, _gate
- stat_tests: adfuller and het_arch called with result_object=False.
- Dependencies of P2: rules -> correlogram, stat_tests; selector -> rules, stat_tests, arch.

## Config keys added in P2
- mean.alpha, variance.corr_lags, variance.fade_lag
- sim.burn, sim.dist, sim.test.{n, n_noise, n_seeds, min_share, garch11, arch1} (tests only)
- pairs now includes DEXINUS; pairs_optional is empty
- Reused: escalation.cap (max p and q), gate.*, fit.dist

## P2b changes
- selector.select_and_fit result gains `mean_resid_lb_p` (float): Ljung-Box(mean.lb_lags) p on the mean-model residuals, report only, not used in any decision.
- Start order is read from escalation_log[0]["order"] (no separate key).
- Config: sim.demo.{n, garch11, arch1} for notebooks/02_selector_sim.ipynb.
- New notebook: notebooks/02_selector_sim.ipynb (cell A real data, cell B simulated, closing markdown). Contains a small presentation helper summary_row.
- requirements.txt: + nbconvert, ipykernel (D-017).

## P3a changes
- config.yaml: calibration.{seed_base, R, n, n_jobs, models, truth, candidates.{fade, mean_trigger}}, eval.seed_base, fit.persistence_tol, mean.trigger (spike_or_lb | lb_only), variance.fade_max_spikes, paths.results_dir. Defaults (spike_or_lb, 0) reproduce the pre-P3a rules.
- rules.mean_order_rule reads mean.trigger; rules.variance_order_rule counts ACF-of-squares spikes in fade_lag..corr_lags and compares with fade_max_spikes. Signatures unchanged.
- selector._valid(params, tol) -> (bool, why): rejects persistence >= 1 - tol. escalation_log entries gain `persistence`. select_and_fit result gains `no_valid_fit` (bool). Every fit rejected -> no_valid_fit=True, no exception (D-019).
- simulate.py new: simulate_true_model(true_model, n, seed, cfg) -> ndarray; order_recovery_experiment(true_model, n, R, seed_base, cfg) -> DataFrame[seed, m, p, q, dist, models_fitted, flagged, no_valid_fit]; recovery_summary(df, true_model, cfg) -> dict; apply_candidates(cfg, fade=None, mean_trigger=None) -> cfg copy; check_seed_ranges(cfg); calibration_table(cfg) -> DataFrame; summarise_calibration(table) -> (fade_df, mean_df). Dependency: simulate -> selector (new), joblib, pandas.
- Notebook 02 gains cells s04 (markdown) and s05 (calibration, writes results/calibration.csv).
- Tests: tests/test_p3a.py.
- arch persistence constraint (read from installed source, not executed): .atsa-project/lib/python3.13/site-packages/arch/univariate/volatility.py lines 1106-1123, GARCH.constraints(): the comment at line 1112 says "sum(alpha) + 0.5 sum(gamma) + sum(beta) < 1", and the code sets a[k_arch + 1, 1:] = -1.0 (line 1120) with b[k_arch + 1] = -1.0 (line 1123), i.e. -sum(params[1:]) + 1 >= 0, so sum <= 1 (non-strict, which allows the boundary). ARCH is a subclass of GARCH (class ARCH(GARCH), line 2014) and inherits it. That the optimiser actually ends on the boundary for the INR fit is unverified (fitted value was never logged).

## P3a calibration extension (D-021)
- config.yaml: calibration.candidates.fade gains F3: 3, F4: 5 (F0-F2 and all defaults unchanged).
- simulate._one_replication / order_recovery_experiment: rows gain start_p, start_q (= escalation_log[0]["order"]).
- simulate.calibration_table(cfg) now returns (table, orders) (was a single DataFrame). Mean candidates are scored on iid, arch1, garch11 and ar1_garch11 with the same seeds as the fade runs.
- simulate.order_counts(df) -> DataFrame[start_order, final_order, count] (new).
- simulate.summarise_calibration(table) -> (fade_df, mean_df): fade_df gains garch11_ge_090; mean_df columns are now any_ar_<model> for the four models plus ar1_detect (was iid_false_ar, ar1_detect).
- Notebook cell s05 writes results/calibration.csv and results/calibration_orders.csv.

## P3a-3 cut-off read calibration (D-022)
- config.yaml: variance.cutoff_rule (last_significant = C0, default | contiguous = C1); calibration.models.arch2 {omega, alphas} and calibration.truth.arch2 (calibration-only, not in the P3 true grid); calibration.candidates.cutoff {C0, C1}; calibration.cutoff_grid {fade: [F2, F3, F4], models: [arch1, arch2, garch11], margin: 0.03}.
- rules.pacf_cutoff(pacf_spikes, max_p, rule) -> int (new, pure). variance_order_rule calls it; signature and defaults unchanged (C0 reproduces the old max-of-small-spikes read).
- simulate.sim_arch(n, omega, alphas, seed, burn=500) -> ndarray (new; raises if sum(alphas) >= 1, omega <= 0, a negative alpha or no alphas). simulate_true_model accepts "arch2".
- simulate.apply_candidates(cfg, fade=None, mean_trigger=None, cutoff=None) (new keyword cutoff).
- simulate.cutoff_calibration_table(cfg) -> (table[cutoff, fade, true_model, exact_order, flagged_rate], orders[cutoff, fade, true_model, start_order, final_order, count]); simulate.summarise_cutoff(table, cfg) -> DataFrame (score, garch11_ge_090, gain_vs_C0F3, clears_margin; reports only, does not pick).
- Notebook 02 gains cell s06 (writes results/calibration_cutoff.csv and results/calibration_cutoff_orders.csv); s04 text gets one line.
- Tests: tests/test_p3a.py +8 (sim_arch x3, pacf_cutoff x2, default reproduces rule x2, switch and grid shape).

## Frozen rules (D-023)
- config.yaml top-level `frozen: {date: "2026-10-08", decision_id: D-023}` (new key, read by tests only).
- Frozen values, now the config defaults: variance.cutoff_rule = last_significant (C0), variance.fade_max_spikes = 3 (F3), mean.trigger = lb_only (M1), fit.persistence_tol = 1.0e-6.
- calibration.candidates keeps F0-F2, F4, M0, C1, commented "calibration only"; notebook 02 still reproduces the calibration with them. apply_candidates is unchanged and still overrides on a copy.
- Behaviour change: default select_and_fit / variance_order_rule / mean_order_rule now run F3 and M1 (before: F0, M0). No signature changed, no code in src/ touched.
- tests/test_frozen.py pins the four values and the frozen marker. tests/test_p3a.py::test_apply_candidates_does_not_mutate_input now expects F3/M1 as the untouched defaults.
- Change policy in decision.md D-023.

## P3(a) forecast layer (D-024 to D-027)
- Supersedes the earlier lines `baselines.* each (train_returns, horizon) -> float` and `forecast.rolling_refit_forecast(returns, selector_fn, refit_every, start)`.
- baselines.py: every selector is `fit_forecast(train, cfg) -> dict(h_next, order, models_fitted, flagged, no_valid_fit, spec)`; spec = dict(m, order, dist, params) or None. Functions: rolling_var, fixed_garch11, acf_only, grid_bic, hybrid; registry `SELECTORS` (name -> function). Helpers: rolling_variance(x, window) -> float, next_variance(x, spec) -> float. Imports the private selector helpers _fit, _mean_resid, _valid (not changed). acf_only returns no escalation_log.
- forecast.py: rolling_refit_forecast(returns: Series, selector_name, cfg) -> DataFrame[date, pair, selector, h, r2, order, models_fitted, flagged, no_valid_fit, refit_date]; n_test_days(n, cfg); pairs_to_run(cfg); run_pair(pair, cfg) (writes results/forecasts_<pair>.csv); run_all(cfg). Private _run_block (joblib task: one refit block). Dependencies: forecast -> baselines, data, joblib; baselines -> rules, selector, arch.
- Config: forecast.{refit_every 20, horizon 1, smoke, smoke_days 100, n_jobs -1}. Window (baselines.rolling_window 60) and grid (baselines.grid_max 5) stay under `baselines`.
- arch calls (read from installed source .atsa-project/lib/python3.13/site-packages/arch/univariate/base.py, NOT executed): ARCHModel.fix(self, params, first_obs=None, last_obs=None) at line 526 returns ARCHModelFixedResult; its docstring says parameters are not checked against model constraints (line 553). ARCHModelFixedResult.forecast(self, params=None, horizon=1, start=None, align="origin", method="analytic", ...) at line 1444 (params=None uses the fixed params, line 1559). ARCHModelForecast.variance (a DataFrame) at line 2224. Docstring: the row for position t holds the forecast made with y[:t] (align="origin"). Assumption, unverified until run: with start=None the frame has one row, so `.variance.to_numpy()[-1, 0]` is the forecast from the last observation; and the order of res.params.to_dict() equals the model's parameter order expected by fix.
- Tests: tests/test_forecast.py (7 test functions; look-ahead is parametrised over 3 selectors, so 9 test cases by my count, unverified).
- Notebook: notebooks/03_results.ipynb (calls run_all; one small groupby table for display).

## P3(b) evaluation layer (D-028)
- evaluate.py (supersedes the earlier line `evaluate.qlike, evaluate.mse, evaluate.diebold_mariano(l_a, l_b, lag) -> dict`):
  - qlike(h, r2) -> ndarray, mse(h, r2) -> ndarray (per-day losses; raise on h <= 0, r2 < 0, non-finite, shape mismatch); LOSSES = {qlike, mse}.
  - nw_lag(T, cfg) -> int; newey_west_lrv(d, L) -> float.
  - diebold_mariano(loss_a, loss_b, L=None, cfg=None) -> dict(mean_diff, dm, p, L, status); status ok | identical | nonpositive_lrv. cfg=None loads config.yaml.
  - dm_table(forecasts, cfg) -> DataFrame[pair, loss, sample, A, B, mean_diff, dm, p, L, status, n_days] (n_days is an addition to the specified columns); status can also be too_few_days.
  - loss_table(forecasts, cfg) -> DataFrame[pair, selector, qlike, mse, models_fitted, refits, escalation_rate, modal_order_share, agree_grid, fallback_share, valid_day_qlike].
  - cumulative_qlike_diff(fc, cfg) -> DataFrame (date index, one column per selector except the baseline); max_abs_h_diff(new, old) -> float.
  - `forecasts` = dict pair -> stacked forecast DataFrame. Dependency: evaluate -> data (load_config), scipy.stats.norm.
- forecast.COLUMNS gains refit_models, fit_status, reject_reason, rejected_persistence (repeated on every row of a refit block). Rows built with fit.get(...), so a selector dict without the two reject keys still works.
- baselines: every fit_forecast dict gains reject_reason (str) and rejected_persistence (float). New private _reject_summary(rejects); _pack(..., rejects=()); imports selector._persistence. No selection logic changed.
- Config: evaluate.{primary_loss, losses, samples, comparisons, grid_selector, figure_baseline, dm.{lag_c, lag_ref, lag_exp, min_days}, test.{n, shift, noise_sd}}.
- Outputs (written by notebooks/03_results.ipynb, cells r03-r05): results/loss_table.csv, results/dm_table.csv, one figure. Regression input: results/forecasts_<pair>_p3a.csv (copied by the user before the rerun).
- Tests: tests/test_evaluate.py (new; 14 test functions, 21 cases with parametrisation, by my count, unverified) and 2 tests appended to tests/test_forecast.py.

## P3(b2) robustness and observation changes (D-029)
- evaluate.dm_table: output gains dm_L20, p_L20 (appended after n_days): the DM test with L = forecast.refit_every; NaN unless the primary status is ok and L < T. The primary dm, p, L are unchanged.
- evaluate.loss_table: escalation_rate is NaN for evaluate.grid_selector; agree_grid counts only refits where both selectors had fit_status valid; new column n_both_valid (after agree_grid). Column order now: pair, selector, qlike, mse, models_fitted, refits, escalation_rate, modal_order_share, agree_grid, n_both_valid, fallback_share, valid_day_qlike.
- evaluate.block_qlike_diff(fc, cfg) -> DataFrame[refit_date, <A>_order, <A>_dist, <B>_order, n_days, block_qlike_diff, share_of_total] (new; A, B = evaluate.block_compare; one pair's table; needs the dist column).
- forecast.COLUMNS gains `dist` (last column); value = fit["spec"]["dist"], "" when spec is None (rolling_var or no_valid_fit). baselines.py not touched.
- Config: evaluate.block_pair (DEXINUS), evaluate.block_compare ([hybrid, fixed_garch11]).
- Outputs: results/dm_table.csv (2 new columns), results/loss_table.csv (1 new column), results/inr_hybrid_vs_fixed.csv (new). Regression input unchanged: results/forecasts_<pair>_p3a.csv.
- Tests: tests/test_evaluate.py (loss_table and dm_table tests updated for the new definitions; +3 tests), tests/test_forecast.py (+1 test).

## P3(c) order-recovery experiment (D-030)
- simulate.py (all existing functions keep their behaviour; sim_garch11, sim_arch1, sim_arch, simulate_true_model untouched):
  - sim_garch(n, omega, alphas, betas, seed, burn=500, dist="normal", nu=8.0) -> ndarray (general hand-rolled GARCH(p, q), p = len(alphas), q = len(betas); raises on omega <= 0, a negative coefficient or persistence >= 1; "t" scaled to unit variance); private _push(buf, value).
  - true_spec(par) -> dict(m, p, q); simulate_recovery_model(true_model, n, seed, cfg) -> ndarray (omega = 1 - persistence; optional AR(1) phi).
  - _one_replication(true_model, n, seed, cfg, selector="hybrid", model_set="calibration") and order_recovery_experiment(true_model, n, R, seed_base, cfg, selector="hybrid", model_set="calibration") (extended; defaults reproduce the old calls). model_set "recovery" reads recovery.models and recovery.n_jobs. Result gains gate_passed (NaN for grid_bic); grid_bic rows have start_p / start_q NaN. Dependency added: simulate -> baselines.grid_bic, rules.mean_order_rule.
  - order_counts: start_order is "n/a" when start_p is all NaN (grid_bic).
  - nests_true(final_p, final_q, true_p, true_q), family_match(start_q, true_q), mc_se(rate, R), recovery_metrics(df, true_model, cfg, selector) -> dict (exact, nesting, family, any_ar_rate, gate_pass, escalation_rate, flagged, no_valid_fit, each with a _se; plus mean_fits), recovery_table(cfg) -> (table, orders), order_count_matrix(orders, true_model, n, selector, pmax, qmax) -> DataFrame.
- Config: recovery.{smoke, smoke_R, smoke_n, grid_n, n_jobs, models, test}. Lengths come from sim.n, R from sim.R, seeds from eval.seed_base.
- Outputs (written by notebooks/03_results.ipynb cells r08-r09): results/recovery_table.csv, results/recovery_orders.csv, results/run_time_recovery.txt, two figures (hybrid and grid_bic final-order heatmaps at n = recovery.grid_n[0]).
- Tests: tests/test_recovery.py (new, 16 tests by my count, unverified).
- Observation from the P3(b2) run (INR, rejected_persistence per refit): values above 1 occur (hybrid max 1.0011, grid_bic max 1.0018, acf_only / fixed_garch11 max 1.0001), so arch's "sum <= 1" constraint (see P3a changes) is not enforced exactly by the optimiser. The earlier note that the sum is constrained to <= 1 holds only to optimiser tolerance. _valid still rejects them (>= 1 - tol); nothing changed.

## P3(c2) post-hoc diagnostic: ARCH(1) recovery versus n (D-031)
- simulate.py gains a last section; nothing existing is edited except the module docstring and two imports (itertools, correlogram.acf_pacf_band / significant_lags). Dependency added inside the repo: simulate -> correlogram. No new package.
  - diagnostic_model_name(alpha) -> str ("arch1_a0.4"); diagnostic_cfg(cfg) -> deep copy whose recovery.models also holds one {alphas: [alpha], betas: []} per diagnostic.alphas (omega = 1 - alpha is set by simulate_recovery_model, as in D-030).
  - seed_ranges(cfg) -> dict name -> (lo, hi) for calibration, eval, diagnostic; check_diagnostic_seed_ranges(cfg) raises ValueError if any pair overlaps. check_seed_ranges (calibration vs eval) is unchanged.
  - pacf_squares_spike(x, cfg) -> bool: demean, square, acf_pacf_band(.., variance.corr_lags, band_confidence), any significant PACF lag in diagnostic.lag_min..lag_max. Raises if lag_max > variance.corr_lags. No model is fitted.
  - _spike_replication(true_model, n, seed, cfg) -> bool (private, joblib task); false_spike_rate(true_model, n, R, seed_base, cfg) -> float (uses recovery.n_jobs).
  - diagnostic_arch1_table(cfg) -> DataFrame[alpha, n, R, exact, nesting, false_spike_rate, exact_se, nesting_se, false_spike_se]. exact, nesting and their SEs come from order_recovery_experiment(model_set="recovery") and recovery_metrics unchanged (hybrid, frozen rules).
  - diagnostic_verdict(table, cfg) -> dict(change_exact_low_alpha, change_exact_high_alpha, change_spike_high_alpha, low_alpha_flat, high_alpha_falls, high_alpha_spike_rises, verdict "supported" | "unexplained"); the D-031 interpretation, end points only, tol = diagnostic.change_tol.
- Config: diagnostic.{enabled (true), seed_base (3000000), R (500), n ([500, 1000, 4000]), alphas ([0.2, 0.4]), lag_min (2), lag_max (5), change_tol (0.05), test.{n, R, rate_lo, rate_hi, n_small, R_small}}. The only spec'd keys were enabled and seed_base; the others keep every design value in config.yaml (CLAUDE.md).
- Output: results/diagnostic_arch1.csv, written by notebooks/03_results.ipynb cell r10 (skipped when diagnostic.enabled is false). The spec listed one `se` column; the file has one SE per rate (exact_se, nesting_se, false_spike_se).
- Tests: tests/test_diagnostic.py (new; 9 test functions, 10 cases with the parametrised overlap test, by my count, unverified).

## P4 dashboard (D-032, D-033)
- Structure: `src/` gains plots.py and dashboard.py; app.py is now the dashboard (was a stub). Presentation layer = app.py + plots.py + dashboard.py, notebooks, report. Dependencies inside the repo: app -> plots, dashboard, baselines.grid_bic, selector.select_and_fit, data; dashboard -> data (ROOT), rules, selector (private _mean_resid), simulate, stat_tests; plots -> correlogram. No new package.
- plots.py (all return a matplotlib Figure built with the Figure class, no pyplot):
  - price_and_returns(price, returns, label) -> Figure (2 axes)
  - correlogram_2x2(returns, nlags, confidence=0.95) -> Figure (4 axes; spikes outside the band in the accent colour)
  - forecast_vs_abs_return(fc, selectors, label) -> Figure (1 axis; fc has date, selector, h, r2; ValueError on an unknown selector)
  - final_order_bars(counts, true_order, label) -> Figure (1 axis; counts has final_order, count)
- dashboard.py:
  - slice_asof(x, asof); asof_bounds(returns, min_obs) -> (date, date); summary_table(returns); stationarity_table(price, returns)
  - diagnostic_table(returns, cfg) -> DataFrame[test, series, lag, statistic, p_value]; rule_readout(returns, cfg) -> dict(mean=dict(m, text, reason), variance=dict(order, stop, text, reason))
  - selection_tables(result, cfg) -> dict(summary, params, gate, log); grid_comparison(result, grid) -> DataFrame
  - read_result(cfg, name) -> DataFrame | None; result_mtime(cfg, name) -> float | None; pair_rows(df, pair)
  - true_order_label(cfg, true_model); live_recovery(true_model, n, R, cfg) -> (metrics, counts) (hybrid, eval seeds, R <= app.simulate.max_live_R); saved_recovery_row(table, true_model, n, selector); rates_table(metrics); constant RATES
- app.py cached calls (st.cache_data): load_series(pair), run_selection(pair, asof), run_grid(pair, asof), read_csv(name, mtime), run_live(true_model, n, R). Session-state keys grid_key and sim_key remember which button click is being shown.
- Config: new top-level `app` section: page_title, min_obs, pair_labels, forecast_default_selectors, simulate.{default_model, default_n, default_R, max_live_R, saved_selector}, missing_csv_command, captions.{data, diagnose, select, forecast, simulate}, pair_notes.{DEXINUS}, test.timeout_s (tests only). Reused, not duplicated: pairs, start, band_confidence, eda.nlags, gate.*, frozen.decision_id, sim.n, eval.seed_base, recovery.models, paths.results_dir.
- Reads (never writes): results/forecasts_<pair>.csv, loss_table.csv, dm_table.csv, recovery_table.csv. The missing-file message shows app.missing_csv_command (executes notebook 03, which writes all four).
- Tests: tests/test_plots.py (6 tests), tests/test_app.py (14 tests; the last is the AppTest smoke, importorskip on streamlit.testing.v1 and skip if the first pair's raw CSV is absent). Counts are mine, unverified.
- streamlit.testing.v1 exists in the installed streamlit 1.65.0 (folder listed: app_test.py, element_tree.py with Tab, Info and Exception classes; checked by reading the source, not run). That AppTest handles a date slider is assumed, not checked.

## P4b readable dashboard (D-034)
- New dependency: plotly (requirements.txt). matplotlib stays for the notebooks only; nothing the app imports uses it.
- src/plots.py (supersedes the P4 matplotlib list; all return plotly.graph_objects.Figure, Okabe-Ito palette, hatch/dash as second cue):
  - price_line(price, label, unit); return_line(returns, label); return_histogram(returns, label) (2 traces + linear/log buttons)
  - correlogram_grid(returns, nlags, confidence=0.95) (2x2 subplots; per panel band, inside-band and outside-band traces)
  - gate_pvalue_bars(gate, alpha) (gate = DataFrame test, p_value, passes)
  - forecast_lines(fc, selectors, label, names, fallback_selector=None, order=None) (range slider; yellow vrects on fallback runs; ValueError on unknown selector); cumulative_qlike_lines(diff, baseline_name, label, names, order=None)
  - recovery_bars(live, saved, rates, live_R, saved_R) (rates = [(key, se_key, label)]; percent, error_y = Monte Carlo SE); order_choice_bars(saved, live, saved_R, live_R, true_order, max_orders) (trace "True order" + green vrect + "(true)" tick suffix; ValueError with no data); order_heatmap(orders, n, selector, model_names, true_orders)
  - private: _style, _marker, _colour_index, _order_key, _fallback_runs. Imports: plotly, scipy.stats.norm, correlogram.acf_pacf_band. No st.*, no file or config reads.
- src/dashboard.py changes: selection_tables(result, cfg) now returns plain test and parameter names and labelled log values; grid_comparison(result, grid, cfg) and stationarity_table(price, returns, cfg) and rates_table(metrics, cfg) gained cfg (rates_table returns rate as plain name, share and mc_se in percent). New: rate_specs, order_shares, saved_order_counts, label_values, scale_percent, plain_param, results_table, step_table (icons PASS / FAIL / SKIP), render_text, explain_values, constants PASS, FAIL, SKIP. Imports added: re, scipy.stats.norm.
- app.py: cached calls unchanged (load_series, run_selection, run_grid, read_csv, run_live); new helpers show_chart (st.plotly_chart(fig, width="stretch")), show_table (st.column_config: labels from app.columns, app.percent_columns with one decimal, app.number_format), fill_explain. Expander boxes are created at the top of each tab and filled at the end of the script, when explain_values has every number. Extra widgets: forecast fallback-shading selectbox.
- Config (all under `app`): pair_labels (now short) and pair_units, forecast_fallback_default, selector_labels (YAML anchor reused by value_labels), model_labels, rate_labels, param_labels, columns, percent_columns, number_format, value_labels, simulate.{chart_rates, max_orders, live_note}, explain.{title, parts, data, diagnose, select, forecast, simulate}, glossary_title, glossary. Placeholders in the texts are filled by dashboard.explain_values from the data, the results CSVs (diagnostic_arch1, recovery_table, loss_table, dm_table) and config; a missing source prints "n/a".
- Reads (never writes): additionally results/recovery_orders.csv and results/diagnostic_arch1.csv.
- Tests: tests/test_plots.py (10 functions, 19 cases, skipped if plotly is absent), tests/test_app.py (22 functions; config-coverage and placeholder tests check that every column, selector, model, rate and {placeholder} has a plain label or source). Counts are mine, unverified.
- Verified in the installed source (not run): st.plotly_chart(figure_or_data, use_container_width=None, *, width="stretch", height="content", theme="streamlit", key=None, on_select="ignore", ...), streamlit 1.65.0, elements/plotly_chart.py lines 428-445. Unverified: every plotly call (plotly not installed in the venv when written), the sprintf format "%.1f" and "%.4g" in st.column_config.NumberColumn, AppTest's element name "plotly_chart".

## Teaching wiki (D-035)
- docs/wiki/ is documentation only; nothing in src/, app.py, tests/, notebooks/ or config.yaml imports or reads it.
- Layout: 00-index, 01-glossary, 02-notation, 03-life-of-a-sample, 04-viva-bank, 05-experiments; phases/ (7), concepts/ (32), code/ (code/src/ for the 11 modules, plus app.md, config.md, tests.md, notebooks.md). Every page has frontmatter with `sources:` (repo paths it explains), which the skill's manifest uses to find stale pages.
- docs/wiki/.manifest.json is script-managed (wiki_manifest.py scan / commit). It does not exist yet: the scripts are python and hard rule 1 forbids Claude Code from running them.
- Maintenance rule: when a src/ function, a config key or a result file changes, the page listed in its `sources:` frontmatter is stale. Structure, signature or config changes still go to this file first (as before).
