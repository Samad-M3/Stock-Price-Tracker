import yfinance as yf

def fetch_historical_data(list_of_tickers, period, interval):
    for single_ticker in list_of_tickers:
        ticker = yf.Ticker(single_ticker)
        history = ticker.history(period=period, interval=interval).reset_index().drop(["Dividends", "Stock Splits"], axis="columns", errors="ignore")
        history["Ticker"] = single_ticker
        print(history.to_string())
        print()

def fetch_live_price(tickers):
    for ticker in tickers:
        current_ticker = yf.Ticker(ticker)
        print(f"{ticker} current price = ${current_ticker.fast_info['lastPrice']:.2f}")

# fetch_live_price(["AAPL", "MSFT", "TSLA", "AMZN"])

fetch_historical_data(["TSLA", "AAPl"], "1mo", "1d")


