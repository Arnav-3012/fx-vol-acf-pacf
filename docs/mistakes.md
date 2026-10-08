# Mistakes

Format: ID | date | what went wrong | cause | fix | prevention rule.

## Logged mistakes
(none yet)

## Known traps, pre-seeded, not yet hit
- p/q naming swapped between sources (arch: p = squared-shock lags, q = variance lags).
- Look-ahead leakage from choosing the order on the full sample.
- Returns not scaled x100 breaks the optimiser.
- QLIKE ln(0) on zero-return days (r^2 = 0 is fine, but h = 0 or log of zero proxy is not; guard).
- FRED holidays are "." not NaN.
- Ljung-Box degrees of freedom must be adjusted after fitting.
- ACF band assumes white noise and light tails.
