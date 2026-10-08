# Decisions

Format: ID | date | choice | why | alternatives.

## D-001 | 2026-10-08
- Choice: Topic is fixed: "ACF and PACF Driven Order Selection for Daily Foreign Exchange Rate Volatility Analysis".
- Why: Assigned by faculty.
- Alternatives: none.

## D-002 | 2026-10-08
- Choice: ACF/PACF is the backbone, GARCH is the engine, a diagnostic gate with escalation checks the fit.
- Why: Keeps the assigned topic central while giving a testable volatility model.
- Alternatives: pure ACF/PACF on squared returns with no gate; full-grid information criteria only.

## D-003 | 2026-10-08
- Choice: Data from FRED H.10 daily. DEXJPUS and DEXUSEU verified; DEXINUS unverified.
- Why: Free, daily, reproducible.
- Alternatives: Yahoo Finance, ECB, paid feeds.

## D-004 | 2026-10-08
- Choice: Five selectors compared: (1) rolling 60-day variance, (2) fixed GARCH(1,1), (3) ACF/PACF only, (4) full-grid BIC with p,q <= 5, (5) hybrid.
- Why: Covers a naive, a standard, a pure-topic, an exhaustive and a combined approach.
- Alternatives: fewer baselines (rejected: baselines are never cut).

## D-005 | 2026-10-08
- Choice: Loss QLIKE = ln(h) + r^2/h and MSE, both against squared-return proxy. Diebold-Mariano with Newey-West.
- Why: QLIKE is robust to proxy noise; DM tests equal predictive accuracy.
- Alternatives: realized-variance proxy (needs intraday, out of scope).

## D-006 | 2026-10-08
- Choice: Notation p = ARCH lags (squared shocks), q = GARCH lags (variances), mean orders m (AR), n (MA).
- Why: Matches arch package convention; avoids the swapped-naming trap.
- Alternatives: Bollerslev's original (p, q swapped).

## D-007 | 2026-10-08
- Choice: Rules frozen in config.yaml before results; tuned once on simulated data.
- Why: Prevents tuning on the evaluation data.
- Alternatives: tuning on real data (rejected: leakage).

## D-008 | 2026-10-08
- Choice: Workflow: claude.ai plans, Claude Code codes, Claude Code never runs code or state-changing git.
- Why: User runs everything and pastes output; no invented results.
- Alternatives: Claude Code runs code directly.

## D-009 | 2026-10-08
- Choice: Streamlit dashboard with 5 tabs: Data, Diagnose, Select, Forecast, Simulate.
- Why: Basic, maps one-to-one to pipeline stages.
- Alternatives: notebook only.

## D-010 | 2026-10-08
- Choice: Escalation on gate failure: try best-BIC neighbour (p+1,q) / (p,q+1), then Student-t errors, cap 3 attempts, flag failure if still failing.
- Why: Bounded, deterministic repair path.
- Alternatives: unbounded grid search; accept first fit.

## D-011 | 2026-10-08
- Choice: FX data loaded by direct FRED CSV download (fred.url_template in config.yaml, URL unverified), cached under data/raw. Manual download from the FRED series page is the fallback (save as data/raw/{series_id}.csv).
- Why: No API key or extra dependency; cached file makes later runs offline and reproducible.
- Alternatives: fredapi / pandas-datareader (new dependency), Yahoo Finance.
