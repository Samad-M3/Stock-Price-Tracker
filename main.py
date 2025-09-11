import yfinance as yf
import pandas as pd
from pathlib import Path

column_names = ["Date", "Open", "High", "Low", "Close", "Volume", "Ticker"]

def fetch_historical_data(list_of_tickers, start, end, interval="1d"):
    compiled_history = pd.DataFrame(columns=column_names)
    # Forces each column into the correct data type
    compiled_history = compiled_history.astype({
        "Date": "datetime64[ns]",
        "Open": "float64",
        "High": "float64",
        "Low": "float64",
        "Close": "float64",
        "Volume": "int64",
        "Ticker": "string"
    })

    for single_ticker in list_of_tickers:
        ticker = yf.Ticker(single_ticker)
        history = ticker.history(start=start, end=end, interval=interval).reset_index().drop(["Dividends", "Stock Splits"], axis="columns", errors="ignore")
        history["Ticker"] = single_ticker
        compiled_history = pd.concat([compiled_history, history], ignore_index=True)

    save_to_csv(compiled_history, "historical_data.csv")
    compiled_history = load_from_csv("historical_data.csv")
    print(compiled_history)



def fetch_live_price(tickers):
    for ticker in tickers:
        current_ticker = yf.Ticker(ticker)
        print(f"{ticker} current price = ${current_ticker.fast_info['lastPrice']:.2f}")

def save_to_csv(dataframe, filename):
    dataframe.to_csv(filename, index=False)

def load_from_csv(filename):
    if Path(filename).exists():
        df = pd.read_csv(filename)
        df["Date"] = pd.to_datetime(df["Date"])
        return df
    else:
        print("File does not exist")

fetch_historical_data(["AAPL", "AMZN", "MSFT"], "2025-08-01", "2025-09-01", "1d")

# fetch_live_price(["AAPL", "MSFT", "TSLA", "AMZN"])
