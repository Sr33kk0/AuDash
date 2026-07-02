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

## License

[Apache License 2.0](./LICENSE)
