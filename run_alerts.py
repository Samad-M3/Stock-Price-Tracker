"""
Daily alert runner script for Stock Price Tracker.

This script reads the configuration from `alert_config.json` and triggers
the daily percentage change email alerts for the specified stock tickers.
It is intended to be run automatically via Windows Task Scheduler at 9:10 PM.
"""

import json
from main import StockTracker

try:
    data = None

    with open("alert_config.json", "r") as f:
        data = json.load(f)

    list_of_tickers = data["tickers"]
    threshold_value = data["threshold"]
    recipient_email = data["recipient_email"]

    tracker = StockTracker()
    tracker.percentage_change_alert(list_of_tickers, threshold_value, recipient_email, verbose=False)
    
except FileNotFoundError:
    print(f"\n⚠️  Error: **alert_config.json** not found")
except json.JSONDecodeError:
    print(f"\n⚠️  Error: **alert_config.json** is corrupted or not valid JSON")
except (PermissionError, OSError) as e:
    print(f"\n⚠️  Error accessing **alert_config.json**: {e}")
except Exception as e:
    print(f"\n⚠️  Unexpected error: {e}")