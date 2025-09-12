import yfinance as yf
import pandas as pd
from pathlib import Path
from datetime import datetime

COLUMN_NAMES = ["Date", "Open", "High", "Low", "Close", "Volume", "Ticker"]

def fetch_historical_data(list_of_tickers, start, end, interval):
    start = pd.to_datetime(start).tz_localize("America/New_York")
    end = pd.to_datetime(end).tz_localize("America/New_York")
    filename = get_filename(interval)

    if Path("historical_data.csv").exists():
        compiled_history = load_from_csv("historical_data.csv")
        present_tickers = []
        missing_tickers = []
        fully_checked_tickers = []

        for ticker in list_of_tickers:
            if ticker in compiled_history["Ticker"].values:
                present_tickers.append(ticker)
            else:
                missing_tickers.append(ticker)

        for ticker in present_tickers:
            ticker_specific_dataframe = compiled_history[compiled_history["Ticker"] == ticker] # Returns a dataframe for just that ticker
            """
            Check to see if the shortest date in the dataframe is earlier than or equal to the start date
            Check to see if the longest date in the dateframe is later than or equal to the end date
            """
            if start >= ticker_specific_dataframe["Date"].min() and end <= ticker_specific_dataframe["Date"].max():
                pass
            else:
                if start < ticker_specific_dataframe["Date"].min():
                    ticker_object = yf.Ticker(ticker)
                    history = ticker_object.history(start=start, end=ticker_specific_dataframe["Date"].min(), interval=interval).reset_index().drop(["Dividends", "Stock Splits", "Adj Close"], axis="columns", errors="ignore")
                    history["Ticker"] = ticker

                    if history.empty:
                        pass
                    else:
                        compiled_history = pd.concat([compiled_history, history], ignore_index=True)

                if end > ticker_specific_dataframe["Date"].max():
                    ticker_object = yf.Ticker(ticker)
                    history = ticker_object.history(start=ticker_specific_dataframe["Date"].max(), end=end, interval=interval).reset_index().drop(["Dividends", "Stock Splits", "Adj Close"], axis="columns", errors="ignore")
                    history["Ticker"] = ticker

                    if history.empty:
                        pass
                    else:
                        compiled_history = pd.concat([compiled_history, history], ignore_index=True)

            fully_checked_tickers.append(ticker)
                
        for ticker in missing_tickers:
            ticker_object = yf.Ticker(ticker)
            history = ticker_object.history(start=start, end=end, interval=interval).reset_index().drop(["Dividends", "Stock Splits", "Adj Close"], axis="columns", errors="ignore")
            history["Ticker"] = ticker
            compiled_history = pd.concat([compiled_history, history], ignore_index=True)
            fully_checked_tickers.append(ticker)   
      
        compiled_history.drop_duplicates(subset=["Date", "Ticker"], inplace=True)
        save_to_csv(compiled_history, "historical_data.csv")    
        
        combined_resulting_dataframe = pd.DataFrame(columns=COLUMN_NAMES) # Creating an empty dataframe so each tickers filtered data can be appeneded on and representred as one big dataframe
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

        for ticker in fully_checked_tickers:
            combined_resulting_dataframe = pd.concat([combined_resulting_dataframe, compiled_history[(compiled_history["Ticker"] == ticker) & (compiled_history["Date"] >= start) & (compiled_history["Date"] <= end)]])

        print(combined_resulting_dataframe.to_string())
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
            history = ticker.history(start=start, end=end, interval=interval).reset_index().drop(["Dividends", "Stock Splits", "Adj Close"], axis="columns", errors="ignore")
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

def get_filename(interval):
    return f"data/historical_data_{interval}.csv"

# fetch_historical_data(["AAPL", "AMZN", "MSFT"], "2025-08-01", "2025-09-01", "1d")
# fetch_historical_data(["MSFT", "TSLA"], "2025-08-10", "2025-08-23", "1d")
# fetch_historical_data(["MSFT", "AMZN", "META", "GOOGL"], "2025-09-01", "2025-09-10", "1d")
# fetch_historical_data(["AAPL", "MSFT"], "2025-06-10", "2025-06-24", "1d")

# fetch_live_price(["AAPL", "MSFT", "TSLA", "AMZN"])