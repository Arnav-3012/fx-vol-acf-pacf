# Logs

Append-only. Entry format:

```
## date | phase | title
Done:
Files touched:
Commands I ran and result:
Open issues:
Next:
```

---

## 2026-10-08 | P0 | Planning complete, no code yet
Done: Topic, scope, phase plan, decisions D-001..D-010 and module contracts fixed in claude.ai Project. Repo scaffolded with stubs only.
Files touched: all scaffold files (CLAUDE.md, README.md, config.yaml, requirements.txt, .gitignore, docs/*, src/*, app.py, tests/__init__.py, .gitkeep files).
Commands I ran and result: none yet (bootstrap commands pending, see P0 task output).
Open issues: DEXINUS availability unverified. statsmodels/arch versions unverified. notebooks/ is empty and needs `mkdir` (git will not track it until it has a file).
Next: P1, data.py, stat_tests.py, correlogram.py, 01_eda notebook.

## 2026-10-08 | P0 | Environment installed, versions recorded
Done: venv created and requirements installed by user. Versions pasted by user: arch 8.0.0, numpy 2.5.3, pandas 3.0.6, scipy 1.18.1, statsmodels 0.15.0.
Files touched: docs/logs.md, docs/phaseplan.md.
Commands I ran and result: (user) pip list | grep -iE "statsmodels|arch|pandas|numpy|scipy" -> versions above. Python version, git status and commit result not yet pasted (unverified).
Open issues: pandas 3.x (copy-on-write, string dtype default) and arch 8.0.0 / statsmodels 0.15.0 APIs are newer than my training data; check docs before relying on signatures (arch p/q convention especially). DEXINUS still unverified.
Next: confirm commit, then P1 data.py.

## 2026-10-08 | P1 | Data, tests, correlograms, EDA notebook written (not run)
Done: Implemented data.py (load_config, load_fx, to_log_returns), stat_tests.py (adf_kpss, ljung_box, arch_lm), correlogram.py (acf_pacf_band, significant_lags), tests/test_p1.py, notebooks/01_eda.ipynb (cells 1-9, no outputs). Added config keys fred.url_template, pairs_optional, eda.nlags, eda.sig_window (extra, to avoid hard-coding the 1..20 window), paths.*. D-011 recorded. Paths resolve against project root so the notebook works from notebooks/.
Files touched: config.yaml, src/data.py, src/stat_tests.py, src/correlogram.py, tests/test_p1.py, notebooks/01_eda.ipynb, docs/logs.md, docs/phaseplan.md, docs/decision.md, docs/architecture.md.
Commands I ran and result: none. Nothing was executed.
Open issues: FRED URL, DEXINUS availability, statsmodels 0.15 / pandas 3 signatures all unverified. jupyter/nbconvert/nbformat/ipykernel not in requirements.txt (unverified whether installed). P1 gate not ticked, planner decides after outputs.
Next: user runs the commands, pastes outputs; planner fills the gate decision.

## 2026-10-08 | P1 | Ran tests and EDA notebook
Done: User ran P1 commands; outputs read from the executed notebook.
Files touched: docs/logs.md (notebooks/01_eda.ipynb now holds outputs).
Commands I ran and result: (user) versions 0.15.0 8.0.0 1.18.1 3.0.6 2.5.3; pytest 5 passed; nbconvert executed without error. Data: DEXUSEU, DEXJPUS n=4191, DEXINUS n=4190, 2010-01-04..2026-10-02. Returns stationary (ADF p 0.0, KPSS p>=0.1) all pairs. LB(10) squares p ~0 and ARCH-LM(5) p<1e-17 all pairs; 19-20 of first 20 squared-return ACF lags significant. DEXUSEU/DEXJPUS returns show no autocorrelation (LB(10) p 0.33, 0.18); DEXINUS does (p ~3e-8), 134 zero returns, excess kurtosis 8.7.
Open issues: statsmodels FutureWarnings for adfuller/het_arch (harmless). Correlogram figures not inspected by me. P1 gate left for planner.
Next: planner decides P1 gate, then P2.

## 2026-10-08 | P1 | Added explanatory comments to 01_eda notebook
Done: Line-by-line comments and short ADF/KPSS, ACF/PACF, Ljung-Box, ARCH-LM explanations added to code cells 1-8. Code logic unchanged; stored outputs kept.
Files touched: notebooks/01_eda.ipynb, docs/logs.md.
Commands I ran and result: none of the project code; cell sources syntax-checked with ast.parse only (ok).
Open issues: none new.
Next: unchanged.
