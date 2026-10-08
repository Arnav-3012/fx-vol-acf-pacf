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

## D-012 | 2026-10-08
- Choice: DEXINUS (USD/INR) promoted from pairs_optional to pairs. Verified by user's run on 2026-10-08 (n=4190). It is the contrast/stress case (autocorrelated returns, 134 zero returns, excess kurtosis 8.75). Rules are NOT tuned on it.
- Why: Data exists and passes the gate; a harder case tests the selector. Supersedes the "unverified" part of D-003.
- Alternatives: keep optional; cut INR (kill criterion 1, still available).

## D-013 | 2026-10-08
- Choice: "ACF of squares fades fast" = no lag in fade_lag..corr_lags (config: 10..20) has |ACF of squared residuals| outside the 95% white-noise band. ARCH(p) rule also needs PACF of squares significant lag p <= pacf_cut_max_p (3), and no significant PACF lag in p+1..p+quiet_lags (5); otherwise start at (1,1). To be frozen in config.yaml before P3 results (D-007).
- Why: Concrete and testable. A GARCH(1,1) with high persistence keeps squared ACF significant past lag 10, ARCH(1) does not. Band assumes white noise and light tails, so it is a heuristic (unverified on simulated data).
- Alternatives: geometric-decay fit of the ACF; fixed ratio ACF(k+1)/ACF(k).

## D-014 | 2026-10-08
- Choice: Gate Ljung-Box on squared standardised residuals uses model_df=0 (no dof adjustment for estimated GARCH params). Same for Check 1.
- Why: The adjustment is only approximate for squared standardised residuals and with 5/10/20 lags and ~4000 obs the effect is small; adjusting would make the gate slightly stricter. Known simplification, to state in the report.
- Alternatives: model_df = p + q.

## D-015 | 2026-10-08
- Choice: Escalation details. (a) neighbours (p+1,q),(p,q+1) are fitted only if p and q stay <= escalation.cap (3); the lowest-BIC valid fit among start and neighbours is gate-tested. (b) Student-t refit at that order. (c) if still failing, return the lowest-BIC valid fit over all fits, flagged=True. A fit is invalid if omega<=0, any alpha/beta<0 or persistence>=1; invalid fits never win. Constant-variance stop (Check 1) fits vol="constant" and returns order (0,0).
- Why: Interprets D-010 and the P2 spec; bounded at most 4 fits after the start.
- Alternatives: apply t to both neighbours; unbounded search.

## D-016 | 2026-10-08
- Choice: Mean fallback m=1 is kept as is: when the mean rule rejects "constant" (a spike or LB(10) p <= alpha) but no PACF spike sits in 1..max_m, it returns AR(1). To be evaluated in P3 on iid noise (how often does it wrongly add AR(1)?). No change before then.
- Why: Rules are frozen before results (D-007); the behaviour is a known quirk, not a bug found on real data. Under iid noise the 5% band plus LB(10) can trigger it by chance.
- Alternatives: fall back to constant instead; widen to max_m=3.

## D-017 | 2026-10-08
- Choice: Add nbconvert and ipykernel to requirements.txt (dev tooling for executing notebooks inside the project venv).
- Why: .atsa-project has neither (checked its site-packages). `jupyter` on PATH is conda's, whose Python lacks arch, so 02_selector_sim.ipynb would fail there (same cause as M-002). Not used by src/.
- Alternatives: run notebooks with conda and install arch there (pollutes base); copy the cells into a script (no scripts run by me anyway).

## D-018 | 2026-10-08 | Calibration protocol and selection criteria (written BEFORE any calibration number exists)
- Note: the prompt called this D-017, but D-017 is already the nbconvert/ipykernel entry, so P3a entries are D-018, D-019, D-020.
- Choice: Two rules are calibrated on SIMULATED data only (real data untouched, D-007). Protocol: R = calibration.R (100) replications, n = calibration.n (1000), seeds calibration.seed_base + i; eval.seed_base is a different range and is never used here (check_seed_ranges raises on overlap). Candidates and true models are in config.yaml (calibration.*).
  - Fade tolerance (variance.fade_max_spikes): F0 = 0 spikes allowed (current), F1 <= 1, F2 <= 2, counted over lags fade_lag..corr_lags. Scored by exact (p, q) recovery on ARCH(1) alpha 0.4 and GARCH(1,1) alpha 0.1 beta 0.85, n = 1000. A replication with no_valid_fit never counts as recovered. Mean trigger held at M0.
  - Mean trigger (mean.trigger): M0 = current (reject "constant" on any ACF/PACF spike in 1..spike_lags OR LB(10) fails); M1 = reject only when LB(10) fails. Order m = PACF cut-off <= max_m, fallback 1 when LB fails with no spike in range (D-016 behaviour kept). Scored on iid normal (false-AR rate = share with m > 0) and AR(1) phi 0.2 + GARCH(1,1) (AR(1) detection = share with m == 1). Fade held at F0.
- Criteria (fixed now):
  - Fade: pick the candidate with the highest mean of (ARCH(1) exact recovery, GARCH(1,1) exact recovery). Ties go to the fewer tolerated spikes.
  - Mean: pick M1 if iid false-AR (M1) <= 10% AND AR(1) detection (M1) is not lower than M0's by more than 10 percentage points; otherwise M0.
- Why: Recorded before the numbers so the choice cannot be fitted to the results. The 5% white-noise band is too narrow for heavy-tailed squares (log 2026-10-08, P2b findings), so spurious late spikes kill ARCH(p) under F0; the M0 mean trigger fires on chance spikes (D-016).
- Caveats: R = 100 gives a standard error up to about 5 percentage points per rate, so small differences are noise (unverified until run). Omegas (ARCH 0.20, GARCH 0.05) are my choice, and one n only. The winners are frozen in a separate step after the user pastes results; until then config keeps F0 and M0.
- Alternatives: tune on real data (rejected, D-007); score on all four models for both rules; larger R (costlier).

