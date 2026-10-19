# ACF and PACF Driven Order Selection for Daily Foreign Exchange Rate Volatility Analysis

**Arnav Chaturvedi**
**Roll No: [add roll number]**
**Date: [add submission date]**
**Course: Advanced Time Series Analysis (ATSA), mini-project**

---

## Abstract

This study asks whether the autocorrelation (ACF) and partial autocorrelation (PACF) patterns of daily exchange-rate returns can choose the order of a GARCH volatility model well enough to forecast volatility as accurately as an exhaustive search, at a fraction of the cost. A rule-based selector reads the ACF/PACF of the returns and of their squares, proposes an ARMA-GARCH($p,q$) specification, checks the fitted model with a diagnostic gate, and repairs it by bounded escalation if the gate fails. The rules were tuned once on simulated data and then frozen before any forecast was scored. The procedure was tested two ways: on rolling one-day-ahead variance forecasts for EUR/USD, USD/JPY and USD/INR against four baselines (QLIKE and MSE losses, Diebold-Mariano tests), and on simulated series with a known true order (Monte Carlo order recovery). The evidence shows the selector is **cheaper** than full-grid BIC (about 42 model fits against 1,260 on EUR/USD) and **as accurate** on these data, but it is **not demonstrably better** at forecasting. Its exact-order accuracy is high for GARCH(1,1) (0.94 at $n=1000$, 1.00 at $n=4000$) and weak for other shapes. A post-hoc diagnostic is consistent with the white-noise band being too narrow for heavy-tailed squared returns.

---

## 1. Introduction

Daily exchange-rate returns are close to uncorrelated, but their *size* is not: calm periods follow calm periods and wild periods follow wild periods. This is **volatility clustering**, and it appears as autocorrelation in the squared returns, a noisy stand-in for variance. The ARCH and GARCH family of models describes it.

The classical Box-Jenkins idea reads ARMA orders from correlograms: an AR($p$) process has a PACF that cuts off after lag $p$, and an MA($q$) process has an ACF that cuts off after lag $q$. An ARCH($p$) model makes the squared shocks follow an AR($p$)-like process, so the PACF of the squares should cut off at lag $p$; a GARCH(1,1) makes the squares behave like an ARMA(1,1), so both functions decay slowly. This project turns those patterns into explicit rules for choosing the GARCH order.

**Notation.** In GARCH($p,q$), $p$ is the number of lags of squared shocks and $q$ the number of lags of the variance (the convention of the `arch` package; some textbooks swap them). $m$ is the AR order of the mean equation.

$$\sigma_t^2=\omega+\sum_{i=1}^{p}\alpha_i\varepsilon_{t-i}^2+\sum_{j=1}^{q}\beta_j\sigma_{t-j}^2$$

**Questions.** (1) Do the ACF/PACF rules pick an order that forecasts as well as full-grid BIC? (2) At what cost? (3) How often do the rules recover the true order when it is known?

**Scope.** Daily data for three pairs. No trading strategy, no intraday data, no deep learning.

---

## 2. Methodology

### 2.1 Data

Daily exchange rates from the Federal Reserve H.10 release, downloaded from FRED: EUR/USD (`DEXUSEU`), USD/JPY (`DEXJPUS`) and USD/INR (`DEXINUS`), from 2010-01-01. The raw files are the download of 2026-10-08, with the last observation on 2026-10-02; the data is kept fixed so every saved result is reproducible. Returns are log returns multiplied by 100. FRED H.10 rates are noon buying rates in New York, not closing prices, so every return is noon-to-noon. The last 20% of each series (838 days per pair) is the test period. USD/INR is the stress case: autocorrelated returns, many exact-zero days and heavy tails.

### 2.2 The selector

