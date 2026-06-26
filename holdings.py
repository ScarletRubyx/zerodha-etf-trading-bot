# ============================================================
# holdings.py — Manages local ETF holdings record (etf_holdings.json)
# ============================================================

import json
import logging
import os
import tempfile
from datetime import datetime

logger = logging.getLogger(__name__)

HOLDINGS_FILE = "etf_holdings.json"

# In-memory cache so a single run doesn't re-read/re-parse the file on
# every add/remove/lookup call. Invalidated by reset_cache() if you ever
# need to force a fresh read (e.g. in tests, or if the file changes
# underneath the process).
_cache: dict | None = None


def _validate(data) -> dict:
    """
    Make sure loaded JSON actually looks like a holdings dict:
    { "SYMBOL": {"quantity": int, "buy_price": float, "buy_date": str}, ... }
    Falls back to {} (and logs a warning) for anything that doesn't fit,
    instead of letting a malformed-but-valid JSON file blow up later in
    add_holding/remove_holding/get_total_deployed.
    """
    if not isinstance(data, dict):
        logger.warning(
            f"{HOLDINGS_FILE} did not contain a JSON object (got "
            f"{type(data).__name__}), starting fresh."
        )
        return {}

    cleaned = {}
    for symbol, record in data.items():
        if not isinstance(record, dict):
            logger.warning(f"Skipping malformed holding entry for {symbol!r}.")
            continue
        if "quantity" not in record or "buy_price" not in record:
            logger.warning(f"Skipping incomplete holding entry for {symbol!r}.")
            continue
        cleaned[symbol] = record

    return cleaned


def _read_from_disk() -> dict:
    """Load holdings from JSON file. Returns {} if file missing, corrupt, or malformed."""
    try:
        with open(HOLDINGS_FILE, "r") as f:
            raw = json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        logger.warning(f"Could not parse {HOLDINGS_FILE}, starting fresh.")
        return {}

    return _validate(raw)


def load_holdings(force_reload: bool = False) -> dict:
    """
    Return the current holdings dict. Reads from disk once per process
    and caches the result; pass force_reload=True to bypass the cache
    and re-read the file from disk.
    """
    global _cache
    if _cache is None or force_reload:
        _cache = _read_from_disk()
    return _cache


def reset_cache():
    """Drop the in-memory cache so the next load_holdings() re-reads from disk."""
    global _cache
    _cache = None


def save_holdings(holdings: dict):
    """
    Persist holdings dict to JSON file atomically: write to a temp file
    in the same directory, then os.replace() it into place. This avoids
    leaving a half-written/corrupt etf_holdings.json behind if the
    process crashes or is killed mid-write.
    """
    directory = os.path.dirname(os.path.abspath(HOLDINGS_FILE)) or "."
    fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=".etf_holdings_", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(holdings, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, HOLDINGS_FILE)
    except Exception:
        # Clean up the temp file if something went wrong before replace()
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise

    global _cache
    _cache = holdings


def add_holding(symbol: str, quantity: int, buy_price: float):
    """Record a new purchase."""
    holdings = load_holdings()
    holdings[symbol] = {
        "quantity": quantity,
        "buy_price": buy_price,
        "buy_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    save_holdings(holdings)
    logger.info(f"Holdings updated: added {symbol} x{quantity} @ Rs.{buy_price:.2f}")


def remove_holding(symbol: str):
    """Remove a holding after selling."""
    holdings = load_holdings()
    if symbol in holdings:
        del holdings[symbol]
        save_holdings(holdings)
        logger.info(f"Holdings updated: removed {symbol}")
    else:
        logger.warning(f"Tried to remove {symbol} but it wasn't in holdings.")


def get_total_deployed(kite=None) -> float:
    """
    Return total capital currently deployed (sum of buy_price * quantity).

    NOTE: kite param is currently unused — we use locally recorded buy
    prices rather than live market value. If you want this to reflect
    *current* deployed value (e.g. using live LTP from Kite) rather than
    cost basis, that's a future enhancement: fetch quotes via kite.ltp()
    for each held symbol and multiply by quantity instead of buy_price.
    """
    holdings = load_holdings()
    total = sum(
        h.get("buy_price", 0) * h.get("quantity", 0)
        for h in holdings.values()
    )
    return total
