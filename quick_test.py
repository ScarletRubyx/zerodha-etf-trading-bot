#!/usr/bin/env python3
"""
quick_test.py — Validate that all ETF tickers resolve with yfinance.
Run this once after installing yfinance to confirm no ticker issues.

Usage:
  python3 quick_test.py
"""

import yfinance as yf
import time

POPULAR_ETFS = [
    "NIFTYBEES.NS",
    "JUNIORBEES.NS",
    "SETFNN50.NS",
    "GOLDBEES.NS",
    "MON100.NS",
    "INFRABEES.NS",
    "BANKBEES.NS",
    "PSUBNKBEES.NS",
    "NEXT50IETF.NS",
    "ITBEES.NS",
]

print("=" * 70)
print("ETF TICKER VALIDATION TEST")
print("=" * 70)
print(f"Testing {len(POPULAR_ETFS)} ETF tickers with yfinance...\n")

passed = 0
failed = 0

for etf in POPULAR_ETFS:
    try:
        print(f"  Checking {etf:20} ... ", end="", flush=True)
        
        # Fetch just 2 days to be quick
        hist = yf.download(etf, period="2d", progress=False, timeout=5)
        
        if hist.empty or len(hist) < 1:
            print("[FAIL] NO DATA")
            failed += 1
        else:
            close_col = hist["Close"]
            if hasattr(close_col, "columns"):  # MultiIndex — flatten
                close_col = close_col.iloc[:, 0]
            price = float(close_col.iloc[-1])
            print(f"[OK] Rs.{price:.2f}")
            passed += 1
    
    except Exception as e:
        print(f"[FAIL] ERROR: {str(e)[:40]}")
        failed += 1
    
    time.sleep(0.5)  # Be nice to yfinance

print("\n" + "=" * 70)
print(f"RESULT: {passed}/{len(POPULAR_ETFS)} passed")
print("=" * 70)

if failed == 0:
    print("\n[OK] All tickers are valid! You're ready to deploy.\n")
else:
    print(f"\n[WARN] {failed} ticker(s) failed. Review the list and update per_scanner.py.\n")
