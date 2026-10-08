# Phase plan

## P0 Bootstrap
- [x] Planning complete, repo scaffolded (stubs only)
- [x] Environment installed, versions recorded (arch 8.0.0, statsmodels 0.15.0, pandas 3.0.6, numpy 2.5.3, scipy 1.18.1)
- [ ] First git commit (user to confirm)

## P1 Data, returns, stationarity, first correlograms (4h)
- [ ] data.py
- [ ] stat_tests.py
- [ ] correlogram.py
- [ ] notebooks/01_eda with 4-panel ACF/PACF for EUR/USD
- [ ] Gate: squared-return structure present, else stop and re-plan

## P2 Selector (8h)
- [ ] simulate.sim_garch11
- [ ] rules.py
- [ ] selector.py
- [ ] Tests on simulated GARCH(1,1) and ARCH(1)

## P3 Baselines, forecast, evaluate, recovery experiment (8h)
- [ ] baselines.py, all 5 selectors
- [ ] forecast.py, rolling refit
- [ ] evaluate.py: QLIKE, MSE, DM
- [ ] Results table
- [ ] Recovery table

## P4 Streamlit (6h)
- [ ] 5 tabs: Data / Diagnose / Select / Forecast / Simulate

## P5 Report, cleanup, README (8h)
- [ ] Report
- [ ] Cleanup
- [ ] README

## Kill criteria (in order)
1. Cut INR.
2. Shrink recovery experiment to GARCH(1,1) at two n.
3. Cut Simulate tab.

Never cut: baselines, no-look-ahead.
