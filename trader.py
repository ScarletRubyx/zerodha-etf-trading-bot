# ============================================================
# trader.py — Places buy/sell orders via Zerodha Kite API.
#
# DRY_RUN = True  → logs what it WOULD do, no real orders placed.
# DRY_RUN = False → places real orders. Switch only when confident.
# ============================================================

import logging
from math import floor
from kiteconnect import KiteConnect
import config
from holdings import load_holdings, add_holding, remove_holding, get_total_deployed

logger = logging.getLogger(__name__)

# ── Safety Switch ─────────────────────────────────────────────
# Set to False only when you are ready to place real orders.
DRY_RUN = True


def place_buy_order(kite: KiteConnect, symbol: str, quantity: int, current_price: float) -> bool:
    """
    Place a market buy order.
    In DRY_RUN mode: just logs, no actual order.
    """
    if DRY_RUN:
        logger.info(
            f"[DRY RUN] Would BUY {symbol} | "
            f"Qty: {quantity} | ~Price: Rs.{current_price:.2f} | "
            f"~Total: Rs.{quantity * current_price:.2f}"
        )
        # Still record in holdings so sell logic works in dry run
        add_holding(symbol, quantity, current_price)
        return True

    try:
        order_id = kite.place_order(
            variety=kite.VARIETY_REGULAR,
            exchange=config.EXCHANGE,
            tradingsymbol=symbol,
            transaction_type=kite.TRANSACTION_TYPE_BUY,
            quantity=quantity,
            product=kite.PRODUCT_CNC,
            order_type=kite.ORDER_TYPE_MARKET,
            market_protection=2,        # Max 2% slippage (mandatory from Apr 1 2026)
        )
        logger.info(
            f"BUY ORDER PLACED | {symbol} | "
            f"Qty: {quantity} | ~Price: Rs.{current_price:.2f} | Order ID: {order_id}"
        )
        add_holding(symbol, quantity, current_price)
        return True

    except Exception as e:
        logger.error(f"BUY ORDER FAILED [FAIL] | {symbol} | Error: {e}")
        return False


def place_sell_order(kite: KiteConnect, symbol: str, quantity: int, current_price: float = 0.0) -> bool:
    """
    Place a market sell order.
    In DRY_RUN mode: just logs, no actual order.
    """
    if DRY_RUN:
        logger.info(
            f"[DRY RUN] Would SELL {symbol} | "
            f"Qty: {quantity}"
            + (f" | ~Price: Rs.{current_price:.2f}" if current_price else "")
        )
        remove_holding(symbol)
        return True

    try:
        order_id = kite.place_order(
            variety=kite.VARIETY_REGULAR,
            exchange=config.EXCHANGE,
            tradingsymbol=symbol,
            transaction_type=kite.TRANSACTION_TYPE_SELL,
            quantity=quantity,
            product=kite.PRODUCT_CNC,
            order_type=kite.ORDER_TYPE_MARKET,
            market_protection=2,
        )
        logger.info(
            f"SELL ORDER PLACED | {symbol} | Qty: {quantity} | Order ID: {order_id}"
        )
        remove_holding(symbol)
        return True

    except Exception as e:
        logger.error(f"SELL ORDER FAILED [FAIL] | {symbol} | Error: {e}")
        return False


def run_etf_buy_orders(kite: KiteConnect, buy_signals: list[dict]):
    """
    Execute (or simulate) buy orders for ETF buy signals.
    Calculates quantity from config.BUDGET_PER_TRADE.

    Expected input: [{symbol, current_price, week_high, pct_below_high}, ...]
    """
    if not buy_signals:
        logger.info("No ETF buy signals to act on.")
        return

    existing_holdings = load_holdings()
    deployed = get_total_deployed()
    logger.info(f"Processing {len(buy_signals)} ETF buy signal(s)...")
    logger.info(f"Currently deployed: Rs.{deployed:.2f} / Rs.{config.MAX_TOTAL_FUNDS}")

    for signal in buy_signals:
        symbol = signal["symbol"]
        current_price = signal["current_price"]

        # Skip if already holding
        if symbol in existing_holdings:
            logger.info(f"Skipping {symbol} — already in holdings.")
            continue

        # Calculate quantity from budget
        quantity = floor(config.BUDGET_PER_TRADE / current_price)
        if quantity < 1:
            logger.warning(
                f"Skipping {symbol} — price Rs.{current_price:.2f} exceeds "
                f"budget Rs.{config.BUDGET_PER_TRADE}"
            )
            continue

        spend = quantity * current_price

        # Check overall fund cap
        if deployed + spend > config.MAX_TOTAL_FUNDS:
            logger.warning(
                f"Skipping {symbol} — fund limit reached "
                f"(Rs.{deployed:.2f} + Rs.{spend:.2f} > Rs.{config.MAX_TOTAL_FUNDS})"
            )
            continue

        success = place_buy_order(kite, symbol, quantity, current_price)
        if success:
            deployed += spend


def run_etf_sell_orders(kite: KiteConnect, sell_signals: list[dict]):
    """
    Execute (or simulate) sell orders for ETF sell signals.

    Expected input: [{symbol, buy_price, current_price, gain_pct}, ...]
    """
    if not sell_signals:
        logger.info("No ETF sell signals to act on.")
        return

    holdings = load_holdings()
    logger.info(f"Processing {len(sell_signals)} ETF sell signal(s)...")

    for signal in sell_signals:
        symbol = signal["symbol"]
        current_price = signal["current_price"]

        if symbol not in holdings:
            logger.warning(f"ETF {symbol} not in holdings — skipping sell.")
            continue

        quantity = holdings[symbol].get("quantity", 0)
        if quantity < 1:
            logger.warning(f"ETF {symbol} has quantity 0 in holdings — skipping.")
            continue

        logger.info(
            f"Selling {symbol} | Qty: {quantity} | "
            f"Gain: {signal['gain_pct']:.2f}%"
        )
        place_sell_order(kite, symbol, quantity, current_price)