| Step | What it does |
|---|---|
| Mean rule | Ljung-Box(10) on returns; if it rejects, an AR order $m\le 2$ is read from the PACF |
| Volatility check | Ljung-Box and ARCH-LM on squared residuals; no effect means constant variance, and the selector stops |
| Variance rule | PACF of squares cuts off at $p\le3$, is quiet afterwards, and the ACF of squares fades: ARCH($p$); otherwise start at GARCH(1,1) |
| Fit and validity | Fit with `arch`; reject a fit if $\omega\le0$, any coefficient is negative, or persistence $\alpha+\beta\ge1-10^{-6}$ |
| Diagnostic gate | Squared standardised residuals must look white: Ljung-Box at lags 5, 10, 20 and ARCH-LM at 5 lags, all with $p>0.05$ |
| Escalation | If the gate fails: try the best-BIC neighbour $(p+1,q)$ or $(p,q+1)$ (cap 3), then Student-t errors; if still failing, return the lowest-BIC valid fit, flagged. At most 4 fits in total |

**Frozen rules.** The thresholds were calibrated once on simulated data only and then frozen (decision D-023) before any forecast loss existed: Ljung-Box-only mean trigger, up to 3 spikes tolerated in the "fading" lags 10 to 20, the last significant PACF lag as the cut-off, and the persistence tolerance above. Real data never tunes a rule.

### 2.3 The five selectors compared

| Selector | Description |
|---|---|
| Rolling-window variance | Variance of the last 60 returns; no model |
| Fixed GARCH(1,1) | Always GARCH(1,1) |
| ACF/PACF rules only | The rule's starting order, fitted once; no gate, no escalation |
| Full-grid BIC | Every $(p,q)$ with $p\in1..5$, $q\in0..5$ (30 models), lowest valid BIC |
| Hybrid | The full procedure: rules, fit, gate, bounded escalation |

All GARCH-based selectors use the same mean rule, so differences come from the variance order alone.

### 2.4 Forecast design and evaluation

- **Forecast:** one-day-ahead conditional variance, expanding window, the whole selector rerun every 20 test days (42 refits); no look-ahead (every choice and fit uses data up to time $t$ only).
- **Failure handling:** if every fit in a refit is rejected, that block of days uses the rolling 60-day variance; such days are counted and flagged, never hidden.
- **Target:** the squared return of the target day, a noisy but standard proxy for variance.
- **Losses:** QLIKE $=\ln h+r^2/h$ (primary, robust to proxy noise) and MSE $=(r^2-h)^2$ (secondary). Lower is better.
- **Test:** Diebold-Mariano with a Newey-West variance (Bartlett weights, $L=\lfloor4(T/100)^{2/9}\rfloor$), plus a second bandwidth $L=20$. A result is called **robust** only if $p<0.05$ under both. No multiplicity correction is applied across the 60 tests.

### 2.5 Order-recovery experiment

Series are simulated from known models, the selector is run on each, and the share returning the true order is counted. True models: ARCH(1), GARCH(1,1), GARCH(2,1), GARCH(1,2), GARCH(1,1) with Student-t errors, and two controls (iid noise, AR(1)+GARCH(1,1)). Lengths $n=500,1000,4000$; $R=500$ replications; seeds from a range disjoint from the calibration seeds. Metrics: **exact** order, **nesting** (chosen model contains the truth) and **family** (right ARCH versus GARCH type), with Monte Carlo standard error $\sqrt{\hat p(1-\hat p)/R}\le0.022$.

### 2.6 Implementation

Python with `arch`, `statsmodels`, `scipy`, `pandas` and `numpy`; only the simulation recursion, QLIKE and Diebold-Mariano are hand-written. Every threshold, seed, date and pair lives in `config.yaml`. A Streamlit dashboard (Plotly charts) presents each stage, and a suite of 132 tests passes.

---

## 3. Results

### 3.1 Volatility clustering is present

The project's go/no-go gate passed for all three pairs: squared returns are autocorrelated even though returns are close to uncorrelated. USD/INR is the contrast case: its returns are themselves autocorrelated (the selector picks an AR mean there), it has 134 exact-zero days, and its excess kurtosis is 8.75 on the full sample.

### 3.2 Forecast losses (838 test days, 42 refits)

