"""
ETF Scanner using yfinance
===========================

Scans for:
1. Popular ETFs where current price is >= 5% below the 10-day high (BUY signal)
2. Past purchased ETFs where gain from buy price >= 10% (SELL signal)

10-day high = highest price over the last 10 trading days (from yfinance daily bars).
yfinance is reliable, no auth, works globally for .NS (NSE) tickers.
"""

import logging
from datetime import datetime
import yfinance as yf
from holdings import load_holdings, add_holding

# ── Configuration ────────────────────────────────────────────
POPULAR_ETFS = [
    "NIFTYBEES.NS",      # Nippon Nifty 50 ETF
    "JUNIORBEES.NS",     # Nippon Nifty Next 50 ETF
    "SETFNN50.NS",       # SBI Nifty Junior ETF (replaces SPDRBEES)
    "GOLDBEES.NS",       # Nippon Gold ETF
    "MON100.NS",         # Motilal Oswal NASDAQ 100 ETF (replaces MOTILALOSSB)
    "INFRABEES.NS",      # Nippon Infrastructure ETF
    "BANKBEES.NS",       # Nippon Bank ETF
    "PSUBNKBEES.NS",     # Nippon PSU Bank ETF (replaces UNITTRUST)
    "NEXT50IETF.NS",     # ICICI Prudential Nifty Next 50 ETF (replaces ICIPROXETF)
    "ITBEES.NS",         # Nippon Nifty IT ETF (replaces PPFAS)
]

BUY_THRESHOLD = 5.0      # Buy if price is >= 5% below the 10-day high
SELL_THRESHOLD = 10.0    # Sell if gain from buy price >= 10%

LOG_FILE = "etf_scanner.log"

# ── Logging Setup ────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def get_etf_data(symbol: str) -> dict | None:
    """
    Fetch current price and 10-day high from yfinance.
    Returns: {current_price, ten_day_high, pct_below_high} or None on error.

    Fetches last 12 trading days of data, calculates max high over those days.
    """
    try:
        # Fetch last 12 days of data (gets ~10 trading days)
        hist = yf.download(symbol, period="12d", progress=False, timeout=10)

        if hist.empty or len(hist) < 2:
            logger.debug(f"No data available for {symbol}")
            return None

        # Current price = most recent close
        # yfinance may return MultiIndex columns — flatten to Series if needed
        close_col = hist["Close"]
        if hasattr(close_col, "columns"):  # MultiIndex DataFrame
            close_col = close_col.iloc[:, 0]
        current_price = float(close_col.iloc[-1])
        if current_price <= 0:
            return None

        # 10-day high = max high over the period
        high_col = hist["High"]
        if hasattr(high_col, "columns"):
            high_col = high_col.iloc[:, 0]
        ten_day_high = float(high_col.max())

        if ten_day_high <= 0:
            return None

        # % below the 10-day high (positive = below high, negative = above high)
        pct_below_high = ((ten_day_high - current_price) / ten_day_high) * 100

        return {
            "current_price": round(current_price, 2),
            "ten_day_high": round(ten_day_high, 2),
            "pct_below_high": round(pct_below_high, 2),
        }

    except Exception as e:
        logger.debug(f"Error fetching {symbol}: {e}")
        return None


def scan_buy_signals() -> list[dict]:
    """
    Scan POPULAR_ETFS for those >= 5% below their 10-day high.
    Returns: [{symbol, current_price, ten_day_high, pct_below_high}, ...]
    """
    logger.info(f"\n{'='*60}")
    logger.info("SCANNING FOR BUY SIGNALS (5% Below 10-Day High)")
    logger.info(f"{'='*60}")

    buy_signals = []

    for etf in POPULAR_ETFS:
        logger.info(f"Checking {etf}...")
        data = get_etf_data(etf)

        if data is None:
            logger.debug(f"  [WARN] No data available for {etf}")
            continue

        current_price = data["current_price"]
        ten_day_high = data["ten_day_high"]
        pct_below = data["pct_below_high"]

        if pct_below >= BUY_THRESHOLD:
            logger.info(
                f"  [BUY SIGNAL] {etf} | "
                f"Price: Rs.{current_price:.2f} | "
                f"10-Day High: Rs.{ten_day_high:.2f} | "
                f"{pct_below:.2f}% below high"
            )
            buy_signals.append({
                "symbol": etf.replace(".NS", ""),  # Strip .NS for order placement
                "current_price": current_price,
                "ten_day_high": ten_day_high,
                "pct_below_high": pct_below,
            })
        else:
            logger.info(
                f"  [WAIT] {etf} | Price: Rs.{current_price:.2f} | "
                f"10-Day High: Rs.{ten_day_high:.2f} | "
                f"{pct_below:.2f}% below high (No signal)"
            )

    logger.info(f"\nFound {len(buy_signals)} ETFs at 5% below 10-day high.\n")
    return buy_signals


