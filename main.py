import yfinance as yf
import pandas as pd
from pathlib import Path
from datetime import datetime
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

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
        compiled_history = load_from_csv(filename).sort_values(by=["Ticker", "Date"])
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
        compiled_history.sort_values(by=["Ticker", "Date"], inplace=True)
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
        compiled_history.sort_values(by=["Ticker", "Date"], inplace=True)
        save_to_csv(compiled_history, filename)

def fetch_live_price(tickers):
    for ticker in tickers:
        current_ticker = yf.Ticker(ticker)
        print(f"{ticker} current price = ${current_ticker.fast_info['lastPrice']:.2f}")

def analyse_stock_data(ticker, days_range):
    compiled_history = load_from_csv("data/historical_data_1d.csv").sort_values(by=["Ticker", "Date"])
    
    if ticker in compiled_history["Ticker"].values:
        ticker_specific_dataframe = compiled_history[compiled_history["Ticker"] == ticker]

        ticker_object = yf.Ticker(ticker)
        history = ticker_object.history(period="100d").reset_index().drop(["Dividends", "Stock Splits", "Adj Close"], axis="columns", errors="ignore")
        most_recent_trading_day = history["Date"].iloc[-1]
        start_trading_day = history["Date"].iloc[-days_range]

        if ticker_specific_dataframe["Date"].max() < most_recent_trading_day:
            print("Max date is less than most recent trading day")
            fetch_historical_data([ticker], start_trading_day.strftime('%Y-%m-%d'), (most_recent_trading_day + pd.Timedelta(days=1)).strftime('%Y-%m-%d'), "1d")
        elif ticker_specific_dataframe["Date"].max() == most_recent_trading_day:
            print("Max date is equal to the most recent trading day")

            valid_days = ticker_object.history(period=f"{days_range}d").reset_index()["Date"]
            actual_days = ticker_specific_dataframe.sort_values("Date").tail(days_range)["Date"]

            if set(valid_days) == set(actual_days):
                pass
            else:
                fetch_historical_data([ticker], start_trading_day.strftime('%Y-%m-%d'), (most_recent_trading_day + pd.Timedelta(days=1)).strftime('%Y-%m-%d'), "1d")
        else:
            pass

        """
        Rough Workings
        """
        compiled_history = load_from_csv("data/historical_data_1d.csv").sort_values(by=["Ticker", "Date"])

        requested_range_dataframe = compiled_history[compiled_history["Ticker"] == ticker].tail(days_range)
        # print(requested_range_dataframe)

        new_close = requested_range_dataframe["Close"].iloc[-1]
        old_close = requested_range_dataframe["Close"].iloc[-2]

        first_close = requested_range_dataframe["Close"].iloc[0]

        daily_percentage_change = ((new_close - old_close) / old_close) * 100 
        highest_high = requested_range_dataframe["High"].max()
        lowest_low = requested_range_dataframe["Low"].min()
        avg_closing = requested_range_dataframe["Close"].mean()
        avg_volume = round(requested_range_dataframe["Volume"].mean())
        range_percentage_change = ((new_close - first_close) / first_close) * 100
        requested_range_dataframe["5D MA"] = requested_range_dataframe["Close"].rolling(window=5).mean()

        requested_range_dataframe_copy = requested_range_dataframe.copy().dropna()
        dates = [date.strftime("%Y-%m-%d") for date in requested_range_dataframe_copy["Date"]]
        values = [value for value in requested_range_dataframe_copy["5D MA"]]

        """
        Printing out the stats
        """

        print(f"\n{ticker} Stock Analysis (Past {days_range} days)")

        print(f"\nToday's % Change: {daily_percentage_change:+.2f}%")
        print(f"Range High: ${highest_high:.2f}")
        print(f"Range Low: ${lowest_low:.2f}")
        print(f"Average Closing Price: ${avg_closing:.2f}")
        print(f"Average Volume: {avg_volume:,} shares")
        print(f"% Change Over Range: {range_percentage_change:+.2f}%\n")
        # print(f"\n5-Day Moving Average Trend:")

        # for i in range(len(dates)):
        #     print(f"{dates[i]}: ${values[i]:.2f}")
    else:
        print(f"{ticker} does not exist in the dataframe")

