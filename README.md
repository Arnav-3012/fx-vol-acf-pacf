# ACF and PACF Driven Order Selection for Daily FX Volatility

<p>
  <img alt="Python" src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white">
  <img alt="arch" src="https://img.shields.io/badge/arch-GARCH-4B8BBE">
  <img alt="statsmodels" src="https://img.shields.io/badge/statsmodels-ACF%2FPACF%20%2B%20tests-4B8BBE">
  <img alt="pandas" src="https://img.shields.io/badge/pandas-150458?logo=pandas&logoColor=white">
  <img alt="NumPy" src="https://img.shields.io/badge/NumPy-013243?logo=numpy&logoColor=white">
  <img alt="SciPy" src="https://img.shields.io/badge/SciPy-8CAAE6?logo=scipy&logoColor=white">
  <img alt="Plotly" src="https://img.shields.io/badge/Plotly-3F4F75?logo=plotly&logoColor=white">
  <img alt="Streamlit" src="https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white">
  <img alt="Jupyter" src="https://img.shields.io/badge/Jupyter-F37626?logo=jupyter&logoColor=white">
  <img alt="pytest" src="https://img.shields.io/badge/pytest-0A9EDC?logo=pytest&logoColor=white">
  <img alt="Data: FRED" src="https://img.shields.io/badge/data-FRED%20H.10-005A9C">
</p>

<p>
  <img alt="Pairs" src="https://img.shields.io/badge/pairs-EUR%2FUSD%20%7C%20USD%2FJPY%20%7C%20USD%2FINR-555555">
  <img alt="Test days" src="https://img.shields.io/badge/test%20days-838%20per%20pair-2E75B6">
  <img alt="Fits" src="https://img.shields.io/badge/model%20fits%20(EUR%2FUSD)-hybrid%2042%20vs%20grid%201260-2E75B6">
  <img alt="Recovery" src="https://img.shields.io/badge/GARCH(1%2C1)%20exact%20recovery%20(n%3D4000)-0.996-2E75B6">
  <img alt="Replications" src="https://img.shields.io/badge/Monte%20Carlo-R%20%3D%20500-2E75B6">
</p>

**Can the autocorrelation (ACF) and partial autocorrelation (PACF) patterns of daily exchange-rate returns pick the order of a GARCH volatility model well enough to forecast volatility as well as an exhaustive search, at a fraction of the cost?**

This repository is an ATSA (Advanced Time Series Analysis) mini-project. It builds a rule-based selector that reads the ACF/PACF of daily FX log returns and of their squares, proposes an ARMA(m, n)-GARCH(p, q) specification, checks the fitted model with a diagnostic gate, repairs it by bounded escalation if the gate fails, and then tests the whole procedure two ways:

1. **Out of sample**, on rolling one-day-ahead variance forecasts for EUR/USD, USD/JPY and USD/INR against four baselines (QLIKE, MSE, Diebold-Mariano tests).
2. **On simulated data with a known answer**, to measure how often the rules recover the true order (a Monte Carlo order-recovery experiment).

Everything is reproducible from `config.yaml` (all thresholds, lag caps, seeds, dates and pairs live there and nowhere else), and every design choice, mistake and result is logged in `docs/`.

---

## Contents