def scan_sell_signals() -> list[dict]:
    """
    Check all held ETFs. Sell if current price >= 10% above buy price.
    Returns: [{symbol, buy_price, current_price, gain_pct}, ...]
    """
    logger.info(f"\n{'='*60}")
    logger.info("SCANNING FOR SELL SIGNALS (10% Gain from Buy Price)")
    logger.info(f"{'='*60}")

    holdings = load_holdings()
    sell_signals = []

    if not holdings:
        logger.info("No past purchases recorded.")
        return sell_signals

    logger.info(f"Checking {len(holdings)} held ETFs...\n")

    for symbol, buy_info in holdings.items():
        logger.info(f"Checking {symbol}...")
        buy_price = buy_info.get("buy_price")

        # Add .NS suffix for yfinance lookup
        yf_symbol = f"{symbol}.NS"
        data = get_etf_data(yf_symbol)

        if data is None:
            logger.debug(f"  [WARN] No data available for {symbol}")
            continue

        current_price = data["current_price"]

        if buy_price and buy_price > 0:
            gain_pct = ((current_price - buy_price) / buy_price) * 100
        else:
            logger.warning(f"  [WARN] No buy price recorded for {symbol}, skipping.")
            continue

        if gain_pct >= SELL_THRESHOLD:
            logger.info(
                f"  [SELL SIGNAL] {symbol} | "
                f"Buy: Rs.{buy_price:.2f} | "
                f"Current: Rs.{current_price:.2f} | "
                f"Gain: {gain_pct:.2f}%"
            )
            sell_signals.append({
                "symbol": symbol,
                "buy_price": buy_price,
                "current_price": current_price,
                "gain_pct": round(gain_pct, 2),
            })
        else:
            logger.info(
                f"  [WAIT] {symbol} | "
                f"Buy: Rs.{buy_price:.2f} | "
                f"Current: Rs.{current_price:.2f} | "
                f"Gain: {gain_pct:.2f}% (Waiting for target)"
            )

    logger.info(f"\nFound {len(sell_signals)} ETFs at 10% gain.\n")
    return sell_signals


def record_purchase(symbol: str, price: float, quantity: int = 1):
    """Record a new ETF purchase in holdings."""
    add_holding(symbol, quantity, price)
    logger.info(f"Recorded purchase: {symbol} @ Rs.{price:.2f} x{quantity}")


def main():
    """Main scanner execution."""
    logger.info("\n" + "=" * 60)
    logger.info("ETF SCANNER STARTED")
    logger.info("=" * 60)
    logger.info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    buy_signals = scan_buy_signals()
    sell_signals = scan_sell_signals()

    logger.info(f"{'='*60}")
    logger.info("SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Buy Signals:  {len(buy_signals)} ETF(s) at 5% below 10-day high")
    logger.info(f"Sell Signals: {len(sell_signals)} ETF(s) at 10% gain")
    logger.info(f"{'='*60}\n")

    return {
        "buy_signals": buy_signals,
        "sell_signals": sell_signals,
    }


if __name__ == "__main__":
    results = main()

    if results["buy_signals"]:
        print("\n[SUMMARY] BUY SIGNALS (5% Below 10-Day High):")
        for sig in results["buy_signals"]:
            print(
                f"  • {sig['symbol']:15} | "
                f"Rs.{sig['current_price']:8.2f} | "
                f"10-Day High: Rs.{sig['ten_day_high']:8.2f} | "
                f"{sig['pct_below_high']:+6.2f}% below"
            )

    if results["sell_signals"]:
        print("\n[SUMMARY] SELL SIGNALS (10% Gain from Buy Price):")
        for sig in results["sell_signals"]:
            print(
                f"  • {sig['symbol']:15} | "
                f"Buy: Rs.{sig['buy_price']:8.2f} | "
                f"Now: Rs.{sig['current_price']:8.2f} | "
                f"{sig['gain_pct']:+6.2f}%"
            )
