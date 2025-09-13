import yfinance as yf
import pandas as pd
from pathlib import Path
from datetime import datetime

COLUMN_NAMES = ["Date", "Open", "High", "Low", "Close", "Volume", "Ticker"]
INTERVAL_TO_TIMEDIFF = {
    "1m": pd.Timedelta(minutes=1),
    "2m": pd.Timedelta(minutes=2),
    "5m": pd.Timedelta(minutes=5),
    "15m": pd.Timedelta(minutes=15),
    "30m": pd.Timedelta(minutes=30),
    "60m": pd.Timedelta(hours=1),
    "90m": pd.Timedelta(minutes=90),
    "1d": pd.Timedelta(days=1),
    "5d": pd.Timedelta(days=5),
    "1wk": pd.Timedelta(weeks=1),
    "1mo": pd.Timedelta(days=30),
    "3mo": pd.Timedelta(days=90)
}

def fetch_historical_data(list_of_tickers, start, end, interval):
    start = pd.to_datetime(start).tz_localize("America/New_York")
    end = pd.to_datetime(end).tz_localize("America/New_York")
    filename = get_filename(interval)

    if Path(filename).exists():
        compiled_history = load_from_csv(filename)
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

            internal_gaps = get_internal_missing_ranges(ticker_specific_dataframe, start, end, interval)
            ticker_object = yf.Ticker(ticker)
            for gap_start, gap_end in internal_gaps:
                history = ticker_object.history(start=gap_start, end=gap_end, interval=interval).reset_index().drop(["Dividends", "Stock Splits", "Adj Close"], axis="columns", errors="ignore")
                history["Ticker"] = ticker

                if "Datetime" in history.columns:
                        history = history.rename(columns={"Datetime": "Date"})

                if history.empty:
                        pass
                else:
                    compiled_history = pd.concat([compiled_history, history], ignore_index=True)

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

                    if "Datetime" in history.columns:
                        history = history.rename(columns={"Datetime": "Date"})

                    if history.empty:
                        pass
                    else:
                        compiled_history = pd.concat([compiled_history, history], ignore_index=True)

                if end > ticker_specific_dataframe["Date"].max():
                    ticker_object = yf.Ticker(ticker)
                    history = ticker_object.history(start=ticker_specific_dataframe["Date"].max(), end=end, interval=interval).reset_index().drop(["Dividends", "Stock Splits", "Adj Close"], axis="columns", errors="ignore")
                    history["Ticker"] = ticker

                    if "Datetime" in history.columns:
                        history = history.rename(columns={"Datetime": "Date"})

                    if history.empty:
                        pass
                    else:
                        compiled_history = pd.concat([compiled_history, history], ignore_index=True)

            fully_checked_tickers.append(ticker)
                
        for ticker in missing_tickers:
            ticker_object = yf.Ticker(ticker)
            history = ticker_object.history(start=start, end=end, interval=interval).reset_index().drop(["Dividends", "Stock Splits", "Adj Close"], axis="columns", errors="ignore")
            history["Ticker"] = ticker

            if "Datetime" in history.columns:
                history = history.rename(columns={"Datetime": "Date"})

            compiled_history = pd.concat([compiled_history, history], ignore_index=True)
            fully_checked_tickers.append(ticker)   
      
        compiled_history.drop_duplicates(subset=["Date", "Ticker"], inplace=True)
        save_to_csv(compiled_history, filename)    
        
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

        for ticker in list_of_tickers:
            ticker_object = yf.Ticker(ticker)
            history = ticker_object.history(start=start, end=end, interval=interval).reset_index().drop(["Dividends", "Stock Splits", "Adj Close"], axis="columns", errors="ignore")
            history["Ticker"] = ticker

            if "Datetime" in history.columns:
                history = history.rename(columns={"Datetime": "Date"})

            compiled_history = pd.concat([compiled_history, history], ignore_index=True)
        
        print(compiled_history.to_string())
        save_to_csv(compiled_history, filename)

def fetch_live_price(tickers):
    for ticker in tickers:
        current_ticker = yf.Ticker(ticker)
        print(f"{ticker} current price = ${current_ticker.fast_info['lastPrice']:.2f}")

def save_to_csv(dataframe, filename):
    dataframe.to_csv(filename, index=False)

def load_from_csv(filename):
    if Path(filename).exists():
        df = pd.read_csv(filename)
        df["Date"] = pd.to_datetime(df["Date"], utc=True).dt.tz_convert("America/New_York")
        return df
    else:
        print("File does not exist")

def get_filename(interval):
    return f"data/historical_data_{interval}.csv"

def get_internal_missing_ranges(dataframe, start, end, interval):
    requested_range_dataframe  = dataframe[(dataframe["Date"] >= start) & (dataframe["Date"] <= end)].sort_values(by="Date")
    gaps = []

    # Case 1: nothing in range → entire range is a gap
    if requested_range_dataframe.empty:
        return [(start, end)]
    
    # Case 2: check between existing rows
    for i in range(len(requested_range_dataframe) - 1):
        current_date = requested_range_dataframe.iloc[i]["Date"]
        next_date = requested_range_dataframe.iloc[i+1]["Date"]
        if next_date > current_date + pd.Timedelta(INTERVAL_TO_TIMEDIFF[interval]):
            gaps.append((current_date + pd.Timedelta(INTERVAL_TO_TIMEDIFF[interval]), next_date))

    return gaps

"""
Testing for 1d
"""
# fetch_historical_data(["AAPL"], "2025-08-12", "2025-08-18", "1d")
# fetch_historical_data(["AAPL"], "2025-08-01", "2025-09-01", "1d")
fetch_historical_data(["AAPL"], "2025-08-01", "2025-09-01", "1d")

"""
Testing for live prices
"""
# fetch_live_price(["AAPL", "MSFT", "TSLA", "AMZN"])