1. [Headline findings](#headline-findings)
2. [Background: why ACF/PACF for volatility](#background-why-acfpacf-for-volatility)
3. [Method](#method)
4. [Results in detail](#results-in-detail)
5. [Limitations (read before citing any number)](#limitations-read-before-citing-any-number)
6. [Repository layout](#repository-layout)
7. [Installation](#installation)
8. [Usage](#usage)
9. [The dashboard](#the-dashboard)
10. [Configuration](#configuration)
11. [Reproducibility and workflow](#reproducibility-and-workflow)
12. [Project status](#project-status)
13. [Data source](#data-source)
14. [References](#references)

---

## Headline findings

All numbers below come from runs the author executed and read; the exact files are in `results/`. Nothing here is a claim beyond what those tables show.

| # | Finding | Evidence |
|---|---------|----------|
| 1 | All three pairs show strong volatility clustering: squared returns are autocorrelated even though returns are not (the project's go/no-go gate passed for EUR/USD, USD/JPY and USD/INR). | Notebook 01 |
| 2 | On EUR/USD and USD/JPY the four GARCH-based selectors (fixed GARCH(1,1), ACF/PACF only, full-grid BIC, hybrid) chose the **same order at every one of 42 refits**, so their forecasts are identical and the order-selection method cannot be separated from a fixed GARCH(1,1) on these pairs. | `results/loss_table.csv` (`modal_order_share` and `agree_grid` both 1.0) |
| 3 | On those two pairs GARCH has a lower QLIKE than the rolling 60-day variance, but the difference is **not statistically significant** (Diebold-Mariano p = 0.51 for EUR/USD, 0.14 for USD/JPY). | `results/dm_table.csv` |
| 4 | The hybrid fits about **42 models over the whole test period against 1,260 for the full-grid search** on EUR/USD (142 against 1,260 on USD/INR), which is the main practical advantage the evidence supports. | `results/loss_table.csv`, column `models_fitted` |
| 5 | USD/INR is a stress case: on 67-76% of refits every fitted GARCH was rejected (persistence at or above 1) and the forecast fell back to the rolling variance. The hybrid beats full-grid BIC there (p = 0.0012, robust to a second bandwidth), but the hybrid-versus-fixed result on INR rests on about 40 days and is **not robust**. | `results/dm_table.csv`, `results/inr_hybrid_vs_fixed.csv` |
| 6 | **Order recovery** (simulated, R = 500): the rules find a true GARCH(1,1) almost always once n is large (0.77 / 0.94 / 1.00 at n = 500 / 1000 / 4000) but find true ARCH(1) only 45-66% of the time and almost never find true GARCH(2,1) or GARCH(1,2), where both the hybrid and full-grid BIC mostly settle on (1,1). | `results/recovery_table.csv` |
| 7 | ARCH(1) recovery gets **worse** with more data (0.64 → 0.50 for a = 0.4). A post-hoc diagnostic is consistent with a cause: the 95% white-noise band is too narrow for the PACF of heavy-tailed squared returns, so chance spikes grow more frequent. | `results/diagnostic_arch1.csv` |

The honest summary: the ACF/PACF-driven hybrid is **cheaper and about as accurate as exhaustive search on these data**, it is **not demonstrably better at forecasting**, and its exact-order accuracy is good for GARCH(1,1) and weak for other shapes.

---

## Background: why ACF/PACF for volatility

Daily FX returns are close to uncorrelated, but their *size* is not: calm weeks follow calm weeks, wild weeks follow wild weeks. This is **volatility clustering**, and it shows up as autocorrelation in the **squared** returns (a noisy stand-in for variance).

The classical Box-Jenkins idea for ARMA models reads model orders from correlograms:

| Process | ACF | PACF |
|---------|-----|------|
| AR(p) | decays | **cuts off after lag p** |
| MA(q) | **cuts off after lag q** | decays |

An ARCH(p) model makes the squared shocks follow an AR(p)-like process, so the **PACF of the squares cuts off at lag p**. A GARCH(1,1) makes the squares behave like an ARMA(1,1): both ACF and PACF of the squares decay slowly. The selector turns these patterns into explicit rules, then lets a diagnostic gate and a bounded repair step catch the cases where the visual rule is wrong.

**Notation (the `arch` package convention).** In GARCH(p, q), `p` is the number of lags of squared shocks (ARCH terms) and `q` is the number of lags of the variance (GARCH terms). Mean-equation orders are `m` (AR) and `n` (MA). Some textbooks swap `p` and `q`; this project does not. Only the AR order `m` is selected; no MA term is fitted.

$$\sigma_t^2 = \omega + \sum_{i=1}^{p}\alpha_i\,\varepsilon_{t-i}^2 + \sum_{j=1}^{q}\beta_j\,\sigma_{t-j}^2$$

---

## Method

### Pipeline

```
FRED daily prices
      |
      v
log returns x 100  ->  ADF / KPSS (stationarity)
      |
      v
MEAN RULE        Ljung-Box on returns; if autocorrelated, AR order m from the PACF (m <= 2)
      |
      v
ARCH CHECK       Ljung-Box + ARCH-LM on squared residuals; no effect -> constant variance, stop
      |
      v
VARIANCE RULE    PACF of squares cuts off at p <= 3, quiet after, ACF of squares fades -> ARCH(p)
                 otherwise start at GARCH(1,1)
      |
      v
FIT (arch)       reject invalid fits (omega <= 0, negative coefficient, persistence >= 1 - 1e-6)
      |
      v
GATE             squared standardised residuals must look white (Ljung-Box at 5/10/20, ARCH-LM)
      |
      +-- pass --> done
      |
      +-- fail --> ESCALATE (at most 3 attempts): best-BIC neighbour (p+1,q) or (p,q+1), cap 3,
                   then Student-t errors; if still failing, return the lowest-BIC valid fit, flagged
      |
      v
ROLLING FORECAST (expanding window, refit every 20 days, one step ahead, no look-ahead)
      |
      v
QLIKE / MSE  ->  Diebold-Mariano with Newey-West
```

### The five selectors compared

| Selector | What it does |
|----------|--------------|
| `rolling_var` | Variance of the last 60 returns. No model. |
| `fixed_garch11` | GARCH(1,1) always. |
| `acf_only` | The ACF/PACF rule's starting order, fitted once, no gate, no escalation. |
| `grid_bic` | Fit every (p, q) with p in 1..5, q in 0..5 (30 models) and keep the lowest valid BIC. |
| `hybrid` | The full procedure above: rules, fit, gate, bounded escalation. |

All GARCH-based selectors use the same mean rule so that differences between them come from the **variance order**, which is the subject of the study.

### Frozen rules (no tuning on real data)

The rule thresholds were tuned **once, on simulated data only**, then frozen in `config.yaml` (decision D-023) before any forecast loss was computed. Real data never tunes a rule. The frozen choices:

- **Mean trigger `lb_only` (M1):** add AR terms only when Ljung-Box(10) on returns rejects. (Calibration: false-AR rate on iid noise 0.05 vs 0.16 for the alternative.)
- **Fade tolerance F3:** the ACF of squares may have up to 3 spikes in lags 10-20 and still count as "fading".
- **Cut-off read C0:** `p` is the last significant PACF lag of the squares up to lag 3.
- **Persistence tolerance:** a fit with alpha + beta >= 1 - 1e-6 is rejected (IGARCH boundary, infinite variance).

Changing any of these needs a new decision entry, a calibration rerun and an eval-seed rerun (policy in `docs/decision.md`, D-023).

### Forecast design

- **Target:** one-day-ahead conditional variance, evaluated against the squared return of the target day, a noisy but standard proxy (realised variance needs intraday data, which is out of scope).
- **Window:** expanding. The forecast for day *i* uses returns before day *i* only. Test set = last 20% of each series (838 days per pair).
- **Refits:** the whole selector is rerun every 20 test days (42 refits). Between refits the order and parameters are kept and only the variance recursion is filtered through the new returns.
- **Failure handling:** if every fit is rejected, that block of days uses the rolling 60-day variance and is counted and flagged, never hidden.

### Evaluation

- **QLIKE** (primary) = ln(h) + r²/h. Robust to proxy noise. Lower is better.
- **MSE** = (r² - h)² (secondary robustness check, dominated by a few outlier days).
- **Diebold-Mariano** with Newey-West long-run variance, Bartlett weights, bandwidth L = floor(4 (T/100)^(2/9)). A second bandwidth (L = 20, one refit block) is reported, and a result is called **robust** only if p < 0.05 under both.
- **No multiplicity correction** is applied (60 tests across the full table). One small p-value is not evidence on its own.
- Only the loss, the test, the samples and the comparison list were fixed *before* looking at numbers (D-028); amendments made afterwards are labelled post-hoc in `docs/decision.md`.

### Order-recovery experiment

Series are simulated from known models, the selector is run on each, and the share of runs that return the true order is counted (with Monte Carlo standard error). True models: ARCH(1), GARCH(1,1), GARCH(2,1), GARCH(1,2), GARCH(1,1) with Student-t errors, plus two controls (iid noise, AR(1)+GARCH(1,1)). Lengths n = 500 / 1000 / 4000, R = 500 replications, with seeds from a range that never overlaps the calibration seeds. Metrics: **exact** order, **nesting** (chosen model contains the truth), **family** (right ARCH vs GARCH type), false-AR rate, gate pass rate, escalation rate, fits per series.

---

## Results in detail

### Forecast losses (test period: 838 days, 42 refits per selector)

| Pair | Selector | QLIKE (lower better) | MSE | Models fitted | Rolling-variance fallback |
|------|----------|---------------------:|----:|--------------:|--------------------------:|
| EUR/USD | rolling_var | -0.7534 | 0.1304 | 0 | 0% |
| EUR/USD | fixed_garch11 = acf_only = hybrid = grid_bic | -0.7630 | 0.1303 | 42 (grid: 1,260) | 0% |
| USD/JPY | rolling_var | 0.1210 | 0.6768 | 0 | 0% |
| USD/JPY | fixed_garch11 = acf_only = hybrid = grid_bic | 0.0447 | 0.6688 | 42 (grid: 1,260) | 0% |
| USD/INR | rolling_var | -2.1046 | 0.02106 | 0 | 0% |
| USD/INR | fixed_garch11 = acf_only | -2.0995 | 0.02117 | 42 | 76% |
| USD/INR | grid_bic | -1.9041 | 0.02344 | 1,260 | 0% |
| USD/INR | hybrid | -2.1014 | 0.02115 | 142 | 67% |

Source: `results/loss_table.csv`. On USD/INR the rolling variance has the lowest QLIKE, and the fixed GARCH, ACF-only and hybrid rows are partly the rolling baseline in disguise because of the fallback share. Read their losses together with that column.

### Diebold-Mariano tests (QLIKE, all test days, primary bandwidth / L = 20)

| Pair | A vs B | Mean loss diff (A - B) | p (primary) | p (L = 20) | Reading |
|------|--------|-----------------------:|------------:|-----------:|---------|
| EUR/USD | hybrid vs rolling_var | -0.0096 | 0.51 | 0.53 | not significant |
| USD/JPY | hybrid vs rolling_var | -0.0763 | 0.14 | 0.12 | not significant |
| USD/INR | hybrid vs grid_bic | -0.1972 | 0.0012 | 0.0056 | hybrid better, **robust** |
| USD/INR | grid_bic vs rolling_var | +0.2005 | 0.0052 | 0.0176 | grid_bic worse, **robust** |
| USD/INR | hybrid vs fixed_garch11 | -0.0019 | 0.68 | 0.70 | not significant |
| USD/INR | hybrid vs rolling_var | +0.0033 | 0.93 | 0.94 | not significant |

For EUR/USD and USD/JPY, hybrid vs fixed / ACF-only / grid are "identical forecasts": the selectors picked the same model every time, so no test exists. On the USD/INR *common-valid* sample (days where both selectors had a valid fit) the hybrid-vs-fixed result is significant at the primary bandwidth (p = 0.0048) but not at L = 20 (p = 0.114), and 100% of its total difference comes from two consecutive refit blocks (about 40 days) where the hybrid used (1,2). It is reported as **not robust**.

### Order recovery (hybrid, exact order found, R = 500, MC SE up to 0.022)

| True model | n = 500 | n = 1000 | n = 4000 | grid_bic at n = 1000 |
|------------|--------:|---------:|---------:|---------------------:|
| ARCH(1), a = 0.4 | 0.658 | 0.606 | 0.452 | 0.994 |
| GARCH(1,1) | 0.766 | 0.938 | 0.996 | 0.982 |
| GARCH(2,1) | 0.046 | 0.036 | 0.224 | 0.060 |
| GARCH(1,2) | 0.000 | 0.006 | 0.038 | 0.004 |
| GARCH(1,1), Student-t errors | 0.660 | 0.878 | 0.992 | 0.844 |
| iid noise (true (0,0)) | 0.926 | 0.912 | 0.930 | 0.000 (not in its grid) |
| AR(1) + GARCH(1,1) | 0.782 | 0.952 | 0.996 | 0.986 |

Other points from `results/recovery_table.csv`:

- **Failures are mostly under-fits**: for every model except ARCH(1), "nesting" equals "exact" to within 0.01, so the chosen model is too small, not too big. For ARCH(1) the opposite holds (nesting about 1.0 against exact 0.45-0.66): the rule over-fits to (2,0), (3,0) or (1,1).
- **Higher-order truths are mostly missed by both selectors.** The rule always starts GARCH(2,1) and GARCH(1,2) series at (1,1); (2,1) is only ever reached by escalation.
- **Cost:** the hybrid fits 1.07-1.83 models per series on average; full-grid BIC fits 30.
- **False-AR rate** of the frozen mean rule: about 0.05 on iid noise, but 0.11-0.20 on ARCH/GARCH series and up to 0.38 on fat-tailed GARCH, probably because Ljung-Box over-rejects under conditional heteroskedasticity (unverified).
- The share of series where every fit was rejected (`no_valid_fit`) is 0.000 in all 26 recovery cells.

### Why ARCH(1) recovery falls with n (post-hoc diagnostic, D-031)

| ARCH(1) alpha | n | exact | false PACF-of-squares spike in lags 2-5 |
|--------------:|--:|------:|-----------------------------------------:|
| 0.2 | 500 → 4000 | 0.604 → 0.724 | 0.216 → 0.228 (flat) |
| 0.4 | 500 → 4000 | 0.640 → 0.500 | 0.316 → 0.472 (rises) |

For normal-error ARCH(1) the eighth moment of returns is infinite when alpha exceeds about 0.31 (author's arithmetic), which makes the sample autocorrelation of squares more variable than the 1.96/√n band assumes. The pre-fixed verdict rule in `simulate.diagnostic_verdict` printed **"supported"**: the result is *consistent with* that explanation, not a proof. The late-lag ACF "fade" route was not measured and may also contribute. The rules stay frozen; this is reported as a limitation, not fixed.

### Calibration on simulated data (D-018 to D-023)

At the frozen rules (R = 100, n = 1000, calibration seeds, so optimistic by selection): exact-order recovery ARCH(1) 0.65, ARCH(2) 0.46, GARCH(1,1) 0.94. The contiguous cut-off alternative (C1) was identical to C0 in all 18 cells and was not adopted. Files: `results/calibration*.csv`.

---

## Limitations (read before citing any number)

- **Noon rates, not closes.** FRED H.10 gives noon buying rates in New York, so every return is noon-to-noon.
- **Noisy target.** The squared return is a very noisy proxy of variance; only averaged losses mean anything, single days say little.
- **No multiplicity correction** across the 60 DM tests; DM uses an asymptotic normal reference with no small-sample correction.
- **Heuristic band.** The 95% white-noise band assumes light tails and no clustering, so for squared returns it is too narrow and chance spikes are common.
- **Gate uses no degrees-of-freedom adjustment** (D-014), a known simplification: with several thousand observations the effect is expected to be small, but it makes the gate slightly lenient.
- **Hard cases.** Higher-order truths ((2,1), (1,2)) are almost never recovered; ARCH(1) recovery degrades with n at large alpha; the frozen mean rule adds a spurious AR term in 10-38% of constant-mean ARCH/GARCH series.
- **USD/INR fallback.** On most INR refits every fit is rejected at the persistence boundary, so selectors there partly reduce to the rolling baseline.
- **Simulation design is the author's choice.** True models, omegas and parameter values cover low orders only; the t case has nu = 6 only; the AR control has one phi.
- **Stale parameters.** Refitting every 20 days is a cost choice, not tuned (no sensitivity run).
- **Scope.** Daily data, three pairs, no trading strategy, no intraday data, no deep learning.

---

## Repository layout

```
fx-vol-acf-pacf/
├── app.py                  Streamlit dashboard (UI only, no logic)
├── config.yaml             every threshold, lag cap, seed, date, pair, dashboard text
├── requirements.txt        dependencies (unpinned)
├── CLAUDE.md               working rules for the AI coding assistant used on this project
├── src/
│   ├── data.py             FRED download/cache, config loader, log returns
│   ├── stat_tests.py       ADF/KPSS, Ljung-Box, ARCH-LM
│   ├── correlogram.py      ACF/PACF with white-noise band, significant lags
│   ├── rules.py            mean-order rule, variance-order rule, PACF cut-off read
│   ├── selector.py         select_and_fit: fit, validity check, gate, escalation
│   ├── baselines.py        the five selectors (fit_forecast interface)
│   ├── forecast.py         rolling-refit forecasting, writes results/forecasts_<pair>.csv
│   ├── evaluate.py         QLIKE, MSE, Diebold-Mariano (hand-rolled), loss/DM tables
│   ├── simulate.py         GARCH/ARCH simulators, order-recovery experiment, calibration, diagnostic
│   ├── plots.py            Plotly figure builders (pure functions)
│   └── dashboard.py        pure helpers for the app (as-of cut, tables, labels, text)
├── notebooks/
│   ├── 01_eda.ipynb            returns, stationarity, first correlograms, the go/no-go gate
│   ├── 02_selector_sim.ipynb   selector demo on real and simulated data, calibration
│   └── 03_results.ipynb        forecasts, loss and DM tables, recovery experiment, diagnostic
├── tests/                  pytest suite (rules, selector, forecast, evaluate, recovery, app, plots)
├── results/                saved CSV tables the dashboard and report read
├── data/raw/               cached FRED CSVs (git-ignored, downloaded on first use)
├── docs/                   phaseplan, decision log, mistakes, architecture, work log
└── report/                 (reserved for the written report)
```

Design rules: pure functions in `src/`; no logic in `app.py` or notebooks; seeds, thresholds and pairs only in `config.yaml`; no look-ahead anywhere (every choice or fit uses data up to time *t* only); log returns × 100; prefer `statsmodels`, `arch` and `scipy`, and hand-roll only the simulation recursion, QLIKE and Diebold-Mariano.

---

## Installation

Requires **Python 3.11 or newer** (developed on 3.13) and an internet connection the first time, to download the FRED series.

```bash
git clone https://github.com/Arnav-3012/fx-vol-acf-pacf.git
cd fx-vol-acf-pacf

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Dependencies: pandas, numpy, scipy, statsmodels, arch, matplotlib, plotly, streamlit, joblib, pyyaml, pytest, nbconvert, ipykernel. They are unpinned in `requirements.txt`; the author's runs used arch 8.0.0, statsmodels 0.15.0, pandas 3.0.6, numpy 2.5.3, scipy 1.18.1 and streamlit 1.65.0.

> **Tip:** always call tools through the environment's interpreter (`python -m pytest`, `python -m streamlit`, `python -m nbconvert`). A bare `pytest` or `jupyter` can resolve to a different Python (for example conda's) that lacks `arch` (logged as M-002).

---

## Usage

### 1. Run the tests

```bash
python -m pytest -q
```

### 2. Get the data

Nothing to do by hand: the first call to `data.load_fx` downloads each series from FRED (`fred.url_template` in `config.yaml`) and caches it in `data/raw/{series_id}.csv`; later runs are offline. If the download fails, save the CSV from the FRED series page into `data/raw/` under that name. Series used:

| Pair | FRED series | Quote |
|------|-------------|-------|
| EUR/USD | `DEXUSEU` | US dollars per euro |
| USD/JPY | `DEXJPUS` | Japanese yen per US dollar |
| USD/INR | `DEXINUS` | Indian rupees per US dollar |

### 3. Reproduce the analysis

Run the notebooks in order. They are meant to be read as well as run: each code cell opens with a `GOAL` comment and a note on how to read its output.

```bash
python -m nbconvert --to notebook --execute --inplace notebooks/01_eda.ipynb
python -m nbconvert --to notebook --execute --inplace notebooks/02_selector_sim.ipynb
python -m nbconvert --to notebook --execute --inplace notebooks/03_results.ipynb
```

Notebook 03 regenerates every table in `results/` (forecasts, loss and DM tables, recovery table, diagnostic). In the author's last logged run it took about 3.5 minutes on a multi-core laptop. For a quick check, set `forecast.smoke: true` and `recovery.smoke: true` in `config.yaml` (restore both to `false` for the full run).

### 4. Use the selector directly

```python
from src.data import load_config, load_fx, to_log_returns
from src.selector import select_and_fit

cfg = load_config()
price = load_fx("DEXUSEU", cfg["start"], cfg=cfg)
returns = to_log_returns(price)          # log returns x 100

result = select_and_fit(returns, cfg)    # rules -> fit -> gate -> escalation
print(result["order"], result["dist"], result["gate"], result["flagged"])
```

### 5. Launch the dashboard

```bash
python -m streamlit run app.py
```

The Forecast and Simulate tabs read `results/*.csv`. If they are missing the app prints the command that regenerates them (notebook 03 above).

USD/INR note: on the Select tab, USD/INR at the full sample shows a red "No valid fit" banner. This is expected, not a crash: every GARCH fit tried ends with persistence at the boundary of 1 and is rejected, so the order shown is only the rule's proposal and the forecasting experiment falls back to the rolling 60-day variance (D-019, D-026).

---

## The dashboard

Five tabs map one-to-one onto the pipeline. Every tab has a "How to read this tab" box and the sidebar has a glossary, all rendered from `config.yaml`. The sidebar **as-of date** cuts the data once, so the Data, Diagnose and Select tabs never see anything after that date.

| Tab | What it shows |
|-----|---------------|
| **Data** | Price chart, return chart, return histogram against a normal curve (linear or log axis). |
| **Diagnose** | Interactive ACF/PACF of returns and squared returns with the white-noise band, formal tests, and the frozen rules' readout (mean order, variance start order, reasons). |
| **Select** | Step-by-step trace of one selector run, fitted parameters, gate p-values, every model tried, optional full-grid BIC comparison. |
| **Forecast** | Saved one-day-ahead forecasts for the five selectors against the absolute return, cumulative QLIKE difference, loss table, Diebold-Mariano table. Shaded days mark rolling-variance fallbacks. |
| **Simulate** | Live Monte Carlo order recovery (up to 50 series) next to the saved run (R = 500), order-choice bars and a heatmap of chosen orders for every true model. |

---

## Configuration

`config.yaml` is the single source of truth. Main sections:

| Key | Controls |
|-----|----------|
| `pairs`, `start`, `test_fraction` | Which FRED series, start date (2010-01-01), share held out (0.2) |
| `mean`, `arch_check`, `variance`, `gate`, `escalation`, `fit` | The frozen selector rules and thresholds |
| `forecast`, `baselines` | Refit interval (20), horizon (1), rolling window (60), grid limit (5), smoke mode |
| `evaluate` | Losses, DM comparisons, bandwidth settings |
| `sim`, `eval`, `calibration`, `recovery`, `diagnostic` | Simulation lengths, replications, seed ranges (disjoint: 1,000,000 / 2,000,000 / 3,000,000), true models |
| `app` | Dashboard labels, explanations, glossary and limits |

The `frozen` block records the date and decision ID of the rule freeze; `tests/test_frozen.py` pins the frozen values so an accidental change fails a test. After editing `config.yaml`, clear the Streamlit cache (press `C` in the app) or restart it, because cached functions are not keyed on the config.

---

## Reproducibility and workflow

- **Seeds** come from `config.yaml`. Calibration, evaluation and diagnostic seed ranges are disjoint and checked in code.
- **No look-ahead.** The test suite includes checks that forecasts for day *t* do not change when later data is altered, and that the dashboard's as-of cut does not leak.
- **Decision log.** `docs/decision.md` records every design choice (D-001 to D-035) with why and alternatives; entries written before results are marked as such, and post-hoc ones are labelled post-hoc.
- **Mistakes log.** `docs/mistakes.md` records errors and wrong assumptions with the prevention rule.
- **Work log and plan.** `docs/logs.md` is a dated record of what was run and read; `docs/phaseplan.md` tracks what is verified (`[x]`) versus only written (`[~]`).
- **Division of labour.** Planning was done in a claude.ai project; coding was done with Claude Code under strict rules (see `CLAUDE.md`): the assistant never ran code or state-changing git, and the author ran every command and pasted the output back, so no result in the logs is invented.

---

## Project status

| Phase | State |
|-------|-------|
| P0 scaffold | done |
| P1 data, stationarity, first correlograms | done and verified |
| P2 selector | done and verified |
| P3a calibration and rule freeze | done and verified |
| P3 baselines, forecast, evaluation, recovery experiment | done and verified through the full recovery run |
| P3 (c2) ARCH(1) diagnostic | done and verified (run, read, tests passed) |
| Test suite | **132 passed** in one run (2026-10-19) |
| P4 / P4b Streamlit dashboard (Plotly) | written, all its tests pass; the app was opened and the Select tab for USD/INR was checked by eye. The other four tabs and the Plotly visuals have **not** been visually checked yet |
| P5 written report | not started |

The data is fixed at the FRED download of 2026-10-08 (last observation 2026-10-02), so the dashboard's as-of slider ends there and every saved result is reproducible against the same sample.

Planned work: look at the remaining dashboard tabs, combine the result tables across all three pairs (P3 task d), write the report.

---

## Data source

Daily exchange rates are the Federal Reserve's H.10 release, distributed through FRED (Federal Reserve Bank of St. Louis). Raw CSVs are **not** committed (`data/raw/` is git-ignored); they are downloaded on first use. Check FRED's terms of use before redistributing the data.

---

## References

- Engle, R. F. (1982). Autoregressive conditional heteroscedasticity with estimates of the variance of United Kingdom inflation. *Econometrica*, 50(4).
- Bollerslev, T. (1986). Generalized autoregressive conditional heteroskedasticity. *Journal of Econometrics*, 31(3).
- Box, G. E. P., & Jenkins, G. M. *Time Series Analysis: Forecasting and Control*.
- Diebold, F. X., & Mariano, R. S. (1995). Comparing predictive accuracy. *Journal of Business & Economic Statistics*, 13(3).
- Newey, W. K., & West, K. D. (1987). A simple, positive semi-definite, heteroskedasticity and autocorrelation consistent covariance matrix. *Econometrica*, 55(3).
- Patton, A. J. (2011). Volatility forecast comparison using imperfect volatility proxies. *Journal of Econometrics*, 160(1).
- Sheppard, K. *arch* Python package: https://github.com/bashtage/arch

---

## Author

Arnav Chaturvedi. ATSA mini-project.

No licence has been chosen yet; until one is added, all rights are reserved by default.
