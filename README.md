# GoldAdvisor

A self-hosted quantitative trading dashboard for gold. A background worker fuses market indicators - RSI, volatility, the Gold/Silver ratio, momentum - with AI-driven macroeconomic sentiment (Gemini) into unemotional, short-term BUY / HOLD / SELL signals, using a **Gated Consensus** model: the math proposes the trade, the AI context can only veto it.

> [!IMPORTANT]
> This is a personal analytics tool, not a broker or an advisor. It does not place trades, hold funds, or connect to any brokerage. Every signal is a decision-support artifact for the person running the container - verify independently before acting on it.

## How it works

| Stage | What happens |
|---|---|
| **Ingest** | The worker polls bullion spot rates (metalpriceapi.com) once daily on a scheduled local-time window and persists them to SQLite. |
| **Analyze** | Pure functions in `analytics/` compute RSI, Bollinger %B (volatility), the Gold/Silver ratio band, and momentum/trend-strength - no I/O, 100% unit-tested. |
| **Sentiment** | `ai/news_collector.py` pulls macro headlines; `ai/gemini_orchestrator.py` asks Gemini for a sentiment score, dominant risk factor, and summary, cached per day. |
| **Fuse** | `analytics/signals.py` sums quant votes into a directional bias, then gates it against sentiment. If sentiment is missing or older than `sentiment_max_age_days`, the signal is forced to **HOLD** to protect capital. |
| **Display** | A Streamlit dashboard (`ui/`) renders the verdict, the consensus breakdown, and the "why" - every vote that fed the decision, not just the output. |

Two containers, one shared SQLite (WAL-mode) volume - the worker writes, the UI reads, and either can boot first.

## Stack

Python 3.12+ · Streamlit · pandas · numpy · plotly · SQLite3 (WAL) · Google Gemini API.

## Getting Started

```bash
cp .env.example .env
# fill in GEMINI_API_KEY and METALPRICEAPI_KEY

docker compose up --build
```

