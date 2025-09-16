import yfinance as yf
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas_market_calendars as mcal
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path
from datetime import datetime, time
from zoneinfo import ZoneInfo


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
    else:
        print(f"{ticker} does not exist in the dataframe")

def visualise_stock_data(ticker, days_range):
    compiled_history = load_from_csv("data/historical_data_1d.csv").sort_values(by=["Ticker", "Date"])
    requested_range_dataframe = compiled_history[compiled_history["Ticker"] == ticker].tail(days_range)
    
    # generate_daily_percentage_change_chart(ticker, days_range, requested_range_dataframe)
    # generate_volume_over_time_chart(ticker, days_range, requested_range_dataframe)
    # generate_closing_price_vs_moving_average_chart(ticker, days_range, requested_range_dataframe)
    # generate_high_low_range_chart(ticker, days_range, requested_range_dataframe)
    # generate_cumulative_returns_chart(ticker, days_range, requested_range_dataframe, 100000)

def generate_daily_percentage_change_chart(ticker, days_range, requested_range_dataframe):
    requested_range_dataframe["% daily change"] = requested_range_dataframe["Close"].pct_change() * 100
    requested_range_dataframe = requested_range_dataframe.dropna(subset=["% daily change"]).copy()
    requested_range_dataframe["Positive/Negative"] = requested_range_dataframe["% daily change"].apply(lambda x: "Positive" if x >= 0 else "Negative")
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
    sns.barplot(x="Shortend Date", y="% daily change", data=requested_range_dataframe, hue="Positive/Negative", palette=colours)

    plt.title(f"{ticker} - Daily Percentage Change (Last {days_range} Days)")
    plt.xlabel("Date")
    plt.ylabel("% change")
    plt.xticks(rotation=45)
    plt.legend([],[], frameon=False)

    plt.tight_layout()
    plt.show()

def generate_volume_over_time_chart(ticker, days_range, requested_range_dataframe):
    requested_range_dataframe["Shortend Date"] = requested_range_dataframe["Date"].dt.strftime("%d-%m-%Y")

    # print(requested_range_dataframe)

    fig = plt.figure(figsize=(8, 5))
    fig.canvas.manager.set_window_title(f"{ticker} - Volume Over Time")

    sns.set_style("whitegrid")
    sns.set_context("notebook")

    sns.barplot(x="Shortend Date", y="Volume", data=requested_range_dataframe, color="#3498db")

    plt.title(f"{ticker} - Daily Trading Volume (Last {days_range} Days)")
    plt.xlabel("Date")
    plt.ylabel("Volume")
    plt.xticks(rotation=45)

    # Format y-axis in millions for readability
    ax = plt.gca()
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{int(x/1e6)}M'))

    plt.tight_layout()
    plt.show()

def generate_closing_price_vs_moving_average_chart(ticker, days_range, requested_range_dataframe):
    requested_range_dataframe["Shortend Date"] = requested_range_dataframe["Date"].dt.strftime("%d-%m-%Y")
    requested_range_dataframe["5D MA"] = requested_range_dataframe["Close"].rolling(window=5).mean()

    # print(requested_range_dataframe)

    fig = plt.figure(figsize=(8, 5))
    fig.canvas.manager.set_window_title(f"{ticker} - Closing Price vs Moving Average")

    sns.set_style("whitegrid")
    sns.set_context("notebook")

    sns.lineplot(x="Shortend Date", y="Close", data=requested_range_dataframe, label="Closing Price", color="#2980b9")
    sns.lineplot(x="Shortend Date", y="5D MA", data=requested_range_dataframe, label="5-Day MA", color="#f39c12")

    plt.title(f"{ticker} - Closing Price with 5-Day Moving Average (Last {days_range} Days)")
    plt.xlabel("Date")
    plt.ylabel("Price")
    plt.xticks(rotation=45)
    plt.legend()

    ax = plt.gca()
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'${x:,.0f}'))
    plt.xlim(requested_range_dataframe["Shortend Date"].iloc[0], requested_range_dataframe["Shortend Date"].iloc[-1])

    plt.tight_layout()
    plt.show()

def generate_high_low_range_chart(ticker, days_range, requested_range_dataframe):
    requested_range_dataframe["Shortend Date"] = requested_range_dataframe["Date"].dt.strftime("%d-%m-%Y")
    requested_range_dataframe["High-Low Range"] = (requested_range_dataframe["High"] - requested_range_dataframe["Low"])

    # print(requested_range_dataframe)

    fig = plt.figure(figsize=(8, 5))
    fig.canvas.manager.set_window_title(f"{ticker} - Daily High-Low Range")

    sns.set_style("whitegrid")
    sns.set_context("notebook")

    plt.fill_between(requested_range_dataframe["Shortend Date"], requested_range_dataframe["High-Low Range"], color="#3498db", alpha=0.4, edgecolor="#2980b9")

    plt.title(f"{ticker} - Daily High-Low Range (Last {days_range} Days)")
    plt.xlabel("Date")
    plt.ylabel("Price Range")
    plt.xticks(rotation=45)

    plt.xlim(requested_range_dataframe["Shortend Date"].iloc[0], requested_range_dataframe["Shortend Date"].iloc[-1])
    plt.ylim(bottom=0)
    ax = plt.gca()
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'${x:,.0f}'))

    plt.tight_layout()
    plt.show()