## D-019 | 2026-10-08 | No-valid-fit fallback
- Choice: select_and_fit never raises when every fit is rejected as invalid; it returns the usual dict with no_valid_fit=True, flagged=True, persistence/bic NaN, params {}. (The pre-P3a code already returned in that case; the key is new.) forecast.py (P3, later) must then substitute the rolling 60-day variance (baselines.rolling_window) for that refit and count the substitutions in its output.
- Why: INR hit this on the full sample (all four fits had persistence >= 1). A rolling refit over thousands of windows must not crash on one window, and the count keeps the substitution visible instead of hiding it.
- Alternatives: raise (breaks the rolling loop); silently reuse the previous fit (hides failure, adds state).

## D-020 | 2026-10-08 | Persistence tolerance
- Choice: fit.persistence_tol = 1e-6 in config.yaml. A fit is invalid when persistence (sum of alpha and beta) >= 1 - tol. The persistence of every fit, rejected or not, is written to escalation_log.
- Why: arch constrains the sum to <= 1 (source read, see architecture.md), so the optimiser can end exactly on the IGARCH boundary, where the variance is infinite. The old test ">= 1" could miss 0.9999999 and accept a boundary fit. Logging the value shows how close to 1 a rejected fit was.
- Alternatives: keep ">= 1" (misses boundary fits); a looser tol such as 1e-3 (would reject legitimate very persistent fits; not evaluated, unverified).

## D-021 | 2026-10-08 | Calibration addendum (added AFTER seeing the F0-F2 and M0/M1 results; written before any F3/F4 or extra-model number exists)
- Disclosure: D-018 was fixed before any number. The first run (R=100, n=1000) then gave fade score F0 0.680, F1 0.735, F2 0.780 (ARCH(1) exact 0.39/0.52/0.61) and M0 iid false-AR 0.16 vs M1 0.05. Because the best fade candidate was the largest tolerance tried, F3 and F4 are added below. This is a data-informed extension, not a pre-registered one. The first-run results are kept in results history (logs.md). Nothing is frozen; config defaults stay F0 and M0.
- Fade: add F3 (<= 3 spikes) and F4 (<= 5 spikes). Choose the candidate that maximises the mean of ARCH(1) and GARCH(1,1) exact-order recovery over F0-F4, subject to GARCH(1,1) recovery >= 0.90; ties go to fewer tolerated spikes. (The floor is new; it guards the case the ARCH(1) gain is bought by losing GARCH(1,1).)
- Mean: M1 is chosen by dominance: M1 rejects "constant" only when LB(10) fails, M0 when LB fails OR a spike appears, so M1's triggers are a subset of M0's. In the first run AR(1) detection (exactly m = 1) was equal at 0.93 for both (the any-AR rate was 1.0 for both). The false-AR rate (any m > 0) is reported for all four true models (iid, arch1, garch11, ar1_garch11; for the last one it is a detection rate, truth m = 1). Same calibration seeds for M0 and M1, so the comparison is paired. This replaces D-018's 10% / 10-point test for the mean rule; the first run also satisfies it (M1 iid false-AR 0.05).
- Reporting added: results/calibration_orders.csv (candidate, true_model, start_order, final_order, count) for F0-F4 on arch1 and garch11, to see where ARCH(1) recovery is lost (unverified until run).
- Why: ARCH(1) recovery was only 0.61 at F2 and was still rising; M0 gave 0.39 / 0.44 any-AR on pure ARCH/GARCH series, which iid alone did not show.
- Alternatives: stop at F2 (leaves a possible gain unmeasured); retune the band itself instead of the spike tolerance (a larger change, out of scope here).

