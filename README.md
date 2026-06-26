# ETF Trading Bot (Zerodha + yfinance)

A small personal trading bot for Indian ETFs on the NSE, using the Zerodha
Kite Connect API for order placement and `yfinance` for price data.

**Status:** Personal project, runs in dry-run mode by default. Not financial
advice — see [Disclaimer](#license--disclaimer) below.

---

## What It Does

- Logs into Zerodha **once** via browser OAuth when started.
- Then loops continuously (default: every 20 minutes) for as long as you
  leave it running:
  - **Sells** any held ETF that's ≥10% above its recorded buy price.
  - **Buys** ETFs currently ≥5% below their 10-day high (one position per
    symbol — it won't average down or add to an existing holding).
- Runs in **dry-run mode by default** — logs what it *would* do, places no
  real orders, until you flip a switch in `trader.py`.
- Stop it any time with `Ctrl+C` — it shuts down cleanly.

This is **not** a scheduled job — it's a single long-running process. There's
no built-in market-hours check, so it's on you to start and stop it around
the trading day (or leave it running, but see the warning under
[Known Limitations](#known-limitations) about overnight token expiry).

---

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Create your own `config.py`** in the project root (not included — see
   [Configuration](#configuration) below).

3. **Validate ETF tickers:**
   ```bash
   python3 quick_test.py
   ```

4. **Run in dry-run mode** (default):
   ```bash
   python3 main.py
   ```
   Watch the log. Nothing real happens yet — `DRY_RUN = True` in `trader.py`.

5. **Go live** only when you're confident:
   - Open `trader.py`, set `DRY_RUN = False`.
   - Make sure your Zerodha account has CNC trading enabled and sufficient
     funds (see [Funding](#funding) below).
   - Run `python3 main.py` again.

---

## Configuration

`config.py` is **not included in this repo** because it holds your Zerodha
API credentials. Create it yourself in the project root:

```python
# config.py
API_KEY = "your_zerodha_api_key"
API_SECRET = "your_zerodha_api_secret"
EXCHANGE = "NSE"
BUDGET_PER_TRADE = 10000     # Rs. per trade
MAX_TOTAL_FUNDS = 100000     # Rs. total capital the bot will deploy
LOG_FILE = "bot.log"
```

Get your API key/secret from the
[Zerodha Kite Connect developer console](https://developers.kite.trade/).
Kite Connect API access requires a separate paid subscription from your
regular trading account — check current pricing on Zerodha's site.

**Never commit `config.py`.** See [Security](#security) below.

---

## The ETFs Being Scanned

Defined in `per_scanner.py` → `POPULAR_ETFS`:

| Ticker | Tracks |
|---|---|
| NIFTYBEES.NS | Nifty 50 |
| JUNIORBEES.NS | Nifty Next 50 |
| SETFNN50.NS | SBI Nifty Junior |
| GOLDBEES.NS | Gold |
| MON100.NS | Nasdaq 100 (Motilal Oswal) |
| INFRABEES.NS | Infrastructure |
| BANKBEES.NS | Nifty Bank |
| PSUBNKBEES.NS | PSU Bank |
| NEXT50IETF.NS | Nifty Next 50 (ICICI Prudential) |
| ITBEES.NS | Nifty IT |

Edit this list directly in `per_scanner.py` to add or remove ETFs — and
update the same list in `quick_test.py` if you do, since it keeps its own
copy for ticker validation.

---

## Files in This Repo

| File | Purpose |
|---|---|
| `main.py` | Entry point. Logs in once, then loops the scan-and-trade cycle. |
| `per_scanner.py` | Scans ETFs via `yfinance` for buy/sell signals. |
| `trader.py` | Places (or simulates) orders via Zerodha Kite Connect. |
| `Per_Gen.py` | Zerodha OAuth login flow (local Flask callback server). |
| `holdings.py` | Manages `etf_holdings.json`, your local holdings record. |
| `quick_test.py` | Standalone script to confirm all ETF tickers resolve via `yfinance`. |
| `requirements.txt` | Python dependencies. |
| `SETUP_GUIDE.md` | Step-by-step setup walkthrough. |

**Not in this repo** (created locally, or excluded — see `.gitignore`):
- `config.py` — your API credentials (you create this yourself)
- `etf_holdings.json` — your local holdings record (auto-created)
- `*.log` — runtime logs (auto-created)

---

## Funding

The bot needs actual settled funds in your Zerodha trading account before
it can place live buy orders — `MAX_TOTAL_FUNDS` in `config.py` is a
**self-imposed cap the bot tracks locally**, not a live check against your
real account balance. If you set `MAX_TOTAL_FUNDS` higher than what's
actually in your account, orders will be rejected by Zerodha once you run
out of real funds (logged as `BUY ORDER FAILED`, not silently ignored —
but still worth avoiding). Set `MAX_TOTAL_FUNDS` to match what you've
actually funded the account with.

---

## Known Limitations

- **No live market-hours check.** The loop runs continuously until you stop
  it; it doesn't know or care whether NSE is open.
- **Zerodha access tokens expire daily.** If this process is left running
  across a token's expiry (typically overnight), API calls will start
  failing. The bot logs and retries each cycle but can't refresh the token
  itself — restart the process and log in again each trading day.
- **Holdings are tracked locally, not synced with Zerodha.** If you buy or
  sell manually through the Zerodha app/web UI, this bot won't know — its
  local `etf_holdings.json` will drift out of sync with your real account.
  Use one or the other for a given ETF, not both.
- **One position per ETF, no averaging down.** Once a symbol is in
  holdings, the bot skips it entirely on future buy signals until it's sold.
- **No stop-loss.** The bot only sells on a +10% gain target — there's no
  downside protection if a position drops.
- **Order fills aren't verified.** A successful `place_order()` call means
  Zerodha *accepted* the order, not that it filled exactly as expected.
- **Market orders only**, with `market_protection=2` (max 2% slippage) as
  the only execution safeguard.

---

## Security

**Never commit `config.py`, `etf_holdings.json`, or log files.** The first
contains your Zerodha API secret; the others contain your real trade data.
All three are listed in `.gitignore`.

If you ever do accidentally commit real credentials, removing them from
the latest commit isn't enough — they remain in git history. Rotate the
Zerodha API key/secret (generate new ones via the developer console) and
treat the old ones as compromised.

---

## License & Disclaimer

Personal project for educational and personal trading use. No warranty of
any kind. Trading involves real financial risk, including the risk of
losing your invested capital. This is not financial advice. Test thoroughly
in dry-run mode before enabling live orders, and review the
[Known Limitations](#known-limitations) above before relying on it
unattended.
