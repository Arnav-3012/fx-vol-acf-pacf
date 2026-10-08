# Phase plan

## P0 Bootstrap
- [x] Planning complete, repo scaffolded (stubs only)
- [x] Environment installed, versions recorded (arch 8.0.0, statsmodels 0.15.0, pandas 3.0.6, numpy 2.5.3, scipy 1.18.1)
- [x] First git commit (user confirmed; Python 3.13+)

## P1 Data, returns, stationarity, first correlograms (4h)
(`[~]` = written, not yet run; `[x]` = verified by user run)
- [x] data.py
- [x] stat_tests.py
- [x] correlogram.py
- [x] tests/test_p1.py (5 passed)
- [x] notebooks/01_eda with 4-panel ACF/PACF for EUR/USD
- [x] Gate PASSED: squared-return structure present for all three pairs (user run)

## P2 Selector (8h)
- [x] simulate.sim_garch11, sim_arch1
- [x] rules.py
- [x] selector.py
- [x] tests/test_p2.py (verified: user's full-suite run, 19 passed; by my count P1 5 + P2 7 + P3a 7)
- [~] notebooks/02_selector_sim.ipynb (P2b, written, not run)

## P3a Recovery harness and calibration on simulated data (D-018) DONE
- [~] config keys, rules (fade tolerance, mean trigger), selector (persistence_tol, no_valid_fit), written, not run
- [~] simulate.order_recovery_experiment and calibration helpers, written, not run
- [~] tests/test_p3a.py, written, not run
- [~] notebooks/02_selector_sim.ipynb cells s04-s05, written, not run
- [x] First calibration run (F0-F2, M0/M1) read; nothing frozen
- [~] Calibration extended: F3, F4, mean candidates on arch1/garch11, calibration_orders.csv (D-021), written, not run
- [x] User ran extended calibration, tables read (F3 = F4 plateau; ARCH(1) loss is a PACF cut-off issue)
- [~] P3a-3: cut-off read calibration (D-022): sim_arch, cutoff_rule C0/C1, helper pacf_cutoff, grid cell s06, tests, written, not run
- [x] User ran P3a-3, results read: C1 identical to C0 in all 18 cells; D-022 criterion keeps (C0, F3); nothing frozen
- [x] Winners frozen in config.yaml (D-023: C0, F3, M1, persistence_tol 1e-6), tests/test_frozen.py written, not run

## P3 Baselines, forecast, evaluate, recovery experiment (8h) <- CURRENT PHASE
Each task is <= 4h. Rules are frozen (D-023); nothing here may change them.
- [x] (a) tests verified by user run (38 passed); full run done for 3 pairs (838 days, 42 refits), CSVs in results/, no losses computed yet (D-024 to D-027). baselines.py plus forecast.py rolling refit: 5 selectors incl. baselines, refit every forecast.refit_every, no look-ahead (fit and order choice use data up to t only); no_valid_fit refits fall back to the rolling variance and are counted (D-019)
- [x] (b) VERIFIED by user runs (61 passed, regression diff 0.0, tables and reject reasons read; rejected_persistence values and the figure not yet seen). D-028 written first. evaluate.py (QLIKE, MSE, Diebold-Mariano hand-rolled, loss/DM tables, cumulative-QLIKE data), fit-failure columns in the forecast CSV, evaluate config, tests/test_evaluate.py, notebook cells r02-r05: tests verified (61 passed), notebook ran (23 s), tables read; regression check read: max abs diff in h = 0.0 for all 3 pairs; still open: reject columns' values not yet seen
- [x] (b2) VERIFIED by user runs (81 passed, regression diff 0.0 for all 3 pairs, notebook ran with no error, dm_table / inr table / rejected_persistence read). Robustness and observation fixes on the (b) tables (D-029 written first): dm_L20 / p_L20 in dm_table (robust = significant under both L), escalation_rate NaN for grid_bic, agree_grid on both-valid refits only plus n_both_valid, `dist` column in the forecast CSV, results/inr_hybrid_vs_fixed.csv (evaluate.block_qlike_diff), tests in test_evaluate.py (+3) and test_forecast.py (+1), notebook cells r04 (comments) and r06. Open: the regression check must still print 0.0
- [x] (c) VERIFIED by user runs: smoke (R = 20, 7.7 s) then FULL run (R = 500, n = 500/1000/4000, recovery part 180.5 s, notebook 3:23 wall, no error); recovery_table.csv read, recovery_orders.csv spot-read, heatmap of the full run not looked at. order_recovery_experiment on the eval seeds (eval.seed_base) (D-030 written first): true grid ARCH(1), GARCH(1,1), GARCH(2,1), GARCH(1,2), GARCH(1,1)-t plus iid and AR(1)+GARCH(1,1) controls; n in {500, 1000, 4000}, R = 500, hybrid at all n, grid_bic at n = 1000; exact, nesting, family, any_ar_rate, gate, escalation, fits, flagged, no_valid_fit with Monte Carlo SE. simulate.sim_garch, recovery_metrics, recovery_table, order_count_matrix; config recovery.* (smoke true by default); tests/test_recovery.py (16 tests by my count); notebook cells r07-r09 (tables, heatmaps, run_time_recovery.txt). Open: smoke run, timing, then the full run
- [~] (c2) POST-HOC diagnostic of why ARCH(1) exact recovery falls with n (D-031 written first, labelled post-hoc): simulate.diagnostic_arch1_table / diagnostic_verdict / false_spike_rate / pacf_squares_spike / check_diagnostic_seed_ranges, config diagnostic.*, tests/test_diagnostic.py (10 cases by my count), notebook 03 cell r10 (writes results/diagnostic_arch1.csv). Notebook run and CSV + verdict read (user run; verdict "supported", 7.8 s); pytest output for the 10 new cases NOT yet pasted, so the tests are unverified. Changes no rule, threshold or existing result
- [ ] (d) results tables for all pairs (forecast losses, DM tests, recovery table)

## P4 Streamlit (6h)
- [~] D-032 and D-033 written first (plots module, helper module, as-of rule); config `app` section, written, not run
- [~] src/plots.py (4 pure Figure builders) and src/dashboard.py (pure helpers), written, not run
- [~] app.py, 5 tabs: Data / Diagnose / Select / Forecast / Simulate (UI only), written, not run
- [~] tests/test_plots.py (6 tests) and tests/test_app.py (14 tests incl. the AppTest smoke), written, not run; counts are mine, unverified (expected total 91 + 20 = 111 if the P3(c2) count of 91 holds)
- [~] README run line
- [ ] User runs: pytest, streamlit --version, the app, and looks at each of the five tabs (no P4 run output has been pasted yet; the P4 lines above, including the matplotlib builders and the 6 + 14 test counts, are superseded by P4b)

## P4b Readable dashboard: Plotly, plain labels, explanations
- [~] D-034 written first; plotly added to requirements.txt (not installed in .atsa-project when written)
- [~] config `app`: short pair labels and units, selector / model / rate / parameter / column / value labels, percent columns, simulate chart keys, `explain` (5 tabs x 4 parts), glossary, live note; written, not run
- [~] src/plots.py rewritten: 10 Plotly builders (price_line, return_line, return_histogram, correlogram_grid, gate_pvalue_bars, forecast_lines, cumulative_qlike_lines, recovery_bars, order_choice_bars, order_heatmap), written, not run
- [~] src/dashboard.py: plain-label helpers, step_table, results_table, order_shares, explain_values, render_text; signatures of stationarity_table, grid_comparison, rates_table changed; written, not run
- [~] app.py: Plotly charts via st.plotly_chart(width="stretch"), column_config tables, "How to read this tab" on every tab, sidebar glossary; written, not run
- [~] tests/test_plots.py (10 test functions, 19 cases) and tests/test_app.py (22 test functions), written, not run; counts are mine (expected total 91 + 19 + 22 = 132 if the P3(c2) count of 91 holds), unverified
- [ ] User runs: pip install, pytest, the app, and looks at each tab with its expander open

## P5 Report, cleanup, README (8h)
- [ ] Report
- [ ] Cleanup
- [~] README: full README.md written (method, results from logged runs, install, usage, limits, status), not user-checked; .gitignore gained .atsa-project/, .DS_Store, .env

## Kill criteria (in order)
1. Cut INR.
2. Shrink recovery experiment to GARCH(1,1) at two n.
3. Cut Simulate tab.

Never cut: baselines, no-look-ahead.