| Pair | Selector | QLIKE | MSE | Models fitted | Rolling-variance fallback |
|---|---|---:|---:|---:|---:|
| EUR/USD | Rolling variance | −0.7534 | 0.1304 | 0 | 0% |
| EUR/USD | Fixed GARCH = rules only = hybrid = full grid | −0.7630 | 0.1303 | 42 (grid 1,260) | 0% |
| USD/JPY | Rolling variance | 0.1210 | 0.6768 | 0 | 0% |
| USD/JPY | Fixed GARCH = rules only = hybrid = full grid | 0.0447 | 0.6688 | 42 (grid 1,260) | 0% |
| USD/INR | Rolling variance | −2.1046 | 0.0211 | 0 | 0% |
| USD/INR | Fixed GARCH = rules only | −2.0995 | 0.0212 | 42 | 76% |
| USD/INR | Full-grid BIC | −1.9041 | 0.0234 | 1,260 | 0% |
| USD/INR | Hybrid | −2.1014 | 0.0212 | 142 | 67% |

On EUR/USD and USD/JPY the four GARCH-based selectors chose the **same order at all 42 refits**, so their forecasts are identical and the order-selection method cannot be separated from a fixed GARCH(1,1). On USD/INR the rolling variance has the lowest QLIKE, and the fixed-GARCH, rules-only and hybrid rows are partly the rolling baseline because of the fallback share.

### 3.3 Diebold-Mariano tests (QLIKE, all test days)

| Pair | A versus B | Mean loss difference (A − B) | $p$ (primary) | $p$ ($L=20$) | Reading |
|---|---|---:|---:|---:|---|
| EUR/USD | hybrid vs rolling | −0.0096 | 0.51 | 0.53 | not significant |
| USD/JPY | hybrid vs rolling | −0.0763 | 0.14 | 0.12 | not significant |
| USD/INR | hybrid vs full grid | −0.1972 | 0.0012 | 0.0056 | hybrid better, robust |
| USD/INR | full grid vs rolling | +0.2005 | 0.0052 | 0.0176 | full grid worse, robust |
| USD/INR | hybrid vs fixed GARCH | −0.0019 | 0.68 | 0.70 | not significant |
| USD/INR | hybrid vs rolling | +0.0033 | 0.93 | 0.94 | not significant |

On the USD/INR sample of days where both selectors had a valid fit, hybrid versus fixed GARCH is significant at the primary bandwidth ($p=0.0048$) but not at $L=20$ ($p=0.114$); the whole difference comes from two consecutive refit blocks (about 40 days). It is reported as **not robust**.

### 3.4 Order recovery (hybrid, exact order found, $R=500$)

| True model | $n=500$ | $n=1000$ | $n=4000$ | Full-grid BIC at $n=1000$ |
|---|---:|---:|---:|---:|
| ARCH(1), $\alpha=0.4$ | 0.658 | 0.606 | 0.452 | 0.994 |
| GARCH(1,1) | 0.766 | 0.938 | 0.996 | 0.982 |
| GARCH(2,1) | 0.046 | 0.036 | 0.224 | 0.060 |
| GARCH(1,2) | 0.000 | 0.006 | 0.038 | 0.004 |
| GARCH(1,1), Student-t errors | 0.660 | 0.878 | 0.992 | 0.844 |
| iid noise (true (0,0)) | 0.926 | 0.912 | 0.930 | not in its grid |
| AR(1) + GARCH(1,1) | 0.782 | 0.952 | 0.996 | 0.986 |

- For every model except ARCH(1), "nesting" equals "exact" to within 0.01: the failures are **under-fits**. For ARCH(1) the chosen model nests the truth almost always (about 1.0) but is exact only 45 to 66% of the time: the rule **over-fits** to $(2,0)$, $(3,0)$ or $(1,1)$.
- GARCH(2,1) and GARCH(1,2) truths are started at $(1,1)$ by the rule in nearly every run, and both selectors mostly settle there.
- **Cost:** the hybrid fits 1.07 to 1.83 models per series on average; full-grid BIC fits 30.
- The frozen mean rule adds a spurious AR term in about 5% of iid series but 11 to 20% of ARCH/GARCH series and up to 38% with fat-tailed errors.

### 3.5 Why ARCH(1) recovery falls with $n$ (post-hoc diagnostic)

| ARCH(1) $\alpha$ | $n$ | exact | spurious PACF-of-squares spike, lags 2 to 5 |
|---:|---|---:|---:|
| 0.2 | 500 → 4000 | 0.604 → 0.724 | 0.216 → 0.228 (flat) |
| 0.4 | 500 → 4000 | 0.640 → 0.500 | 0.316 → 0.472 (rises) |