## D-022 | 2026-10-08 | PACF cut-off read: calibration round (written BEFORE any cut-off number exists; added AFTER seeing the F0-F4 orders table)
- Disclosure: D-018 and D-021 were fixed before their numbers. This entry is data-informed: the F0-F4 orders table (results/calibration_orders.csv) showed that the remaining ARCH(1) failures at F4 are (2,0) x19 and (3,0) x5, i.e. a spurious PACF-of-squares spike at lag 2 or 3 makes the "last significant lag <= pacf_cut_max_p" read too high, and fade tolerance cannot fix that. No number from the cut-off candidates below exists when this is written. Nothing is frozen; config defaults stay C0, F0, M0.
- Candidates, cut-off read (variance.cutoff_rule): C0 = current: p is the last significant PACF lag <= pacf_cut_max_p. C1 = contiguous: p is the largest k <= pacf_cut_max_p such that the PACF is significant at ALL lags 1..k. For both, p = 0 falls back to GARCH(1,1). Both keep the quiet check (no PACF spike in p+1..p+quiet_lags) and the fade rule. Note: under C1 a PACF with spikes at {1, 3} gives p = 1, and the spike at 3 then makes the quiet check fail, so the start order is (1,1); this is intended, not a bug.
- Grid: cutoff {C0, C1} x fade {F2, F3, F4}, six candidates. Mean rule M1 stays by dominance (D-021). All three rules are frozen in a later step.
- True models scored (calibration only): arch1 (alpha 0.40), arch2 (omega 0.20, alphas 0.30 and 0.25, my choice), garch11 (alpha 0.10, beta 0.85). arch2 is added so a cut-off read cannot win by only ever returning p = 1; it is calibration-only. The real P3 recovery grid stays ARCH(1), GARCH(1,1), (2,1), (1,2). Protocol as D-018: n = 1000, R = calibration.R, calibration seeds, the SAME seeds for every candidate (paired), eval seeds never used.
- Criterion (fixed now): score = mean exact-order recovery over arch1, arch2, garch11. Keep only candidates with garch11 recovery >= 0.90. Pick the highest score; ties (exactly equal scores) go to C0, then to fewer tolerated spikes (F2 < F3 < F4). If the best candidate beats (C0, F3) by less than 0.03 in score, keep (C0, F3). If no candidate meets the floor, keep (C0, F3) and report it.
- Why: The remaining ARCH(1) loss is a cut-off problem. Fixing the rule before the numbers stops the choice being fitted to them. The 0.03 margin means a small gain is not worth leaving the current rule.
- Caveats: R = 100 gives a standard error up to about 5 points per rate (about 3 points for the mean of three rates; pairing helps but is unquantified), so a 0.03 margin is close to noise (unverified). Omega for arch2 and the alphas are my choice; one n only. Six candidates on one set of seeds can pick a lucky one (selection bias, so the winner's score is optimistic); the frozen rules are re-scored on the eval seeds in P3.
- Alternatives: change pacf_cut_max_p to 2 (loses ARCH(3), a different rule); information-criterion choice of p (a new method, out of scope); larger R (costlier).

## D-023 | 2026-10-08 | Rules frozen
- Choice: the selector rules are frozen as (C0, F3, M1) with persistence_tol = 1e-6. config.yaml: variance.cutoff_rule = last_significant (C0), variance.fade_max_spikes = 3 (F3), mean.trigger = lb_only (M1), fit.persistence_tol = 1.0e-6, plus a top-level `frozen` key (date 2026-10-08, decision_id D-023). The other candidates stay in calibration.candidates, commented "calibration only", because notebook 02 reproduces the calibration with them. tests/test_frozen.py pins the four values.
- Criteria outcome (D-021, D-022, applied as written; no criterion changed):
  - Fade and cut-off: (C0, F3) and (C0, F4) tie exactly at mean exact-order recovery 0.683 over arch1/arch2/garch11. The tie goes to fewer tolerated spikes, so F3. C1 is identical to C0 in all 18 cells (gain 0, below the 0.03 margin), so C0 is kept.
  - Mean trigger: M1 by dominance (D-021). Its triggers are a subset of M0's, AR(1) detection is equal (0.93 both), and iid false-AR is 0.05 vs 0.16.
- Evidence (results/calibration_cutoff.csv, exact_order, arch1 / arch2 / garch11, R = 100, n = 1000, calibration seeds):
  - C0,F2 0.61 / 0.45 / 0.95 = 0.670; C0,F3 0.65 / 0.46 / 0.94 = 0.683; C0,F4 0.66 / 0.46 / 0.93 = 0.683. C1 rows identical to C0 rows. GARCH(1,1) floor 0.90 met by all.
  - results/calibration.csv (rule = mean_trigger, any_ar_rate on true m = 0 series): M0 iid 0.16, arch1 0.39, garch11 0.44; M1 iid 0.05, arch1 0.17, garch11 0.18. m_correct on ar1_garch11 0.93 for both. Fade rows F0..F4 on arch1/garch11 (exact_order) are in the same file.
  - results/calibration_orders.csv and results/calibration_cutoff_orders.csv hold the (start order, final order) counts behind the failures.
- Known limits (reported as they are, not fixed):
  - Exact-order recovery at the frozen rules: ARCH(1) 0.65, ARCH(2) 0.46, GARCH(1,1) 0.94. Most ARCH(1)/ARCH(2) misses are (2,0) or (3,0), from spurious PACF-of-squares spikes, because the 5% white-noise band is too narrow for heavy-tailed squares.
  - M1 false-AR rate (m > 0 on a true m = 0 series): 0.05 iid, 0.17 ARCH(1), 0.18 GARCH(1,1). Likely Ljung-Box size distortion under ARCH effects (unverified).
  - Monte Carlo error at R = 100 is up to about 5 points per rate. The winner was picked on the same seeds it was scored on, so its numbers are optimistic (selection bias). Omegas are my choice and there is one n only.
  - Not yet measured on eval seeds: that is P3 task (c).
- Change policy: any later change to a frozen rule or tolerance needs (1) a new decision entry written before the numbers, (2) a rerun of the calibration AND (3) the eval-seed recovery (eval.seed_base, never overlapping calibration seeds). tests/test_frozen.py is updated in the same step. Real data is never used to tune.
- Why: Criteria were fixed before the numbers (D-018, D-021, D-022); applying them mechanically avoids fitting the rule to the result.
- Alternatives: a wider band or an information criterion for p to lift ARCH recovery (a different method, out of scope); larger R before freezing (costlier, would not change the tie rule).

## D-024 | 2026-10-08 | Forecast design (written BEFORE any forecast number exists)
- Choice: (1) EXPANDING window: the forecast for day i uses returns[:i], never a fixed-length window. (2) Same frozen mean rule (rules.mean_order_rule) for ALL GARCH-based selectors (fixed_garch11, acf_only, grid_bic, hybrid). (3) Baselines have no gate and no escalation; their `flagged` is True only when no valid fit exists. The hybrid keeps its own gate flag.
- Why: (1) uses all information available at t and matches the no-look-ahead rule; a short window would add estimation noise unrelated to order choice. (2) isolates the variance-order choice, the topic of the study; otherwise differences could come from the mean model. (3) acf_only is defined as "rule's start order, fitted once".
- Caveats: an expanding window adapts slowly to regime change (unverified effect). rolling_var uses ddof = 0 (np.var), so it is 59/60 of the ddof = 1 sample variance; a constant factor of about 1.7%, not tuned.
- Alternatives: rolling fixed-length window (cheaper, more reactive); selector-specific mean models (confounds the comparison).

## D-025 | 2026-10-08 | Refit schedule
- Choice: the whole selector is re-run every forecast.refit_every = 20 test days. Between refits the (m, p, q, dist) and parameters are kept and only the conditional variance is re-filtered through the new returns with arch's fix(params) and forecast(horizon=1) (baselines.next_variance).
- Why: re-running the selector every day is about 20 times the cost (the hybrid can need up to 5 fits and the grid 30). 20 days is roughly one trading month. Keeping parameters but updating the variance recursion means yesterday's shock still moves today's forecast.
- Caveats: parameters and even the order are up to 19 days stale; 20 is a cost choice, not tuned, and no sensitivity run exists (unverified).
- Alternatives: daily refit (costly); refit only the parameters on a fixed order (a different baseline).

## D-026 | 2026-10-08 | D-019 fallback used in forecasting
- Choice: if a refit gives no valid fit (all fits rejected), every day of that block uses the rolling 60-day variance (baselines.rolling_window, updated daily from returns[:i]). The rows carry no_valid_fit = True and flagged = True; counting refits with the flag gives the substitution count (D-019). This also applies to grid_bic, fixed_garch11 and acf_only.
- Why: a rolling loop must not crash, and the substitution must stay visible instead of being hidden by reusing an old fit.
- Caveats: a selector with many fallbacks is partly the rolling baseline in disguise, so its losses must be read together with the count.
- Alternatives: reuse the previous valid fit (hides failure, adds state); drop the days (unequal samples break DM tests).

## D-027 | 2026-10-08 | Squared return as the variance proxy; output bookkeeping
- Choice: r2 = the squared return of the target day t + 1 is stored next to each forecast h. It is a NOISY proxy: E[r_t^2 | past] = h_t, but with normal errors its standard deviation is about sqrt(2) times h_t (more with fat tails), so a single r2 says almost nothing and only averages (QLIKE, MSE, DM, D-005) are informative. Output columns: date (target day), pair, selector, h, r2, order, models_fitted, flagged, no_valid_fit, refit_date (last training date of the refit in force). models_fitted is written on the first day of each refit block only (0 elsewhere), so its column sum is the total number of fits; flagged and no_valid_fit repeat on every row of the block because they describe the model in force. CSV output (results/forecasts_<pair>.csv), no new dependency.
- Why: realised variance needs intraday data (out of scope, D-005). Counting fits once avoids multiplying cost by 20.
- Alternatives: parquet (new dependency); models_fitted on every row (inflates sums).
- Config note: baselines.rolling_window (60) and baselines.grid_max (5) already existed in config.yaml, so they were NOT duplicated under forecast; forecast gains smoke, smoke_days, n_jobs next to refit_every and horizon.

## D-028 | 2026-10-08 | Forecast evaluation protocol (written BEFORE any loss or DM number exists)
- Choice:
  - Losses (per day, against the squared-return proxy r2, D-027): QLIKE = ln(h) + r2/h is PRIMARY; MSE = (r2 - h)^2 is SECONDARY. r2 is a noisy proxy and MSE is dominated by a few outlier days, so QLIKE is the headline and MSE is reported only as a robustness check. Lower is better. Both are hand-rolled; h <= 0 or any non-finite input raises.
  - Diebold-Mariano: d_t = L_A,t - L_B,t with A = hybrid (or the first-named selector of a pair below). Statistic DM = mean(d) / sqrt(LRV / T). LRV = gamma_0 + 2 * sum_{k=1..L} (1 - k/(L+1)) * gamma_k (Newey-West, Bartlett weights), gamma_k = (1/T) * sum_{t=k+1..T} (d_t - dbar)(d_{t-k} - dbar). Bandwidth L = floor(4 * (T/100)^(2/9)). Two-sided p from the standard normal. No small-sample (Harvey-Leybourne-Newbold) correction. Negative DM means A has the lower loss (A is better).
  - Comparisons (config evaluate.comparisons): hybrid vs fixed_garch11, acf_only, grid_bic, rolling_var; plus grid_bic vs rolling_var. Raw p-values are reported. NO multiplicity correction is applied (5 comparisons x 2 losses x 2 samples x 3 pairs = 60 tests per full table); the report must say so, and a small p in one cell is not evidence on its own.
  - Samples: PRIMARY = all test days (a day on which a selector used the rolling-variance fallback still counts, D-018/D-026). SECONDARY (common_valid) = only days on which BOTH selectors of the pair had a valid fit (fit_status == valid), which removes the fallback days.
  - Degenerate case: if the two h series are identical (max abs diff exactly 0) or the loss differential has zero variance, status = "identical" and no DM or p is reported (NaN). Guards also give status "too_few_days" when T is below evaluate.dm.min_days or not above L.
  - Fit-failure bookkeeping (observation only, no behaviour change): the per-day CSV gains refit_models (fits spent in the refit in force, repeated on every row of the block, unlike models_fitted which is counted once), fit_status (valid | no_valid_fit), reject_reason (distinct reasons among the fits REJECTED in that refit, semicolon-separated; labels are the existing selector._valid strings: "omega<=0", "negative alpha/beta", "persistence>=1-tol"; empty when nothing was rejected), rejected_persistence (largest persistence among fits rejected for persistence, NaN if none). "Optimiser failure" is NOT captured: no code path rejects a fit for it today, and recording arch's convergence flag would mean editing selector.py's log. Left out on purpose.
  - Table definitions: escalation_rate = share of refits with refit_models > 1; modal_order_share = share of refits whose order equals that selector's most common order (NaN for rolling_var); agree_grid = share of refits whose order string equals grid_bic's at the same refit_date (NaN for rolling_var); fallback_share = share of refits with fit_status no_valid_fit; valid_day_qlike = mean QLIKE over the selector's own valid days. For a no_valid_fit refit the logged order is the rule's proposal, not a fitted model, so modal_order_share and agree_grid include such refits (stated limit).
  - Rules stay frozen (D-023); nothing here may change a rule.
- Why: Fixing the loss, the test, the samples and the comparison list before any number exists stops the analysis from being steered by results. Newey-West is needed because one-step loss differentials are autocorrelated when volatility is persistent.
- Caveats: the L rule and the normal reference are asymptotic (T = 838 here; no small-sample correction, unverified how large the size distortion is). The Bartlett LRV is non-negative, but a very small LRV makes DM huge, hence the guards. Squared-return proxy noise remains (D-027). Where two selectors pick the same order, their h are identical (seen on EUR/USD and USD/JPY in the P3(a) log) and the comparison is degenerate by design.
- Alternatives: realised-variance proxy (intraday data, out of scope); Holm or Bonferroni correction (not applied, raw p shown instead); HLN small-sample correction (not requested); a Model Confidence Set (new method, out of scope).

## D-029 | 2026-10-08 | P3(b) robustness and observation amendments (written BEFORE any rerun number; amends the D-028 definitions below, nothing else in D-028)
- Disclosure: the D-028 tables were already read (log 2026-10-08). So this is a post-hoc robustness addition, not a pre-registered one. The primary DM numbers (L from the D-028 formula) are NOT changed and stay the headline.
- A1 DM bandwidth sensitivity. dm_table gains two columns, dm_L20 and p_L20: the same DM test with the Newey-West bandwidth set to L = forecast.refit_every (20) instead of the formula. Why 20: the loss differential d_t is built from forecasts whose parameters and order are refreshed every 20 days (D-025), so its dependence plausibly reaches about one refit block; the formula gives L = 6 at T = 838. The names assume refit_every = 20 (a test pins this). Rule for the report: a result is called ROBUST only if the two-sided p is below 0.05 under BOTH L (primary p and p_L20); significant under one only is reported as "not robust to the bandwidth". 0.05 is the level already used throughout (gate.alpha, mean.alpha). dm_L20 and p_L20 are NaN when the primary status is not "ok", when the h series are identical, or when 20 is not below T.
- A2 loss_table definitions. escalation_rate is NaN for the selector named evaluate.grid_selector (grid_bic): it always fits 30 models, so "more than one fit" is true by construction and the rate (always 1) says nothing. agree_grid is now computed ONLY on refits where BOTH the selector and grid_bic had fit_status valid (a no_valid_fit refit logs the rule's proposal, not a fitted model, D-028 limit); new column n_both_valid = number of such refits (NaN for rolling_var, which has no order). agree_grid is NaN when n_both_valid is 0.
- A3 Observation only. (1) The forecast CSV gains a column `dist` (error distribution of the model in force: "normal" or "t"; empty when there is no model, i.e. rolling_var or a no_valid_fit refit). It is read from the selector's own spec, nothing is recomputed. (2) New table results/inr_hybrid_vs_fixed.csv (evaluate.block_pair = DEXINUS, evaluate.block_compare = [hybrid, fixed_garch11]): one row per refit block in which BOTH selectors had a valid fit. Columns: refit_date, hybrid_order, hybrid_dist, fixed_garch11_order, n_days, block_qlike_diff = SUM over the block's days of (QLIKE_hybrid - QLIKE_fixed), share_of_total = block_qlike_diff / sum of block_qlike_diff over the listed blocks. Sums (not means) so the shares add to 1. A negative block value means hybrid was better in that block. If the total is close to zero or the blocks have mixed signs the shares can be large or negative; they are reported as they are. This is a description of where the INR common-valid difference comes from; it tests nothing.
- A4 The regression check (max abs diff in h against forecasts_<pair>_p3a.csv) must still print 0.0; neither the new column nor the new tables touch h.
- Why: the INR common-valid DM results (hybrid vs fixed, hybrid vs grid_bic) are the main "significant" findings and rest on one bandwidth rule and the raw normal reference, with 60 uncorrected tests; a second bandwidth is the cheapest check that costs no new fits. The grid_bic escalation rate and the agreement over fallback refits were misleading by construction.
- Caveats: L = 20 is a judgement, not tuned and not a standard rule; with T = 838 it uses 20 of 838 autocovariances (fine) but for the common_valid samples (T about 200-280) the DM statistic at L = 20 may be less reliable (unverified). Two bandwidths are still not a size study. No multiplicity correction is added.
- Alternatives: automatic bandwidth (Andrews/Newey-West data-driven, a new method); HLN small-sample correction; a bootstrap test.

## D-030 | 2026-10-08 | Order-recovery experiment on the EVAL seeds (written BEFORE any run; rules frozen, D-023)
- Choice (true models, config recovery.models; omega = 1 - persistence in every case, so the unconditional variance is 1; p = lags of squared shocks, q = lags of variances, the arch convention):
  - arch1: ARCH(1), alpha 0.40 (true order (1, 0))
  - garch11: alpha 0.10, beta 0.85 (true (1, 1))
  - garch21: alphas (0.05, 0.05), beta 0.85 (true (2, 1))
  - garch12: alpha 0.10, betas (0.50, 0.30) (true (1, 2))
  - garch11_t: GARCH(1,1) 0.10 / 0.85 with Student-t innovations, nu = 6, scaled to unit variance (true (1, 1))
  - controls: iid N(0, 1) (true (0, 0), true m = 0); ar1_garch11: AR(1) phi 0.20 with GARCH(1,1) 0.10 / 0.85 shocks (true (1, 1), true m = 1).
  Omega is not tuned and these are NOT the calibration models (calibration.models used omega 0.20 / 0.05 and a different arch1 scale), so this is an out-of-calibration check of the frozen rules.
- Design: lengths n in {500, 1000, 4000} (sim.n); R = 500 (sim.R); replication i uses seed eval.seed_base + i (check_seed_ranges guards disjointness from the calibration seeds); calibration seeds are never used. The SAME seeds are used for every true model and every n, so the series at different n share their first innovations and the rates at different n are positively correlated (the Monte Carlo SE of each single rate is unaffected; differences across n are tested more sharply than independent runs would be, but are not independent). Selectors: hybrid (select_and_fit as in baselines.hybrid) at every n; grid_bic (baselines.grid_bic, p 1..5, q 0..5, lowest valid BIC) at n = 1000 only (recovery.grid_n), because it costs 30 fits per series. Both use the frozen mean rule.
- Metrics (all are shares over the R replications; Monte Carlo SE = sqrt(p(1 - p) / R) is reported for every rate, 0.022 at p = 0.5 and R = 500):
  - exact = final (p, q) equals the true (p, q) AND the run had a valid fit (a no_valid_fit replication never counts, as in D-018).
  - nesting = final_p >= true_p AND final_q >= true_q AND a valid fit. It says "the chosen model contains the truth", which is weaker than exact: an over-parameterised model still nests it. Hand checks: a final (2, 0) nests true ARCH(1) = (1, 0); a final (1, 1) does NOT nest true (2, 1); a final (3, 1) does. Caveat: GARCH(p, q) with larger orders nests the smaller one only by setting the extra coefficients to zero, so nesting is about the model class, not the parameter estimates; and for the iid control (0, 0) every valid fit nests, so nesting carries no information there.
  - family = the START order (the rule's proposal before the gate and escalation, escalation_log[0]) has (start_q >= 1) == (true_q >= 1), i.e. the rule chose the right model family (pure ARCH versus has-a-variance-lag). Counted over all R replications (the start order exists even when no fit was valid). Hybrid only (grid_bic has no start order: NaN).
  - any_ar_rate = share with a chosen AR mean order m > 0. On the true m = 0 models it is the false-AR rate; on ar1_garch11 it is the AR detection rate (same reading as D-021).
  - gate_pass = share whose final fit passed the diagnostic gate (False when no valid fit); escalation_rate = share with models_fitted > 1; mean_fits = mean models_fitted; flagged = share flagged (hybrid: gate failed after escalation or no valid fit; grid_bic: no valid fit); no_valid_fit = share with every fit rejected. For grid_bic gate_pass and escalation_rate are NaN (no gate, and it always fits 30 models).
- Outputs: results/recovery_table.csv (one row per true model x n x selector, rates with their _se columns) and results/recovery_orders.csv (true_model, n, selector, start_order, final_order, count; grid_bic start_order is "n/a"; for a no_valid_fit replication the order shown is the rule's proposal, not a fit). Written by notebooks/03_results.ipynb. Run time goes to results/run_time_recovery.txt. config recovery.smoke (default true) = R 20 at n = 1000 only; the full run needs smoke false.
- Pre-stated expectations (not tested here, only written down so they cannot be adjusted later): from the calibration at n = 1000 (R = 100, calibration models) exact recovery was about 0.65 for ARCH(1) and 0.94 for GARCH(1,1) and the misses were mostly (2, 0) and (3, 0); I therefore expect exact recovery of ARCH(1) to be clearly below that of GARCH(1,1), nesting to be clearly above exact for ARCH(1), and the iid control to show a false-AR rate near the 0.05 of M1. These are expectations, not claims. Nothing is concluded before the run.
- Why: the frozen rules were tuned on simulated data with a single design (D-023: "not yet measured on eval seeds"); a separate seed range, more true models, three lengths and a heavy-tailed case tells how much of the calibration recovery carries over. A selector cannot be called a method for ACF/PACF-driven order selection without this table.
- Caveats: R = 500 gives SE up to 0.022 per rate; the true models and omegas are my choice and cover only low orders; the t case has nu = 6 only; the AR control has one phi; hybrid and grid_bic are compared at one n only; the hybrid can escalate to orders the rule did not propose, so exact and family measure different things; nesting counts over-parameterisation as success. Cost: unrun, so unmeasured (estimate: grid_bic 30 fits x 500 x 7 models at n = 1000 is about 105,000 fits, plus the hybrid at three n; the smoke mode exists to time it first).
- Amendment 2026-10-08 (after the smoke run, no full-run number exists yet; a limit of the design, not a rule change): grid_bic searches p in 1..5, q in 0..5, so (0, 0) is not in its grid. On the iid control its exact rate is 0 by construction and its nesting rate is trivially 1; neither says anything about its quality. Read the iid control for the hybrid only (and for the false-AR rate, which is the same for both because they share the mean rule and the seeds). Likewise any_ar_rate is identical for hybrid and grid_bic in every cell, by design, so it is one measurement, not two.
- Alternatives: re-tune the rules on these results (forbidden by D-023, would need a new decision plus a rerun); grid_bic at all n (cost); independent seeds per n (would need a larger seed range, kept simple instead); out-of-sample forecast loss as the success measure (that is P3(b)).

## D-031 | 2026-10-08 | Post-hoc diagnostic: why ARCH(1) exact recovery falls with n (post-hoc, added after seeing eval recovery; written BEFORE any diagnostic number exists)
- Disclosure: POST-HOC. The D-030 eval run (log 2026-10-08, "Full recovery run read") showed ARCH(1) alpha 0.4 exact recovery FALLING with n (0.658 / 0.606 / 0.452 at n = 500 / 1000 / 4000) while GARCH(1,1) rises. That finding was not pre-stated; this diagnostic is a reaction to it. It is a diagnostic only: it changes no rule, threshold, frozen value (D-023) or existing result, and its outcome is never used to change a rule. Any rule change would need the D-023 change policy (new decision, calibration rerun, eval rerun).
- Hypothesis: the white-noise band 1.96 / sqrt(n) is too narrow for the PACF of the SQUARES when the 8th moment of the returns is infinite. For normal-error ARCH(1) with shock variance omega + alpha * e^2, E[e^8] is finite only if 105 * alpha^4 < 1, i.e. alpha < (1/105)^(1/4) = about 0.31 (my arithmetic from the normal moments 3, 15, 105; unverified). The sample autocorrelation of squares has a variance that needs the 8th moment, so above that alpha the band understates its spread and chance PACF spikes at lags >= 2 (where the true PACF of squares is zero, because e^2 follows a weak AR(1)) should be more frequent than 5% per lag, and the surplus may grow with n. Such a spike makes the "quiet" check fail or lifts the cut-off p, which is the (1,1), (2,0), (3,0) pattern seen in recovery_orders.csv. Alpha 0.4 is above the threshold; alpha 0.2 is below it.
- Design:
  - True models: ARCH(1) with alpha in {0.2, 0.4} (config diagnostic.alphas), omega = 1 - alpha (unit unconditional variance, as in D-030, so alpha 0.4 is the SAME process as recovery.models.arch1, replicated on new seeds).
  - Lengths n in {500, 1000, 4000} (diagnostic.n), R = 500 (diagnostic.R), seeds diagnostic.seed_base + i with diagnostic.seed_base = 3000000, i < R. Calibration uses 1000000.. (+100) and eval 2000000.. (+500), so the three ranges are disjoint; a new function checks them pairwise, and a test pins it. The same seeds are used at every n and alpha (paired cells, as in D-030).
  - The hybrid selector runs through the existing recovery code (order_recovery_experiment and recovery_metrics, model_set "recovery") with the frozen rules; only the true-model table is extended on a copy of the config.
- Metrics (shares over the R replications; Monte Carlo SE = sqrt(p(1 - p) / R), up to 0.022 at R = 500):
  - exact and nesting: exactly as D-030 (hybrid, a no_valid_fit replication never counts).
  - false_spike_rate = share of series with at least one significant PACF-of-squares lag in lags 2..5 (diagnostic.lag_min = 2, lag_max = 5) on the SIMULATED RETURNS: constant mean (series minus its sample mean, as the rule's m = 0 residuals), no model fit, PACF of the squares from the same acf_pacf_band call and the same band (variance.corr_lags, band_confidence 0.95, band 1.96 / sqrt(n)) as the rules. It is computed on the same seeds as exact. Lags 2..5 follow the spec; the rule's own quiet window after p = 1 would be 2..6 (variance.quiet_lags = 5), so the diagnostic is slightly narrower than the rule.
- Fixed interpretation (set now; "change" = value at n = 4000 minus value at n = 500, from the two end lengths only; tol = diagnostic.change_tol = 0.05):
  - alpha 0.2 exact does not fall: change >= -tol.
  - alpha 0.4 exact falls: change < -tol (the exact complement of the line above, so "falls" means falls by more than 0.05).
  - alpha 0.4 false_spike_rate rises: change > +tol.
  - Hypothesis SUPPORTED if all three hold; otherwise the report says "unexplained". "Supported" means consistent with the hypothesis, not proved. 0.05 is a judgement (about 1.6 SE of a difference of two independent rates at R = 500, p = 0.5), not tuned; the "falls" and "rises" thresholds were not given in the spec and are my choice, fixed here before the numbers. The verdict is computed by simulate.diagnostic_verdict, not by eye.
- Outputs: results/diagnostic_arch1.csv with alpha, n, R, exact, nesting, false_spike_rate and one Monte Carlo SE per rate (exact_se, nesting_se, false_spike_se; one `se` column cannot be right for three rates). Written by one cell of notebooks/03_results.ipynb. Config: diagnostic.enabled (default true), seed_base, plus R, n, alphas, lag_min, lag_max, change_tol and test settings (seeds, lags, thresholds live only in config.yaml).
- Why: the finding that more data makes recovery worse is unexpected and the report needs either a tested reason or an honest "unexplained". The check is cheap (about 6 hybrid cells of 500 series) and touches no rule.
- Caveats: (1) The diagnostic covers PACF spikes at lags 2..5 only. The other route to a wrong start order, ACF-of-squares spikes in lags 10..20 (the fade rule, F3 tolerates 3), is not measured, so a "supported" verdict says nothing about it, and an "unexplained" verdict may only mean the fade route matters. (2) Two alphas on one model family; one omega convention. (3) The false-spike series have a constant-mean residual, whereas the rule may use AR residuals when m > 0 (about 10-20% of ARCH series in D-030). (4) The hybrid's exact rate also depends on the gate and escalation, not on the start order alone. (5) End-point changes of rates with SE up to 0.022 each; paired seeds make them positively correlated across n but the difference is still noisy (unverified how much). (6) The 8th-moment threshold is my arithmetic, unverified; it was not simulated. (7) Nothing was run when this was written; no diagnostic number exists.
- Alternatives: a Monte Carlo of the band's coverage by itself on the true PACF of squares at many alphas (more cells); a heavy-tail-robust band or bootstrap band (a rule change, forbidden here); explaining the fall by the fade rule instead (a second diagnostic, not done).

## D-032 | 2026-10-08 | P4 dashboard structure: src/plots.py and src/dashboard.py (written BEFORE any app run)
- Choice: (1) src/plots.py holds four pure figure builders (price_and_returns, correlogram_2x2, forecast_vs_abs_return, final_order_bars). Each takes data and returns a matplotlib `Figure` built with the `Figure` class directly (no pyplot), so there is no global figure state, no display backend in tests, and nothing to close. It reads no file and no config. (2) A second new module, src/dashboard.py, holds the pure non-figure helpers: as-of cut, summary and diagnostic tables, rule readout, selection tables, CSV readers, live recovery wrapper. (3) app.py only creates widgets and calls src/ functions; captions, defaults, limits and the missing-file command are in config.yaml under `app`. (4) Slow calls use st.cache_data keyed on widget values (pair, as-of date, model, n, R); cached CSV reads are keyed on the file's modified time so a rewritten or newly created file is re-read. The full-grid BIC and the live Monte Carlo run only on a button click, and the result stays while the settings stay.
- Deviation to confirm: the spec listed app.py, src/plots.py, config.yaml, tests and docs. A second new src file (dashboard.py) was added because app.py may hold no logic and plots.py is figures only, while the summary table, the as-of slice, the readout and the CSV readers need a home. The alternative was to edit data.py, rules.py or selector.py; dashboard.py leaves every existing module untouched. It does import the private selector._mean_resid (same pattern as baselines.py) so the Diagnose readout uses the selector's own residual step.
- Simulate tab: seeds are fixed to eval.seed_base + i (not a widget), so a live run with R replications reproduces the first R of the saved eval run; R is capped at app.simulate.max_live_R = 50 by the widget and again inside dashboard.live_recovery (ValueError). Hybrid only, as specified. The saved row is shown with its own Monte Carlo SE; no live-versus-saved test is made.
- Why: keeps the presentation layer thin and testable (figures and tables without Streamlit), and keeps every number and sentence a user reads either computed by src/ or read from config or a saved CSV, never typed into app.py.
- Caveats: live runs at n = 4000 may take about a minute or more (unmeasured, unverified); AppTest support for a date slider is assumed from the installed source, not run. Cache keys do not include config.yaml, so after editing the config the Streamlit cache must be cleared (C in the app menu, or restart).
- Alternatives: put the helpers into plots.py (mixes figures and tables); edit data.py/selector.py/rules.py (touches frozen-rule modules); show only a rules readout without the fit on the Diagnose tab (the spec asked for the reason strings).

## D-033 | 2026-10-08 | The as-of rule of the dashboard (no look-ahead in the UI)
- Choice: the sidebar as-of date is applied ONCE, by dashboard.slice_asof (index <= as-of, so the as-of day itself is included), to the price and the return series. The Data, Diagnose and Select tabs receive only the cut series. The default is the last date (use everything). The earliest allowed date is the app.min_obs-th return (500), so the rules never run on a handful of points. select_and_fit and grid_bic are cached on (pair, as-of date). The Forecast tab does NOT use the as-of date: it shows saved forecasts that were made with an expanding window and no look-ahead (D-024), and says so in its caption. Because returns are a causal transform of prices (a log difference of consecutive days), cutting the returns at the as-of date equals computing returns from the cut prices.
- Why: one cut in one place is easy to test (tests/test_app.py overwrites everything after the as-of day and checks the cut does not change). Applying the slider to saved forecasts would hide the fact that those rows were produced offline.
- Caveats: the as-of date is a calendar date, so a weekend as-of keeps data to the previous trading day. The Select tab result at the last date uses the whole history, including the test period of the forecasts (the Select tab is a description of one fit, not a forecast evaluation). 500 is a judgement, not tuned.
- Alternatives: also filter the Forecast tab to forecasts dated <= as-of (hides that they were pre-computed; could show a refit the user could not have run on that date from this tab); allow any date (rules fail on very short samples).

## D-034 | 2026-10-08 | P4b: Plotly for every dashboard figure, plain labels and explanations from config (written BEFORE any run)
- Choice: (1) add `plotly` to requirements.txt (unpinned, like the other entries) and replace every matplotlib figure in the app by a plotly.graph_objects.Figure. This supersedes D-032 item 1 (matplotlib Figure builders); the rest of D-032 stands. matplotlib stays in requirements.txt because the notebooks use it, but no module the app imports uses it any more. (2) src/plots.py stays pure: one function per chart, data in, Figure out, no file or config reads, no st.*. (3) Streamlit call: `st.plotly_chart(fig, width="stretch")`. Read from the installed streamlit 1.65.0 source (elements/plotly_chart.py, lines 428-445): the signature is `plotly_chart(figure_or_data, use_container_width=None, *, width="stretch", height="content", theme="streamlit", key=None, on_select="ignore", ...)`, so `width` is the keyword-only argument and `use_container_width` is a leftover optional positional one. Whether `use_container_width` is formally deprecated in this version was not checked. (4) Every figure has a plain-sentence title with no raw variable names (no arch1, no "n = 1000", no "R = 20"), axis titles with units, hover text with the exact value, and the Okabe-Ito colour-blind-safe palette. Colour is never the only cue: spikes and failing tests also use a hatch pattern, and the true order is a green band plus a legend entry containing "True order". (5) All explanation text (a "How to read this tab" expander per tab, a sidebar glossary), plain column labels and plain value labels live in config.yaml under `app` (explain, glossary, columns, value_labels, rate_labels, selector_labels, model_labels, param_labels, percent_columns). app.py only renders them. Numbers inside explanation text are placeholders like {saved_R} that dashboard.explain_values fills from the results CSVs, the loaded data or the config; a missing source prints "n/a", never a typed number. (6) Tables use st.column_config for labels and one-decimal percentages; values stored as fractions are multiplied by 100 first (dashboard.scale_percent).
- Why: a marker who has not seen the notebooks needs to hover, zoom and toggle series, and needs the reading instructions on the page; keeping text in config keeps app.py free of content and keeps the numbers traceable to files.
- Caveats: plotly is NOT installed in .atsa-project when this is written (site-packages listing), so every plotly call here is from memory of its API, version unknown, and unverified until the user installs it and runs the tests. st.plotly_chart with the default theme "streamlit" may restyle fonts and background; explicit trace colours are kept. Hatch patterns (marker.pattern) need plotly 5.15 or newer (from memory, unverified). The config text has no automatic check that its placeholders exist; an unknown placeholder prints "n/a".
- Alternatives: Altair (already bundled with Streamlit, so no new dependency; weaker for range sliders, hatching and subplot grids, and the user asked for plotly); keep matplotlib and add st.pyplot captions (no hover or zoom).
