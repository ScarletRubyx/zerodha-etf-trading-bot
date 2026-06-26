# Setup Guide

Step-by-step instructions to get the bot running, from a clean checkout to
live trading.

---

## File Structure

```
your_bot_folder/
│
├── main.py              ← Entry point: logs in once, then loops the scan/trade cycle
├── per_scanner.py        ← Scans ETFs via yfinance for buy/sell signals
├── trader.py             ← Places (or simulates) orders via Zerodha
├── Per_Gen.py             ← Zerodha OAuth login (local Flask callback)
├── holdings.py            ← Manages etf_holdings.json (local holdings record)
├── quick_test.py          ← Validates all ETF tickers before you deploy
├── requirements.txt        ← Python dependencies
│
├── config.py             ← YOU create this — see Step 2 (not in this repo)
├── etf_holdings.json     ← Auto-created on first buy (not in this repo)
└── bot.log               ← Auto-created at runtime (not in this repo)
```

---

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Step 2: Create `config.py`

This file is **not included** in the repo — it holds your Zerodha API
credentials and shouldn't be committed to version control. Create it
yourself in the project root:

```python
# config.py
API_KEY = "your_zerodha_api_key"
API_SECRET = "your_zerodha_api_secret"
EXCHANGE = "NSE"
BUDGET_PER_TRADE = 10000     # Rs. per individual trade
MAX_TOTAL_FUNDS = 100000     # Rs. total capital the bot is allowed to deploy
LOG_FILE = "bot.log"
```

To get your API key and secret:
1. Go to the [Zerodha Kite Connect developer console](https://developers.kite.trade/).
2. Create an app (or use an existing one).
3. Copy the **API Key** and **API Secret** into `config.py` above.

Note: Kite Connect API access is a separate paid subscription from your
regular Zerodha trading account — check current pricing on Zerodha's site
if you haven't set this up before.

Set `MAX_TOTAL_FUNDS` to roughly match what you've actually funded the
trading account with — the bot tracks this cap locally and doesn't check
your live account balance, so a mismatch will surface as rejected orders
rather than a clean warning.

---

## Step 3: Validate ETF Tickers

```bash
python3 quick_test.py
```

You should see something like:

```
  Checking NIFTYBEES.NS      ... [OK] Rs.273.43
  Checking JUNIORBEES.NS     ... [OK] Rs.779.65
  ...

RESULT: 10/10 passed
[OK] All tickers are valid! You're ready to deploy.
```

**If any ticker shows `[FAIL]`**, edit `POPULAR_ETFS` in `per_scanner.py`
(it's likely been delisted or renamed) — and update the matching list in
`quick_test.py` to keep both in sync.

---

## Step 4: Dry-Run

```bash
python3 main.py
```

This will:
1. Open Zerodha login in your browser (PIN + OTP).
2. Log in **once** — the session is reused for every scan cycle after that.
3. Loop continuously, scanning every 20 minutes by default
   (`SCAN_INTERVAL_SECONDS` in `main.py`).
4. Each cycle: check sell signals, check buy signals, log what it *would*
   do — no real orders are placed, because `DRY_RUN = True` in `trader.py`.

Watch the console or `bot.log` to see what it's doing. Stop it any time
with `Ctrl+C` — it logs a clean shutdown message rather than crashing.

---

## Step 5: Go Live (When Ready)

### Pre-flight checklist

- [ ] `config.py` is filled in with correct API keys.
- [ ] All tickers passed `quick_test.py`.
- [ ] You've done at least one dry-run and reviewed the logs.
- [ ] Your Zerodha account has **CNC trading enabled**.
- [ ] Your Zerodha account has **real funds available**, roughly matching
      `MAX_TOTAL_FUNDS`.
- [ ] You're comfortable with the limitations in the main README, especially
      around token expiry and lack of a stop-loss.

### Flip the switch

In `trader.py`:

```python
# Change this:
DRY_RUN = True
# To this:
DRY_RUN = False
```

Then run `python3 main.py` again. Orders will now be placed for real. Check
`bot.log` immediately after the first cycle to confirm orders actually went
through as expected.

---

## Daily Operating Procedure

This bot is a **long-running process**, not a scheduled script. Each
trading day:

```bash
python3 main.py
```

Leave the terminal open (or run it in the background — e.g. via `nohup` on
Linux/macOS, or as a background process on Windows) for as long as you want
it scanning. Stop it with `Ctrl+C` when you're done for the day.

**Restart it fresh each trading day.** Zerodha access tokens expire daily
(typically overnight); a session left running across that boundary will
start failing API calls until you restart and log in again.

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'yfinance'`**
```bash
pip install yfinance
```

**A ticker shows `[FAIL]` in `quick_test.py`**
That ticker may be delisted, renamed, or temporarily unavailable. Update
`POPULAR_ETFS` in `per_scanner.py` and the matching list in `quick_test.py`.

**No buy signals during dry-run**
The 5%-below-10-day-high threshold is intentionally conservative — it's
normal to see "No signal" most of the time. Check `bot.log` for the actual
price data being fetched if you want to confirm it's working.

**Repeated errors after running for many hours / overnight**
Likely an expired access token (see [Known Limitations](README.md#known-limitations)
in the README). Stop the process (`Ctrl+C`) and restart it to log in fresh.

**Garbled or missing log output with special characters**
Should already be handled — `main.py` forces UTF-8 on its logging handlers,
and the rupee sign / status emoji used elsewhere in the codebase have been
replaced with plain ASCII (`Rs.`, `[BUY]`, `[WAIT]`, etc.) specifically to
avoid `UnicodeEncodeError` crashes on Windows consoles using the legacy
cp1252 codepage. If you still see this, double-check you're running the
current version of `main.py`, not an older cached copy.

---

## Next Steps

1. Read the main [README.md](README.md) for an overview and known limitations.
2. Run `quick_test.py`.
3. Dry-run with `main.py` and review `bot.log`.
4. When confident, flip `DRY_RUN = False` and go live.
