# ============================================================
# main.py — Entry point. Run this every trading day morning.
#
# DAILY WORKFLOW:
#   1. Run main.py — it opens browser for Zerodha login ONCE,
#      then loops forever: scans ETFs and places (or simulates)
#      orders every SCAN_INTERVAL_SECONDS, using the same login
#      session (no repeat browser popups).
#   2. Stop it with Ctrl+C when you're done for the day — it will
#      log a clean shutdown message instead of crashing.
#
# NOTE: DRY_RUN is True in trader.py by default.
#       Set DRY_RUN = False in trader.py only when ready for live trading.
#
# NOTE: This loop runs continuously regardless of market hours —
#       it does NOT check NSE trading hours (9:15 AM-3:30 PM IST).
#       Start and stop it yourself around the trading day.
# ============================================================

import logging
import sys
import time

import config
from Per_Gen import login
from per_scanner import scan_buy_signals, scan_sell_signals
from trader import run_etf_buy_orders, run_etf_sell_orders

# How often to re-scan and re-check signals, in seconds.
SCAN_INTERVAL_SECONDS = 20 * 60  # 20 minutes

# ── Logging Setup ─────────────────────────────────────────────
# Force UTF-8 on both handlers explicitly. On Windows, sys.stdout and
# open() often default to the legacy cp1252 codepage instead of UTF-8,
# which can't encode rupee signs and emoji and raises UnicodeEncodeError deep
# inside the logging module (silently swallowed as "Logging error").
file_handler = logging.FileHandler(config.LOG_FILE, encoding="utf-8")

# Reconfigure stdout to UTF-8 if possible (Python 3.7+), otherwise fall
# back to a stream wrapper that replaces unencodable characters instead
# of crashing the handler.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

stream_handler = logging.StreamHandler(sys.stdout)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[file_handler, stream_handler],
)
logger = logging.getLogger(__name__)


def do_login():
    """Log in to Zerodha once. Exits the process if login fails."""
    logger.info("Opening Zerodha login...")
    try:
        kite = login()
        profile = kite.profile()
        logger.info(f"Logged in as: {profile['user_name']} ({profile['user_id']})")
        return kite
    except Exception as e:
        logger.error(f"Login failed: {e}")
        sys.exit(1)


def run_cycle(kite):
    """One scan-and-trade pass, using the already-authenticated kite session."""
    logger.info("=" * 60)
    logger.info("  ETF TRADING BOT - SCAN CYCLE STARTED")
    logger.info("=" * 60)

    # ── Step 1: Scan for sell signals ─────────────────────────
    # Always check sells first to free up capital if needed
    logger.info("\n--- PHASE 1: Checking sell signals ---")
    sell_signals = scan_sell_signals()
    run_etf_sell_orders(kite, sell_signals)

    # ── Step 2: Scan for buy signals ──────────────────────────
    logger.info("\n--- PHASE 2: Scanning for buy signals ---")
    buy_signals = scan_buy_signals()

    # ── Step 3: Place buy orders ──────────────────────────────
    logger.info("\n--- PHASE 3: Placing buy orders ---")
    run_etf_buy_orders(kite, buy_signals)

    logger.info("\n" + "=" * 60)
    logger.info("  ETF TRADING BOT - SCAN CYCLE FINISHED")
    logger.info("=" * 60)


def main():
    logger.info("=" * 60)
    logger.info("  ETF TRADING BOT STARTED (continuous mode)")
    logger.info(f"  Scanning every {SCAN_INTERVAL_SECONDS // 60} minutes. Press Ctrl+C to stop.")
    logger.info("=" * 60)

    # Log in ONCE — the same kite session is reused for every cycle below,
    # so you won't get a repeat browser login popup every 20 minutes.
    kite = do_login()

    try:
        while True:
            try:
                run_cycle(kite)
            except Exception as e:
                # Catch errors from a single cycle (e.g. a transient network
                # blip or yfinance hiccup) so one bad cycle doesn't kill the
                # whole continuous run. The next cycle will just try again.
                logger.error(f"Error during scan cycle: {e}", exc_info=True)

            logger.info(
                f"\nSleeping for {SCAN_INTERVAL_SECONDS // 60} minutes "
                f"until next scan...\n"
            )
            time.sleep(SCAN_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        logger.info("\n" + "=" * 60)
        logger.info("  ETF TRADING BOT STOPPED (Ctrl+C received)")
        logger.info("=" * 60)
        sys.exit(0)


if __name__ == "__main__":
    main()
