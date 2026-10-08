# Architecture

Module contracts are design, adjustable via docs/decision.md.

## Structure
```
fx-vol-acf-pacf/
  CLAUDE.md  README.md  config.yaml  requirements.txt  .gitignore  app.py
  docs/        logs.md phaseplan.md decision.md mistakes.md architecture.md
  data/        raw/ processed/
  src/         __init__ data stat_tests correlogram rules selector
               baselines simulate forecast evaluate
  notebooks/
  tests/       __init__
  report/
```

## Layers
- Data: data.py
- Statistics: stat_tests.py, correlogram.py
- Decision: rules.py, selector.py
- Evaluation: baselines.py, forecast.py, evaluate.py, simulate.py
- Presentation: app.py, notebooks, report

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