The dashboard is served at [http://localhost:8501](http://localhost:8501). The worker runs headless in the background on its own daily schedule.

### Environment variables

| Variable | Purpose |
|---|---|
| `GEMINI_API_KEY` | Google AI Studio credential for Gemini sentiment inference |
| `METALPRICEAPI_KEY` | metalpriceapi.com credential for bullion spot rates |
| `BASE_CURRENCY` | Fiat anchor currency (default `MYR`) |
| `DATA_DIR` | Path for local SQLite persistence |
| `TIMEZONE` | IANA timezone for the worker's scheduled window and staleness display |
| `GEMINI_MODEL` | Gemini model id |

## Development

```bash
python -m venv venv
pip install -r requirements-web.txt -r requirements-worker.txt -r requirements-dev.txt
pytest
```

Analytics modules (`analytics/`) are pure functions - Series and primitives in, values out, no database reads, network calls, or Streamlit code - so they're tested in complete isolation from I/O. The test suite (`tests/`) is phased to match the build order: persistence, worker, analytics, AI, UI, then container integration.

## Repository Layout

```
worker/       Background daemon - scheduling, ingestion pipeline, sentiment pipeline
analytics/    Pure quant functions - RSI, spread, signals, portfolio, risk
ai/           Gemini orchestration + macro news collection
database/     SQLite schema + connection/DAO layer (WAL, idempotent init)
ui/           Streamlit app, theme, charts, presenter, forms
utils/        Shared helpers (UTC-internal / local-edge time handling)
tests/        pytest suite, phased by build stage
```

## Backtest Report

> Historical replay of the quantitative signal engine (`analytics/signals.py`)
> over 25 years of daily gold & silver futures. Generated for paste into README.

### Method

The backtest replays `generate_trade_signal` **day-by-day** using the exact
indicator wiring and default settings the live UI uses (`ui/data_access.py`,
`database/connection.py`):

| Parameter | Value | Source |
|---|---|---|
| RSI period / oversold / overbought | 14 / 30 / 70 | `DEFAULT_SETTINGS` |
| Bollinger deviations | 2.0 | `vol_band_deviations` |
| GSR band window / deviations | 20 / 2.0 | `_GSR_BAND_WINDOW`, `gsr_band_deviations` |
| Momentum ROC window | 10 | `_ROC_WINDOW` |
| Trend R² window / min gate | 20 / 0.50 | `_TREND_WINDOW`, `momentum_r2_min` |
| Quant vote threshold | 2 | `quant_vote_threshold` |

**Data:** (GC=F) and (SI=F), inner-joined on common trading days.

- Period: **2000-08-30 → 2025-12-31** (25.3 years, 6,357 common days; first 20 dropped for indicator warmup → **6,337 active days**).
- Gold close: **$275.60 → $4,337.10/oz**.

**Trading model:** long/flat on gold. `BUY` → enter long, `SELL` → go flat,
`HOLD` → maintain. Return earned on a day only when positioned into it.
**No transaction costs** — default spreads are `0.0`; cost sensitivity noted below.

---

### Headline results

| Metric | Signal strategy | Buy & hold gold |
|---|---:|---:|
| Total return | **+227.2%** | +1,473.7% |
| CAGR | **4.81%** | 11.53% |
| Max drawdown | **−23.2%** | −44.4% |
| Sharpe (daily, ann.) | 0.49 | 0.72 |
| Market exposure | 42.0% | 100% |

**Signal distribution (6,337 days):** BUY **1.4%** (86) · SELL **1.8%** (111) · HOLD **96.9%** (6,140).

**Trade stats:** 31 completed trades · **67.7% win rate** · avg trade **+4.1%**
(avg win +7.6% / avg loss −3.1%) · avg hold **86 trading days**.


---

### Year-by-year

| Year | BUY | SELL | HOLD | Strategy | Buy&Hold |
|---|--:|--:|--:|--:|--:|
| 2000 | 0 | 0 | 64 | 0.0% | −1.3% |
| 2001 | 1 | 10 | 236 | +0.7% | +2.5% |
| 2002 | 2 | 9 | 239 | +16.1% | +24.7% |
| 2003 | 3 | 5 | 242 | +9.5% | +19.6% |
| 2004 | 7 | 3 | 239 | +1.5% | +5.2% |
| 2005 | 2 | 2 | 244 | +3.0% | +18.2% |
| 2006 | 6 | 1 | 242 | +6.3% | +22.8% |
| 2007 | 5 | 6 | 241 | +1.7% | +31.4% |
| 2008 | 3 | 3 | 247 | −7.9% | +5.8% |
| 2009 | 5 | 7 | 240 | +8.7% | +23.9% |
| 2010 | 5 | 1 | 246 | +25.8% | +29.8% |
| 2011 | 2 | 9 | 241 | −6.7% | +10.2% |
| 2012 | 5 | 4 | 241 | +5.4% | +7.0% |
| 2013 | 1 | 6 | 245 | **+4.4%** | **−28.2%** |
| 2014 | 3 | 3 | 246 | +1.4% | −1.5% |
| 2015 | 2 | 2 | 248 | **+6.9%** | **−10.4%** |
| 2016 | 6 | 2 | 242 | −12.8% | +8.5% |
| 2017 | 1 | 2 | 248 | +9.8% | +13.6% |
| 2018 | 3 | 2 | 245 | +2.7% | −2.1% |
| 2019 | 4 | 10 | 238 | +2.0% | +18.9% |
| 2020 | 6 | 4 | 243 | +10.3% | +24.6% |
| 2021 | 5 | 1 | 246 | −6.9% | −3.5% |
| 2022 | 2 | 5 | 244 | −3.4% | −0.4% |
| 2023 | 2 | 3 | 245 | +3.9% | +13.3% |
| 2024 | 2 | 3 | 247 | +25.8% | +27.5% |
| 2025 | 3 | 8 | 241 | +24.1% | +65.0% |

---

## License

[Apache License 2.0](./LICENSE)
