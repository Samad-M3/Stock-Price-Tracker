import yfinance as yf

def fetch_live_price(tickers):
    for ticker in tickers:
        current_ticker = yf.Ticker(ticker)
        print(f"{ticker} current price = ${current_ticker.fast_info['lastPrice']:.2f}")

fetch_live_price(["AAPL", "MSFT", "TSLA", "AMZN"])