def visualise_stock_data(ticker, days_range):
    compiled_history = load_from_csv("data/historical_data_1d.csv").sort_values(by=["Ticker", "Date"])
    requested_range_dataframe = compiled_history[compiled_history["Ticker"] == ticker].tail(days_range)
    
    # daily_percentage_change(ticker, days_range, requested_range_dataframe)
    volume_over_time(ticker, days_range, requested_range_dataframe)

def daily_percentage_change(ticker, days_range, requested_range_dataframe):
    requested_range_dataframe["% daily change"] = requested_range_dataframe["Close"].pct_change() * 100
    requested_range_dataframe = requested_range_dataframe.dropna(subset=["% daily change"])
    requested_range_dataframe["Positve/Negative"] = requested_range_dataframe["% daily change"].apply(lambda x: "Positive" if x >= 0 else "Negative")
    requested_range_dataframe["Shortend Date"] = requested_range_dataframe["Date"].dt.strftime("%d-%m-%Y")
    colours = {
        "Positive": "#2ecc71",
        "Negative": "#e74c3c"
    }
    
    # print(requested_range_dataframe)

    fig = plt.figure(figsize=(8, 5))
    fig.canvas.manager.set_window_title(f"{ticker} - Daily % Change")

    sns.set_style("whitegrid")
    sns.set_context("notebook")

    plt.axhline(0, color = "black", linewidth = 1)
    sns.barplot(x="Shortend Date", y="% daily change", data=requested_range_dataframe, hue="Positve/Negative", palette=colours)

    plt.title(f"{ticker} - Daily Percentage Change (Last {days_range} days)")
    plt.xlabel("Date")
    plt.ylabel("% change")
    plt.xticks(rotation=45)
    plt.legend([],[], frameon=False)

    plt.tight_layout()
    plt.show()

def volume_over_time(ticker, days_range, requested_range_dataframe):
    requested_range_dataframe["Shortend Date"] = requested_range_dataframe["Date"].dt.strftime("%d-%m-%Y")

    print(requested_range_dataframe)

    fig = plt.figure(figsize=(8, 5))
    fig.canvas.manager.set_window_title(f"{ticker} - Volume Over Time")

    sns.set_style("whitegrid")
    sns.set_context("notebook")

    sns.barplot(x="Shortend Date", y="Volume", data=requested_range_dataframe, color="#3498db")

    plt.title(f"{ticker} - Daily Trading Volume (Last {days_range} days)")
    plt.xlabel("Date")
    plt.ylabel("Volume")
    plt.xticks(rotation=45)
    
    # Format y-axis in millions for readability
    ax = plt.gca()
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{int(x/1e6)}M'))

    plt.tight_layout()
    plt.show()

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
Testing for historical data
"""
# fetch_historical_data(["AAPL"], "2025-08-12", "2025-08-18", "1d")
# fetch_historical_data(["AAPL"], "2025-08-01", "2025-09-01", "1d")
# fetch_historical_data(["AAPL"], "2025-08-01", "2025-09-01", "1d")
# fetch_historical_data(["MSFT", "AAPL"], "2025-08-24", "2025-09-08", "1d")
# fetch_historical_data(["AAPL"], "2025-08-13", "2025-09-13", "1d")
# fetch_historical_data(["AAPL"], "2025-07-01", "2025-08-01", "1d")

"""
Testing for live prices
"""
# fetch_live_price(["AAPL", "MSFT", "TSLA", "AMZN"])

"""
Testing for data analysis
"""
# analyse_stock_data("AAPL", 30)

"""
Testing for visualisation
"""
visualise_stock_data("AAPL", 30)