For normal-error ARCH(1) the eighth moment of returns is infinite when $\alpha$ exceeds about 0.31 (author's arithmetic), which makes the sample autocorrelation of squares more variable than the $1.96/\sqrt n$ band assumes. The verdict rule fixed in advance printed "supported": the result is **consistent with** that explanation, not a proof. This diagnostic was added after seeing the recovery results and is labelled post-hoc.

---

## 4. Discussion

1. **The cheap method is as accurate here, not better.** On EUR/USD and USD/JPY the hybrid's forecasts equal those of a fixed GARCH(1,1) at every refit, and GARCH beats the rolling variance only by a margin that is not statistically significant. The supported advantage is cost: about 42 fits against 1,260 for the grid on EUR/USD.
2. **The rules are accurate where the truth is GARCH(1,1).** That is also the process the rules default to, and the one most often found on real FX data; but the rules can only propose $(p,0)$ with $p\le3$ or $(1,1)$, so higher-order truths are reached only by escalation, which rarely happens.
3. **More data does not always help.** For a strong ARCH(1) the narrow white-noise band makes chance PACF spikes more frequent as $n$ grows, so recovery falls (0.64 to 0.50 for $\alpha=0.4$).
4. **USD/INR shows why the gate and the fallback exist.** On most refits every fitted model ends on the persistence boundary and is rejected; the selectors there are partly the rolling baseline. The hybrid beats the full grid on INR because the grid's forced fits are poor, not because the rules are sharper.
5. **Limitations to read before citing any number:** noon rates, not closes; the squared return is a very noisy target, so only averaged losses mean anything; no multiplicity correction across 60 tests, and an asymptotic normal reference without small-sample correction; the 95% band assumes light tails and no clustering; the gate uses no degrees-of-freedom adjustment; the true models, omegas and parameters were chosen by the author and cover low orders only; refitting every 20 days is a cost choice, not tuned.

---

## 5. Conclusion

ACF/PACF-driven order selection with a diagnostic gate and bounded escalation is a **cheap and, on these data, equally accurate** substitute for exhaustive BIC search: it fitted roughly 1.1 to 1.8 models per simulated series against 30, and its out-of-sample QLIKE equalled the full grid's on EUR/USD and USD/JPY. It is not shown to forecast better than a fixed GARCH(1,1), and its exact-order accuracy is strong for GARCH(1,1) but weak for ARCH(1) at large $n$ and for higher-order truths. The design choices that support these conclusions are the frozen rules, the no-look-ahead forecasts, the robustness check on the test bandwidth, and the open reporting of the cases where the method fails.

---

## 6. Future Scope

- A heavy-tail-robust or bootstrap band for the ACF/PACF of squares, to address the ARCH(1) failure (a rule change that would need a new calibration and evaluation under the project's change policy).
- A rule that can propose $(2,1)$ and $(1,2)$ directly, or an information-criterion step for $p$.
- A refit-interval sensitivity run and small-sample (Harvey-Leybourne-Newbold) correction for the Diebold-Mariano tests.
- A realised-variance target from intraday data in place of the squared return.
- More pairs, and a multiplicity correction across the comparison table.

---

## References

- Engle, R. F. (1982). Autoregressive conditional heteroscedasticity with estimates of the variance of United Kingdom inflation. *Econometrica*, 50(4).
- Bollerslev, T. (1986). Generalized autoregressive conditional heteroskedasticity. *Journal of Econometrics*, 31(3).
- Box, G. E. P., & Jenkins, G. M. *Time Series Analysis: Forecasting and Control*.
- Diebold, F. X., & Mariano, R. S. (1995). Comparing predictive accuracy. *Journal of Business & Economic Statistics*, 13(3).
- Newey, W. K., & West, K. D. (1987). A simple, positive semi-definite, heteroskedasticity and autocorrelation consistent covariance matrix. *Econometrica*, 55(3).
- Patton, A. J. (2011). Volatility forecast comparison using imperfect volatility proxies. *Journal of Econometrics*, 160(1).
- Sheppard, K. *arch* Python package: https://github.com/bashtage/arch
- Data: Board of Governors of the Federal Reserve System, H.10 release, via FRED (Federal Reserve Bank of St. Louis).
