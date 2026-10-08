# fx-vol-acf-pacf

ACF and PACF Driven Order Selection for Daily Foreign Exchange Rate Volatility Analysis.

Idea: use autocorrelation and partial autocorrelation patterns of daily FX log returns and squared residuals to choose ARMA(m,n)-GARCH(p,q) orders by rule, check the fit with a diagnostic gate, escalate if it fails, and compare out-of-sample variance forecasts against baselines (rolling variance, fixed GARCH(1,1), full-grid BIC) with QLIKE, MSE and Diebold-Mariano tests.

Run instructions: TODO
