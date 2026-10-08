# CLAUDE.md

## Project
ATSA mini-project. Topic: "ACF and PACF Driven Order Selection for Daily Foreign Exchange Rate Volatility Analysis".
Planning happens in the claude.ai Project. Coding and debugging happen here.

## Hard rules
1. Never run code: no python, pytest, streamlit, jupyter, pip install, scripts or notebooks. Write and edit files only.
2. Never run state-changing git (add, commit, push, pull, merge, rebase, reset, checkout, stash). Read-only status, diff, log are allowed.
3. End every task with a "Commands to run" bash block. One line before each command says what it does and what output to paste back.
4. Never invent output, metrics, p-values or results. Unrun means unknown.
5. Ask before deleting or overwriting existing files.
6. Every piece of code written or edited (src, tests, notebook cells, app.py, config.yaml keys) must be explained by comments, no exceptions: a module docstring (what the file is for), a docstring on every function and test (what it does, inputs, output), a comment on every logical step (what it does and why, in plain English with the statistics idea), and a comment on every non-obvious line. Blank lines between steps, one idea per block. Code without these comments is not finished. When editing existing code, bring the touched function up to this standard.

## Session start read order
1. CLAUDE.md
2. docs/phaseplan.md
3. docs/decision.md
4. docs/mistakes.md
5. docs/architecture.md
6. Last 5 entries of docs/logs.md

## After every task (same turn)
- Append to docs/logs.md.
- Tick docs/phaseplan.md.
- New design choice -> docs/decision.md.
- Bug or wrong assumption -> docs/mistakes.md.
- Structure, signature or config change -> docs/architecture.md.

## Debug protocol
- User pastes the error.
- State the cause in 1-2 lines, quoting the paste.
- Give the smallest fix as a file edit.
- Give commands to verify.
- Log in docs/mistakes.md if the error is ours.
- If the paste is insufficient, ask for one specific command's output. Never guess.

## Code rules
- Python 3.11+, type hints, short docstrings.
- Readability (sensei style) follows hard rule 6. Notebook code cells open with a "GOAL" comment and a plain-English note on how to read the output.
- Pure functions in src/. No logic in app.py or notebooks.
- Thresholds, lag caps, seeds, dates, pairs live only in config.yaml.
- No look-ahead: any choice or fit uses data up to t only.
- GARCH(p,q): p = lags of squared shocks, q = lags of variances (arch convention, check docs). Mean orders: m (AR), n (MA).
- Returns = log returns x100.
- Seeds come from config.
- Prefer statsmodels / arch / scipy. Hand-roll only the simulation recursion, QLIKE and Diebold-Mariano.
- Smallest change, no extra features, no new dependency without a decision entry.

## Scope
- In: FRED daily FX (EUR/USD, USD/JPY, USD/INR if available), ACF/PACF selector, GARCH fit, gate, rolling forecasts, baselines, Monte Carlo recovery, basic Streamlit dashboard, report.
- Out: deep learning, trading strategies, intraday data, other assets.

## Output style
Short, answer first, only requested files, mark uncertainty as unverified.
