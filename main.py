import yfinance as yf
import pandas as pd
from pathlib import Path
from datetime import datetime

COLUMN_NAMES = ["Date", "Open", "High", "Low", "Close", "Volume", "Ticker"]

def fetch_historical_data(list_of_tickers, start, end, interval="1d"):
    if Path("historical_data.csv").exists():
        compiled_history = load_from_csv("historical_data.csv")
        present_tickers = []
        missing_tickers = []
        partial_tickers = {}
        full_covered_tickers = []
        truth_counter = 0

        for ticker in list_of_tickers:



        if set(list_of_tickers).issubset(set(compiled_history["Ticker"].values)): # Check to see if the tickers are present in dataframe
            for ticker in list_of_tickers:
                shortned_df = compiled_history[compiled_history["Ticker"] == ticker] # Returns a dataframe for just that ticker
                if shortned_df["Date"].min().to_pydatetime().strftime("%Y-%m-%d") <= start: # Check to see if the shortest date in the dataframe is earlier than or equal to the start date
                    if shortned_df["Date"].max().to_pydatetime().strftime("%Y-%m-%d") >= end: # Check to see if the longest date in the dateframe is later than or equal to the end date
                        truth_counter +=1
            
        if truth_counter == len(list_of_tickers):
            print("Loading data from CSV...")
            combined_resulting_dataframe = pd.DataFrame(columns=COLUMN_NAMES)
            # Forces each column into the correct data type
            combined_resulting_dataframe = combined_resulting_dataframe.astype({
                "Date": "datetime64[ns]",
                "Open": "float64",
                "High": "float64",
                "Low": "float64",
                "Close": "float64",
                "Volume": "int64",
                "Ticker": "string"
            })
            for ticker in list_of_tickers:
                combined_resulting_dataframe = pd.concat([combined_resulting_dataframe ,compiled_history[(compiled_history["Date"] >= start) & (compiled_history["Date"] <= end) & (compiled_history["Ticker"] == ticker)]])
            print(combined_resulting_dataframe)
        else:
            print("Data needs to be fetched from the API")
    else:
        print("Fetching data from API...")
        compiled_history = pd.DataFrame(columns=COLUMN_NAMES)
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

# fetch_historical_data(["AAPL", "AMZN", "MSFT"], "2025-08-01", "2025-09-01", "1d")

fetch_historical_data(["MSFT", "TSLA"], "2025-08-10", "2025-08-23", "1d")

# fetch_live_price(["AAPL", "MSFT", "TSLA", "AMZN"])