def generate_cumulative_returns_chart(ticker, days_range, requested_range_dataframe, investment_amount):
    requested_range_dataframe["% daily change"] = requested_range_dataframe["Close"].pct_change() * 100
    requested_range_dataframe = requested_range_dataframe.dropna(subset=["% daily change"]).copy()  
    requested_range_dataframe["Cumulative Returns"] = investment_amount * ((1 + requested_range_dataframe["% daily change"] / 100).cumprod())
    requested_range_dataframe["Shortend Date"] = requested_range_dataframe["Date"].dt.strftime("%d-%m-%Y")

    fig = plt.figure(figsize=(8, 5))
    fig.canvas.manager.set_window_title(f"{ticker} - Cumulative Returns")

    sns.set_style("whitegrid")
    sns.set_context("notebook")

    sns.lineplot(x="Shortend Date", y="Cumulative Returns", data=requested_range_dataframe, color="#e67e22", linewidth=2)

    plt.title(f"{ticker} - Cumulative Returns (Last {days_range} Days)")
    plt.xlabel("Date")
    plt.ylabel(f"Value of ${investment_amount:,} Invested")
    plt.xticks(rotation=45)

    plt.xlim(requested_range_dataframe["Shortend Date"].iloc[0], requested_range_dataframe["Shortend Date"].iloc[-1])
    plt.ylim(bottom=investment_amount)
    ax = plt.gca()
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'${x:,.0f}'))

    plt.tight_layout()
    plt.show()

def percentage_change_alert(list_of_ticker, alert_threshold):
    today = datetime.now().date()
    nyse = mcal.get_calendar("NYSE")
    trading_schedule = nyse.schedule(start_date=today, end_date=today)

    utc_time = datetime.now(tz=ZoneInfo("UTC"))
    eastern_time = utc_time.astimezone(ZoneInfo("America/New_York")).time()
    market_open_time = time(hour=9, minute=30, second=0)
    market_close_time = time(hour=16, minute=0, second=0)

    # eastern_time = time(hour=19, minute=0, second=0)

    strings = []

    if today in trading_schedule.index.date and eastern_time >= market_close_time:
        for ticker in list_of_ticker:
            ticker_object = yf.Ticker(ticker)
            history =  ticker_object.history(period="2d")

            if len(history) < 2:
                print(f"Not enough data for {ticker}")
                continue

            last_close = history["Close"].iloc[-1]
            prev_close = history["Close"].iloc[-2]

            percentage_change = ((last_close - prev_close) / prev_close) * 100

            if percentage_change > alert_threshold:
                string = f"ALERT: {ticker} rose {percentage_change:+.2f}% today!"
                strings.append(string)
                print(string)
            elif percentage_change < -alert_threshold:
                string = f"ALERT: {ticker} dropped {percentage_change:+.2f}% today!"
                strings.append(string)
                print(string)
            else:
                string = f"{ticker}: Does not meet threshold requirement."
                strings.append(string)
                print(string)        

        body = f"Daily Stock Alerts:\n\n{'\n'.join(strings)}"
    elif today not in trading_schedule.index.date:
        string = "Market closed today (holiday/weekend)."
        body = string
        print(string)
    elif eastern_time < market_open_time:
        string = "Market not open yet — waiting for open."
        body = string
        print(string)
    elif market_open_time <= eastern_time < market_close_time:
        string = "Market is open — wait until close for daily % change."
        body = string
        print(string)

    subject = f"Stock Market Update - {today.strftime('%d %b %Y')}"
    to = "abdussamadmohit1@gmail.com"
    email_alerts(subject, to, body)

def email_alerts(subject, to, body):
    EMAIL_ADDRESS = os.environ.get("EMAIL_USER")
    EMAIL_PASSWORD = os.environ.get("EMAIL_PASS")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to
    msg.set_content(body)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)

        smtp.send_message(msg)

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
# fetch_historical_data(["AAPL"], "2025-08-28", "2025-09-15", "1d")

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
# visualise_stock_data("AAPL", 30)

"""
Testing for alerts
"""
percentage_change_alert(["AAPL", "MSFT", "TSLA", "VODL.XC"], 0.5)

"""
Testing for email alerts
"""
# email_alerts("Testing", "abdussamadmohit1@gmail.com", "This is working!")