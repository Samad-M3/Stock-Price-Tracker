import yfinance as yf
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas_market_calendars as mcal
import sys
import os
import smtplib
import json
import socket
from email.message import EmailMessage
from pathlib import Path
from datetime import datetime, time
from zoneinfo import ZoneInfo

class StockTracker:

    COLUMN_NAMES = ["Date", "Open", "High", "Low", "Close", "Volume", "Ticker"]
    MAX_LOOKBACK_DAYS = 180
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
    
    MASTER_HISTORY = None
    MASTER_FILENAME = "data/historical_data_1d.csv"

    def __init__(self):
        if Path(StockTracker.MASTER_FILENAME).exists():
            try:
                StockTracker.MASTER_HISTORY = self.load_from_csv(StockTracker.MASTER_FILENAME).sort_values(by=["Ticker", "Date"])
            except pd.errors.ParserError as e:
                print(f"\n⚠️  Could not load {StockTracker.MASTER_FILENAME}, File may be corrupted: {e}")
            except PermissionError as e:
                print(f"\n⚠️  Could not read {StockTracker.MASTER_FILENAME}, Check file permissions: {e}")
        else:
            print("Dataframe for '1d' interval doesn't exist, Fetch some data first")

    def main_menu(self):
        today = datetime.now().date()
        lower_bound_date = datetime(1950, 1, 1).date()

        while True:
            while True:
                try:
                    print(f"\n🏦 Welcome to the Stock Price Tracker!")
                    option = int(input(f"\n1. Fetch Historical Data \n2. Fetch Live Price \n3. Analyse Stock Data \n4. Visualise Stock Data \n5. Configure & Test Percentage Change Alert \n6. Exit Program \n\nChoose an option: "))
                    if option < 1 or option > 6:
                        raise ValueError("Option must be between 1 and 6, Please try again")
                except ValueError as e:
                    print(e)
                else:
                    break

            if option == 1:
                list_of_tickers = []

                while True:
                    ticker = self.validated_ticker()
                    list_of_tickers.append(ticker)
                    add_another_ticker = self.validated_option_yes_or_no()
                    if add_another_ticker == "Yes":
                        pass
                    elif add_another_ticker == "No":
                        break

                start_date, parsed_start_date = self.get_start_date(today, lower_bound_date)

                end_date = self.get_end_date(today, parsed_start_date)

                interval = self.get_interval()

                while True:
                    if interval ==  "1m":
                        seven_days_from_today = today - pd.Timedelta(days=7)
                        if parsed_start_date < seven_days_from_today:
                            print(f"\n1m interval has a maximum lookback of 7 days from today, Please try again")

                            start_date, parsed_start_date = self.get_start_date(today, lower_bound_date)

                            end_date = self.get_end_date(today, parsed_start_date)

                            interval = self.get_interval()
                        else:
                            break
                    elif interval in {"2m", "5m", "15m", "30m", "60m", "90m"}:
                        sixty_days_from_today = today - pd.Timedelta(days=59)
                        if parsed_start_date < sixty_days_from_today:
                            print(f"\n2m/5m/15m/30m/60m/90m interval has a maximum lookback of 60 days from today, Please try again")
                            
                            start_date, parsed_start_date = self.get_start_date(today, lower_bound_date)

                            end_date = self.get_end_date(today, parsed_start_date)

                            interval = self.get_interval()
                        else:
                            break
                    else:
                        break

                self.fetch_historical_data(list_of_tickers, start_date, end_date, interval, verbose=True)

            elif option == 2:
                list_of_tickers = []

                while True:
                    ticker = self.validated_ticker()
                    list_of_tickers.append(ticker)
                    add_another_ticker = self.validated_option_yes_or_no()
                    if add_another_ticker == "Yes":
                        pass
                    elif add_another_ticker == "No":
                        break

                self.fetch_live_price(list_of_tickers)

            elif option == 3:
                if Path(StockTracker.MASTER_FILENAME).exists():
                    ticker = self.validated_ticker()
                    days_back = self.validated_look_back_value(2)

                    self.analyse_stock_data(ticker, days_back)
                else:
                    print(f"\n⚠️  Historical data for interval **1d** doesn't exist, Please fetch some data first (Option 1)")

            elif option == 4:
                self.chart_selection_menu()

            elif option == 5:
                self.email_alert_menu()

            elif option == 6:
                self.exit_program()
    
    def chart_selection_menu(self):
        while True:
            while True:
                try:
                    print(f"\n📊 Chart Options:")
                    option = int(input(f"\n1. View Daily Percentage Change \n2. View Volume Over Time \n3. Compare Closing Price VS Moving Average \n4. View Daily High-Low Range \n5. View Cumulative Returns \n6. Back to Main Menu \n\nChoose an option: "))
                    if option < 1 or option > 6:
                        raise ValueError("Option must be between 1 and 6, Please try again")    
                except ValueError as e:
                    print(e)
                else:
                    break
            
            if option == 1:
                if Path(StockTracker.MASTER_FILENAME).exists():
                    ticker = self.validated_ticker()
                    days_back = self.validated_look_back_value(2)

                    self.generate_daily_percentage_change_chart(ticker, days_back)
                else:
                    print(f"\n⚠️  Historical data for interval **1d** doesn't exist, Please fetch some data first (Option 1)")

            elif option == 2:
                if Path(StockTracker.MASTER_FILENAME).exists():
                    ticker = self.validated_ticker()
                    days_back = self.validated_look_back_value(1)

                    self.generate_volume_over_time_chart(ticker, days_back)
                else:
                    print(f"\n⚠️  Historical data for interval **1d** doesn't exist, Please fetch some data first (Option 1)")

            elif option == 3:
                if Path(StockTracker.MASTER_FILENAME).exists():
                    ticker = self.validated_ticker()
                    days_back = self.validated_look_back_value(2)

                    self.generate_closing_price_vs_moving_average_chart(ticker, days_back)
                else:
                    print(f"\n⚠️  Historical data for interval **1d** doesn't exist, Please fetch some data first (Option 1)")

            elif option == 4:
                if Path(StockTracker.MASTER_FILENAME).exists():
                    ticker = self.validated_ticker()
                    days_back = self.validated_look_back_value(2)

                    self.generate_high_low_range_chart(ticker, days_back)
                else:
                    print(f"\n⚠️  Historical data for interval **1d** doesn't exist, Please fetch some data first (Option 1)")

            elif option == 5:
                if Path(StockTracker.MASTER_FILENAME).exists():
                    ticker = self.validated_ticker()
                    days_back = self.validated_look_back_value(2)

                    while True:
                        try:
                            investment_amount = int(input(f"Enter how much you would like to invest: "))
                            if investment_amount < 1:
                                raise ValueError(f"Invalid amount, Please enter a positive amount\n")
                        except ValueError as e:
                            print(e)
                        else:
                            break

                    self.generate_cumulative_returns_chart(ticker, days_back, investment_amount)
                else:
                    print(f"\n⚠️  Historical data for interval **1d** doesn't exist, Please fetch some data first (Option 1)")

            elif option == 6:
                break

    def email_alert_menu(self):
        while True:
            while True:
                try:
                    option = int(input(f"\n1. Configure Alerts \n2. Test Alerts \n3. Back to Main Menu \n\nChoose an option: "))
                    if option < 1 or option > 3:
                        raise ValueError("Option must be between 1 and 3, Please try again")
                except ValueError as e:
                    print(e)
                else:
                    break

            if option == 1:
                list_of_tickers = []

                while True:
                    ticker = self.validated_ticker()
                    list_of_tickers.append(ticker)
                    add_another_ticker = self.validated_option_yes_or_no()
                    if add_another_ticker == "Yes":
                        pass
                    elif add_another_ticker == "No":
                        break
                
                while True:
                    try:
                        threshold_value = float(input(f"\nEnter a value for the threshold [0 - 500]: "))
                        if threshold_value < 0 or threshold_value > 500:
                            raise ValueError("Invalid threshold value, Please try again")
                    except ValueError as e:
                        print(e)
                    else:
                        break

                recipient_email = self.validated_email_address()

                try:
                    data = None

                    with open("alert_config.json", "r") as f:
                        data = json.load(f)
                        data["tickers"] = list_of_tickers
                        data["threshold"] = threshold_value
                        data["recipient_email"] = recipient_email

                    with open("alert_config.json", "w") as f:
                        json.dump(data, f, indent=4)

                    print(f"\nConfiguration Successful!")
                except json.JSONDecodeError:
                    print(f"\n⚠️  Error: **alert_config.json** is corrupted or not valid JSON")
                except (PermissionError, OSError) as e:
                    print(f"\n⚠️  Error writing configuration: {e}")
            
            elif option == 2:
                try:
                    data = None

                    with open("alert_config.json", "r") as f:
                        data = json.load(f)

                        if len(data["tickers"]) == 0 or data["threshold"] is None or len(data["recipient_email"]) == 0:
                            print(f"\n⚠️  Error: Alerts are not configured yet, Please configure alerts first (Option 1)")
                        else:
                            list_of_tickers = data["tickers"]
                            threshold_value = data["threshold"]
                            recipient_email = data["recipient_email"]

                            self.percentage_change_alert(list_of_tickers, threshold_value, recipient_email, verbose=True)
                except json.JSONDecodeError:
                    print(f"\n⚠️  Error: **alert_config.json** is corrupted or not valid JSON, Please reconfigure alerts (Option 1)")
                except PermissionError:
                    print(f"\n⚠️  Error: The program does not have permission to read **alert_config.json**, Please reconfigure alerts (Option 1)")

            elif option == 3:
                break

    def fetch_historical_data(self, list_of_tickers, start, end, interval, verbose=False):
        # Convert string to datetime (defaults to naive/no timezone)
        start = pd.to_datetime(start)
        # If naive (no timezone), attach New York timezone
        # If already tz-aware, convert it to New York timezone
        if start.tzinfo is None:
            start = start.tz_localize("America/New_York")
        else:
            start = start.tz_convert("America/New_York")
        
        # Repeat for end date
        end = pd.to_datetime(end)
        # Localize if naive, convert if already tz-aware
        if end.tzinfo is None:
            end = end.tz_localize("America/New_York")
        else:
            end = end.tz_convert("America/New_York")

        filename = self.get_filename(interval)

        if Path(filename).exists():
            try:
                # Load CSV and ensure data is ordered by Ticker (grouped) and Date (chronological)
                compiled_history = self.load_from_csv(filename).sort_values(by=["Ticker", "Date"])
            except pd.errors.ParserError as e:
                print(f"\n⚠️  Could not load {filename}, File may be corrupted: {e}")
            except PermissionError as e:
                print(f"\n⚠️  Could not read {filename}, Check file permissions: {e}")

            present_tickers = []
            missing_tickers = []
            fully_checked_tickers = []

            for ticker in list_of_tickers:
                if ticker in compiled_history["Ticker"].values:
                    present_tickers.append(ticker)
                else:
                    missing_tickers.append(ticker)

            for ticker in present_tickers:
                # Returns a dataframe for just that ticker
                ticker_specific_dataframe = compiled_history[compiled_history["Ticker"] == ticker]

                # Check for gaps between start and end
                internal_gaps = self.get_internal_missing_ranges(ticker_specific_dataframe, start, end, interval)
                ticker_object = yf.Ticker(ticker)
                for gap_start, gap_end in internal_gaps:
                    try:
                        history = ticker_object.history(start=gap_start, end=gap_end, interval=interval).reset_index().drop(["Dividends", "Stock Splits", "Adj Close"], axis="columns", errors="ignore")
                    except Exception as e:
                        print(f"\n⚠️  Error fetching data for {ticker}: {e}")
                        history = pd.DataFrame()

                    history["Ticker"] = ticker

                    # For intraday intervals Yahoo returns "Datetime" instead of "Date" → normalise column name
                    if "Datetime" in history.columns:
                            history = history.rename(columns={"Datetime": "Date"})

                    # Skip if no data returned (e.g. weekends/holidays), else append new rows to compiled_history
                    if history.empty:
                            pass
                    else:
                        compiled_history = pd.concat([compiled_history, history], ignore_index=True)

                # Check to see if the shortest date in the dataframe is earlier than or equal to the start date
                # Check to see if the longest date in the dateframe is later than or equal to the end date
                if start >= ticker_specific_dataframe["Date"].min() and end <= ticker_specific_dataframe["Date"].max():
                    pass
                else:
                    if start < ticker_specific_dataframe["Date"].min() < end:
                        ticker_object = yf.Ticker(ticker)
                        try:
                            history = ticker_object.history(start=start, end=ticker_specific_dataframe["Date"].min(), interval=interval).reset_index().drop(["Dividends", "Stock Splits", "Adj Close"], axis="columns", errors="ignore")
                        except Exception as e:
                            print(f"\n⚠️  Error fetching data for {ticker}: {e}")
                            history = pd.DataFrame()

                        history["Ticker"] = ticker

                        # For intraday intervals Yahoo returns "Datetime" instead of "Date" → normalise column name
                        if "Datetime" in history.columns:
                            history = history.rename(columns={"Datetime": "Date"})

                        # Skip if no data returned (e.g. weekends/holidays), else append new rows to compiled_history
                        if history.empty:
                            pass
                        else:
                            compiled_history = pd.concat([compiled_history, history], ignore_index=True)

                    if end > ticker_specific_dataframe["Date"].max() > start:
                        ticker_object = yf.Ticker(ticker)
                        try:
                            history = ticker_object.history(start=ticker_specific_dataframe["Date"].max(), end=end, interval=interval).reset_index().drop(["Dividends", "Stock Splits", "Adj Close"], axis="columns", errors="ignore")
                        except Exception as e:
                            print(f"\n⚠️  Error fetching data for {ticker}: {e}")
                            history = pd.DataFrame()

                        history["Ticker"] = ticker

                        # For intraday intervals Yahoo returns "Datetime" instead of "Date" → normalise column name
                        if "Datetime" in history.columns:
                            history = history.rename(columns={"Datetime": "Date"})

                        # Skip if no data returned (e.g. weekends/holidays), else append new rows to compiled_history
                        if history.empty:
                            pass
                        else:
                            compiled_history = pd.concat([compiled_history, history], ignore_index=True)

                fully_checked_tickers.append(ticker)
                    
            for ticker in missing_tickers:
                ticker_object = yf.Ticker(ticker)
                try:
                    history = ticker_object.history(start=start, end=end, interval=interval).reset_index().drop(["Dividends", "Stock Splits", "Adj Close"], axis="columns", errors="ignore")
                except Exception as e:
                    print(f"\n⚠️  Error fetching data for {ticker}: {e}")
                    history = pd.DataFrame()

                history["Ticker"] = ticker

                # For intraday intervals Yahoo returns "Datetime" instead of "Date" → normalise column name
                if "Datetime" in history.columns:
                    history = history.rename(columns={"Datetime": "Date"})     

                # Skip if no data returned (e.g. weekends/holidays), else append new rows to compiled_history
                if history.empty:
                    pass
                else:
                    compiled_history = pd.concat([compiled_history, history], ignore_index=True)       

                fully_checked_tickers.append(ticker)   
        
            # Remove duplicate rows based on Date and Ticker, then sort by Ticker and Date
            # inplace=True updates compiled_history directly without creating a new DataFrame
            compiled_history.drop_duplicates(subset=["Date", "Ticker"], inplace=True)
            compiled_history.sort_values(by=["Ticker", "Date"], inplace=True)
            try:
                self.save_to_csv(compiled_history, filename)
            except PermissionError as e:
                print(f"\n⚠️  Could not write to {filename}, Check file permissions: {e}")
            except OSError as e:
                print(f"\n⚠️  OS error while saving {filename}: {e}")

            if interval == "1d":
                StockTracker.MASTER_HISTORY = compiled_history

            if verbose:
                combined_resulting_dataframe = pd.DataFrame(columns=StockTracker.COLUMN_NAMES) # Creating an empty dataframe so each tickers filtered data can be appeneded on and representred as one big dataframe
                # Forces each column into the correct data type
                combined_resulting_dataframe = combined_resulting_dataframe.astype({
                    "Date": "datetime64[ns]",
                    "Open": "float64",
                    "High": "float64",
                    "Low": "float64",
                    "Close": "float64",
                    "Volume": "Int64",
                    "Ticker": "string"
                })

                for ticker in fully_checked_tickers:
                    combined_resulting_dataframe = pd.concat([combined_resulting_dataframe, compiled_history[(compiled_history["Ticker"] == ticker) & (compiled_history["Date"] >= start) & (compiled_history["Date"] <= end)]])

                print() # Readability purposes
                print(combined_resulting_dataframe.to_string())
        else:
            compiled_history = pd.DataFrame(columns=StockTracker.COLUMN_NAMES)
            # Forces each column into the correct data type
            compiled_history = compiled_history.astype({
                "Date": "datetime64[ns]",
                "Open": "float64",
                "High": "float64",
                "Low": "float64",
                "Close": "float64",
                "Volume": "Int64",
                "Ticker": "string"
            })

            for ticker in list_of_tickers:
                ticker_object = yf.Ticker(ticker)
                try:
                    history = ticker_object.history(start=start, end=end, interval=interval).reset_index().drop(["Dividends", "Stock Splits", "Adj Close"], axis="columns", errors="ignore")
                except Exception as e:
                    print(f"\n⚠️  Error fetching data for {ticker}: {e}")
                    history = pd.DataFrame()

                history["Ticker"] = ticker

                # For intraday intervals Yahoo returns "Datetime" instead of "Date" → normalise column name
                if "Datetime" in history.columns:
                    history = history.rename(columns={"Datetime": "Date"})

                # Skip if no data returned (e.g. weekends/holidays), else append new rows to compiled_history
                if history.empty:
                    pass
                else:
                    compiled_history = pd.concat([compiled_history, history], ignore_index=True)
            
            compiled_history.drop_duplicates(subset=["Date", "Ticker"], inplace=True)
            compiled_history.sort_values(by=["Ticker", "Date"], inplace=True)
            try:
                self.save_to_csv(compiled_history, filename)
            except PermissionError as e:
                print(f"\n⚠️  Could not write to {filename}, Check file permissions: {e}")
            except OSError as e:
                print(f"\n⚠️  OS error while saving {filename}: {e}")

            if interval == "1d":
                StockTracker.MASTER_HISTORY = compiled_history

            if verbose:
                print(compiled_history.to_string())

    @staticmethod
    def fetch_live_price(list_of_tickers):
        print(f"\nLive Prices of Tickers:\n")
        for ticker in list_of_tickers:
            try:
                current_ticker = yf.Ticker(ticker)
                last_price = current_ticker.fast_info.get("lastPrice")
                if last_price is not None:
                    print(f"{ticker} current price = ${last_price:.2f}")
                else:
                    print(f"\n⚠️  {ticker}: Price data not available")
            except Exception as e:
                print(f"\n⚠️  Error fetching live price for {ticker}: {e}")
 
    def analyse_stock_data(self, ticker, days_range):
        requested_range_dataframe, valid_trading_days, days_range = self.get_requested_range_dataframe(ticker, days_range)

        """
        Calculations
        """

        new_close = requested_range_dataframe["Close"].iloc[-1]
        old_close = requested_range_dataframe["Close"].iloc[-2]

        first_close = requested_range_dataframe["Close"].iloc[0]

        daily_percentage_change = ((new_close - old_close) / old_close) * 100 
        highest_high = requested_range_dataframe["High"].max()
        lowest_low = requested_range_dataframe["Low"].min()
        avg_closing = requested_range_dataframe["Close"].mean()
        avg_volume = round(requested_range_dataframe["Volume"].mean())
        range_percentage_change = ((new_close - first_close) / first_close) * 100 # % change in closing price across the entire range (first → last day)

        """
        Printing out the stats
        """

        print(f"\n{ticker} Stock Analysis (Past {days_range} Trading Days: {valid_trading_days[-days_range].date()} → {valid_trading_days[-1].date()})")

        print(f"\nToday's % Change: {daily_percentage_change:+.2f}%")
        print(f"Range High: ${highest_high:.2f}")
        print(f"Range Low: ${lowest_low:.2f}")
        print(f"Average Closing Price: ${avg_closing:.2f}")
        print(f"Average Volume: {avg_volume:,} shares")
        print(f"% Change Over Range: {range_percentage_change:+.2f}%")

    def generate_daily_percentage_change_chart(self, ticker, days_range):
        requested_range_dataframe, valid_trading_days, days_range = self.get_requested_range_dataframe(ticker, days_range)

        requested_range_dataframe["% daily change"] = requested_range_dataframe["Close"].pct_change() * 100
        requested_range_dataframe = requested_range_dataframe.dropna(subset=["% daily change"]).copy()
        requested_range_dataframe["Positive/Negative"] = requested_range_dataframe["% daily change"].apply(lambda x: "Positive" if x >= 0 else "Negative") # Label each row as "Positive" or "Negative" based on the sign of its daily % change
        requested_range_dataframe["Shortend Date"] = requested_range_dataframe["Date"].dt.strftime("%d-%m-%Y")
        colours = {
            "Positive": "#2ecc71",
            "Negative": "#e74c3c"
        }

        print(f"\nℹ️  Note: First row for {ticker} percentage change is NaN, so it was dropped")

        fig = plt.figure(figsize=(8, 5))
        fig.canvas.manager.set_window_title(f"{ticker} - Daily % Change")

        sns.set_style("whitegrid")
        sns.set_context("notebook")

        plt.axhline(0, color = "black", linewidth = 1)
        sns.barplot(x="Shortend Date", y="% daily change", data=requested_range_dataframe, hue="Positive/Negative", palette=colours)

        plt.title(f"{ticker} - Daily Percentage Change (Last {days_range - 1} Trading Days)")
        plt.xlabel("Date")
        plt.ylabel("% change")
        plt.xticks(rotation=45)
        plt.legend([],[], frameon=False)

        plt.tight_layout()
        plt.show()

    def generate_volume_over_time_chart(self, ticker, days_range):
        requested_range_dataframe, valid_trading_days, days_range = self.get_requested_range_dataframe(ticker, days_range)

        requested_range_dataframe["Shortend Date"] = requested_range_dataframe["Date"].dt.strftime("%d-%m-%Y")

        fig = plt.figure(figsize=(8, 5))
        fig.canvas.manager.set_window_title(f"{ticker} - Volume Over Time")

        sns.set_style("whitegrid")
        sns.set_context("notebook")

        sns.barplot(x="Shortend Date", y="Volume", data=requested_range_dataframe, color="#3498db")

        plt.title(f"{ticker} - Daily Trading Volume (Last {days_range} Trading Days)")
        plt.xlabel("Date")
        plt.ylabel("Volume")
        plt.xticks(rotation=45)

        # Format y-axis in millions for readability
        ax = plt.gca()
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{int(x/1e6)}M'))

        plt.tight_layout()
        plt.show()

    def generate_closing_price_vs_moving_average_chart(self, ticker, days_range):
        requested_range_dataframe, valid_trading_days, days_range = self.get_requested_range_dataframe(ticker, days_range)

        requested_range_dataframe["Shortend Date"] = requested_range_dataframe["Date"].dt.strftime("%d-%m-%Y")
        requested_range_dataframe["5D MA"] = requested_range_dataframe["Close"].rolling(window=5).mean()

        fig = plt.figure(figsize=(8, 5))
        fig.canvas.manager.set_window_title(f"{ticker} - Closing Price vs Moving Average")

        sns.set_style("whitegrid")
        sns.set_context("notebook")

        sns.lineplot(x="Shortend Date", y="Close", data=requested_range_dataframe, label="Closing Price", color="#2980b9")
        sns.lineplot(x="Shortend Date", y="5D MA", data=requested_range_dataframe, label="5-Day MA", color="#f39c12")

        plt.title(f"{ticker} - Closing Price with 5-Day Moving Average (Last {days_range} Trading Days)")
        plt.xlabel("Date")
        plt.ylabel("Price")
        plt.xticks(rotation=45)
        plt.legend()

        ax = plt.gca()
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'${x:,.0f}'))
        plt.xlim(requested_range_dataframe["Shortend Date"].iloc[0], requested_range_dataframe["Shortend Date"].iloc[-1])

        plt.tight_layout()
        plt.show()

    def generate_high_low_range_chart(self, ticker, days_range):
        requested_range_dataframe, valid_trading_days, days_range = self.get_requested_range_dataframe(ticker, days_range)
        
        requested_range_dataframe["Shortend Date"] = requested_range_dataframe["Date"].dt.strftime("%d-%m-%Y")
        requested_range_dataframe["High-Low Range"] = (requested_range_dataframe["High"] - requested_range_dataframe["Low"])

        fig = plt.figure(figsize=(8, 5))
        fig.canvas.manager.set_window_title(f"{ticker} - Daily High-Low Range")

        sns.set_style("whitegrid")
        sns.set_context("notebook")

        plt.fill_between(requested_range_dataframe["Shortend Date"], requested_range_dataframe["High-Low Range"], color="#3498db", alpha=0.4, edgecolor="#2980b9")

        plt.title(f"{ticker} - Daily High-Low Range (Last {days_range} Trading Days)")
        plt.xlabel("Date")
        plt.ylabel("Price Range")
        plt.xticks(rotation=45)

        plt.xlim(requested_range_dataframe["Shortend Date"].iloc[0], requested_range_dataframe["Shortend Date"].iloc[-1])
        plt.ylim(bottom=0)
        ax = plt.gca()
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'${x:,.0f}'))

        plt.tight_layout()
        plt.show()

    def generate_cumulative_returns_chart(self, ticker, days_range, investment_amount):
        requested_range_dataframe, valid_trading_days, days_range = self.get_requested_range_dataframe(ticker, days_range)

        requested_range_dataframe["% daily change"] = requested_range_dataframe["Close"].pct_change() # Daily returns as fractional change (e.g., 0.02 = +2%)
        multipliers = (1 + requested_range_dataframe["% daily change"]).fillna(1) # Convert returns to growth multipliers (1 + change); replace NaN in first row with 1 (no change)
        requested_range_dataframe["Cumulative Returns"] = investment_amount * multipliers.cumprod() # Cumulative compounded value of investment over time
        requested_range_dataframe["Shortend Date"] = requested_range_dataframe["Date"].dt.strftime("%d-%m-%Y")

        fig = plt.figure(figsize=(8, 5))
        fig.canvas.manager.set_window_title(f"{ticker} - Cumulative Returns")

        sns.set_style("whitegrid")
        sns.set_context("notebook")

        sns.lineplot(x="Shortend Date", y="Cumulative Returns", data=requested_range_dataframe, color="#e67e22", linewidth=2)

        plt.title(f"{ticker} - Cumulative Returns (Last {days_range} Trading Days)")
        plt.xlabel("Date")
        plt.ylabel(f"Value of a ${investment_amount:,} Investment")
        plt.xticks(rotation=45)

        plt.xlim(requested_range_dataframe["Shortend Date"].iloc[0], requested_range_dataframe["Shortend Date"].iloc[-1])
        ax = plt.gca()

        if days_range == 2 and investment_amount < 7:
            ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'${x:,.3f}'))
        elif investment_amount < 31:
            ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'${x:,.2f}'))
        else:
            ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'${x:,.0f}'))

        plt.tight_layout()
        plt.show()

    def percentage_change_alert(self, list_of_tickers, alert_threshold, recipient_email, verbose=False):
        today = datetime.now().date()
        nyse = mcal.get_calendar("NYSE")
        trading_schedule = nyse.schedule(start_date=today, end_date=today)

        utc_time = datetime.now(tz=ZoneInfo("UTC"))
        eastern_time = utc_time.astimezone(ZoneInfo("America/New_York")).time()
        market_open_time = time(hour=9, minute=30, second=0)
        market_close_time = time(hour=16, minute=0, second=0)

        # eastern_time = time(hour=1, minute=0, second=0)

        strings = []

        if today in trading_schedule.index.date and eastern_time >= market_close_time:
            for ticker in list_of_tickers:
                try:
                    ticker_object = yf.Ticker(ticker)
                    history = ticker_object.history(period="2d")
                except Exception as e:
                    if verbose:
                        print(f"\n⚠️  Error fetching data for {ticker}: {e}")
                    continue

                if len(history) < 2:
                    if verbose:
                        print(f"Not enough data for {ticker}")
                    continue

                last_close = history["Close"].iloc[-1]
                prev_close = history["Close"].iloc[-2]

                percentage_change = ((last_close - prev_close) / prev_close) * 100

                if percentage_change > alert_threshold:
                    string = f"ALERT: {ticker} rose {percentage_change:+.2f}% today!"
                elif percentage_change < -alert_threshold:
                    string = f"ALERT: {ticker} dropped {percentage_change:+.2f}% today!"
                else:
                    string = f"ALERT: {ticker} does not meet threshold requirement."   
    
                strings.append(string)
                if verbose:
                    print(f"\n{string}")

            if not strings:
                strings.append("No valid alerts generated today.")  

            body = f"Daily Stock Alerts:\n\n{'\n'.join(strings)}"
        elif today in trading_schedule.index.date and eastern_time < market_open_time:
            string = "Market not yet open — waiting to open."
            if verbose:
                print(f"\n{string}")
            body = string
        elif today in trading_schedule.index.date and (market_open_time <= eastern_time < market_close_time):
            string = "Market is open — wait until close for daily % change."
            if verbose:
                print(f"\n{string}")
            body = string
        elif today not in trading_schedule.index.date:
            string = "Market closed today (holiday/weekend)."
            if verbose:
                print(f"\n{string}")
            body = string

        subject = f"Stock Market Update - {today.strftime('%d %b %Y')}"
        self.email_alerts(subject, recipient_email, body)

    @staticmethod
    def email_alerts(subject, to, body):
        # Get email + password from environment variables for security
        EMAIL_ADDRESS = os.environ.get("EMAIL_USER")
        EMAIL_PASSWORD = os.environ.get("EMAIL_PASS")

        # Create email object with subject, sender, recipient, and body
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = to
        msg.set_content(body)

        # Connect to Gmail’s SMTP server using SSL and send the email
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
                smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
                smtp.send_message(msg)
        except smtplib.SMTPAuthenticationError:
            print(f"\n❌  Authentication failed, Check your email and password environment variables")
        except (smtplib.SMTPException, socket.gaierror) as e:
            print(f"\n❌  Failed to send email: {e}")
        except Exception as e:
            print(f"\n❌  Unexpected error while sending email: {e}")

    @staticmethod
    def exit_program():
        print("Closing program...")
        sys.exit(0)

    @staticmethod
    def save_to_csv(dataframe, filename):
        dataframe.to_csv(filename, index=False)

    @staticmethod
    def load_from_csv(filename):
        if Path(filename).exists():
            df = pd.read_csv(filename)
            # Parse "Date" column as timezone-aware UTC datetimes, then convert to NY time
            df["Date"] = pd.to_datetime(df["Date"], utc=True).dt.tz_convert("America/New_York")
            return df
        else:
            print("File does not exist")

    @staticmethod
    def get_filename(interval):
        return f"data/historical_data_{interval}.csv"

    @staticmethod
    def get_internal_missing_ranges(dataframe, start, end, interval):
        # Extract only the rows that fall within the requested date range
        requested_range_dataframe  = dataframe[(dataframe["Date"] >= start) & (dataframe["Date"] <= end)].sort_values(by="Date")

        gaps = []

        # Case 1: No rows at all → entire requested range is missing
        if requested_range_dataframe.empty:
            return [(start, end)]
        
        # Case 2: Check if first row starts after the requested start
        first_row_date = requested_range_dataframe["Date"].iloc[0]
        if first_row_date > start:
            # Gap from requested start until the first available date
            gaps.append((start, first_row_date))
        
        # Case 3: Look for gaps *inside* the available rows
        for i in range(len(requested_range_dataframe) - 1):
            current_date = requested_range_dataframe["Date"].iloc[i]
            next_date = requested_range_dataframe["Date"].iloc[i+1]

            # If the next row jumps by more than one interval → gap
            if next_date > current_date + StockTracker.INTERVAL_TO_TIMEDIFF[interval]:
                # Gap starts just after current_date, and ends at next_date
                gaps.append((current_date + StockTracker.INTERVAL_TO_TIMEDIFF[interval], next_date))

        # Case 4: Check if last row ends before the requested end
        last_row_date = requested_range_dataframe["Date"].iloc[-1]
        if last_row_date < end:
            # Gap from just after last available date until requested end
            gaps.append((last_row_date + StockTracker.INTERVAL_TO_TIMEDIFF[interval], end + StockTracker.INTERVAL_TO_TIMEDIFF[interval]))

        return gaps

    def get_requested_range_dataframe(self, ticker, days_range):

        today = datetime.now().date()
        nyse = mcal.get_calendar("NYSE")
        trading_schedule = nyse.schedule(start_date=today, end_date=today)

        utc_time = datetime.now(tz=ZoneInfo("UTC"))
        eastern_time = utc_time.astimezone(ZoneInfo("America/New_York")).time()
        market_close_time = time(hour=16, minute=0, second=0)

        # Forcing the date
        # today = datetime(2025, 9, 21).date()

        # Forcing the ET time
        # eastern_time = time(hour=14, minute=0, second=0)
        
        if ticker in StockTracker.MASTER_HISTORY["Ticker"].values:
            ticker_specific_dataframe = StockTracker.MASTER_HISTORY[StockTracker.MASTER_HISTORY["Ticker"] == ticker]

            if len(ticker_specific_dataframe) < days_range:
                print(f"\n⚠️  Only {len(ticker_specific_dataframe)} trading days available for {ticker}"
                    f"\nAdjusting requested range from {days_range} → {len(ticker_specific_dataframe)}")
                days_range = len(ticker_specific_dataframe)

            # Today is a trading day and the market has closed for today
            if today in trading_schedule.index.date and eastern_time >= market_close_time:
                list_of_valid_trading_days = []
                list_of_actual_trading_days = []

                # Get all valid trading days up to and including today if it's a trading day
                # NOTE: valid_trading_days only goes back 90 days (adjust if longer lookback is needed)
                valid_trading_days = nyse.valid_days(start_date=today - pd.Timedelta(days=StockTracker.MAX_LOOKBACK_DAYS), end_date=today)

                # Append the last N trading days starting from the most recent (working backwards)
                for i in range(days_range):
                    list_of_valid_trading_days.append(valid_trading_days[-1 - i].date())
                    # print(valid_trading_days[-1 - i].date())

                # Collect the last N dates actually present in the CSV for this ticker (most recent first)
                for i in range(days_range):
                    day = pd.to_datetime(ticker_specific_dataframe["Date"].iloc[-1 - i]).date()
                    list_of_actual_trading_days.append(day)

                # Check if the last N valid trading days match exactly the last N dates in the CSV
                if list_of_valid_trading_days == list_of_actual_trading_days:
                    print("Data matches, can use straight away")
                    pass
                else:
                    print("Data needs to be fetched")
                    # Fetch historical data for this ticker because the CSV is missing some dates
                    # Start date:
                    #   - list_of_valid_trading_days[-1] gives the oldest date in our last N valid trading days
                    #   - valid trading days are stored in reverse chronological order (most recent first)
                    # End date:
                    #   - fetch_historical_data treats start date as inclusive, end date as exclusive
                    #   - today + pd.Timedelta(days=1) ensures that today’s row (most recent trading day) is included in the fetch
                    self.fetch_historical_data([ticker], list_of_valid_trading_days[-1].strftime("%Y-%m-%d"), (today + pd.Timedelta(days=1)).strftime("%Y-%m-%d"), "1d")

            # Today is a trading day and the market is still open or waiting to open
            elif today in trading_schedule.index.date and eastern_time < market_close_time:
                list_of_valid_trading_days = []
                list_of_actual_trading_days = []

                # Get all valid trading days up to yesterday
                # Exclude today because the market is still open; the last valid trading day is yesterday
                valid_trading_days = nyse.valid_days(start_date=today - pd.Timedelta(days=StockTracker.MAX_LOOKBACK_DAYS), end_date=(today - pd.Timedelta(days=1)))

                # Append the last N trading days starting from the most recent (working backwards)
                # Because we have excluded today from valid_trading_days, valid_trading_days[-1] would be yesterday
                for i in range(days_range):
                    list_of_valid_trading_days.append(valid_trading_days[-1 - i].date())
                    # print(valid_trading_days[-1 - i].date())
                    # print()

                # Collect the last N dates actually present in the CSV for this ticker (most recent first)
                for i in range(days_range):
                    day = pd.to_datetime(ticker_specific_dataframe["Date"].iloc[-1 - i]).date()
                    list_of_actual_trading_days.append(day)
                    # print(day)

                # Check if the last N valid trading days match exactly the last N dates in the CSV
                if list_of_valid_trading_days == list_of_actual_trading_days:
                    print("Data matches, can use straight away")
                    pass
                else:
                    print("Data needs to be fetched")
                    # Fetch historical data for this ticker because the CSV is missing some dates
                    # Start date:
                    #   - list_of_valid_trading_days[-1] gives the oldest date in our last N valid trading days
                    # End date:
                    #   - fetch_historical_data treats start date as inclusive, end date as exclusive
                    #   - valid_trading_days ends at yesterday since the market is still open 
                    #   - using today as the end date ensures yesterday’s data is included, while today itself is excluded
                    self.fetch_historical_data([ticker], list_of_valid_trading_days[-1].strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d"), "1d")

            # Today is not a trading day (weekend/holiday)
            else:
                list_of_valid_trading_days = []
                list_of_actual_trading_days = []

                # Get all valid trading days up to today
                # If today is not a trading day, valid_trading_days[-1] gives the most recent trading day before today
                valid_trading_days = nyse.valid_days(start_date=today - pd.Timedelta(days=StockTracker.MAX_LOOKBACK_DAYS), end_date=today)
                most_recent_trading_day = valid_trading_days[-1].date()
                # print(most_recent_trading_day)

                # Append the last N trading days starting from the most recent (working backwards)
                for i in range(days_range):
                    list_of_valid_trading_days.append(valid_trading_days[-1 - i].date())
                    # print(valid_trading_days[-1 - i].date())

                # Collect the last N dates actually present in the CSV for this ticker (most recent first)
                for i in range(days_range):
                    day = pd.to_datetime(ticker_specific_dataframe["Date"].iloc[-1 - i]).date()
                    list_of_actual_trading_days.append(day)

                # Check if the last N valid trading days match exactly the last N dates in the CSV
                if list_of_valid_trading_days == list_of_actual_trading_days:
                    print("Data matches, can use straight away")
                    pass
                else:
                    # Fetch historical data for this ticker because the CSV is missing some dates
                    # Start date:
                    #   - list_of_valid_trading_days[-1] gives the oldest date in our last N valid trading days
                    # End date: most recent trading day (e.g., Friday if today is Sunday) + 1 day
                    #   - +1 ensures the most recent trading day is included because start is inclusive and end is exclusive
                    print("Data needs to be fetched")
                    self.fetch_historical_data([ticker], list_of_valid_trading_days[-1].strftime("%Y-%m-%d"), (most_recent_trading_day + pd.Timedelta(days=1)).strftime("%Y-%m-%d"), "1d")
        else:
            print(f"{ticker} does not exist in the dataframe")
            
            # Today is a trading day and the market has closed for today
            if today in trading_schedule.index.date and eastern_time >= market_close_time:
                # Get all valid trading days up to and including today if it's a trading day
                # NOTE: valid_trading_days only goes back 90 days (adjust if longer lookback is needed)
                valid_trading_days = nyse.valid_days(start_date=today - pd.Timedelta(days=StockTracker.MAX_LOOKBACK_DAYS), end_date=today)
                # Start date: valid_trading_days[-days_range] → the Nth most recent trading day (inclusive)
                # End date: today + 1 day → ensures today’s trading data is included 
                self.fetch_historical_data([ticker], valid_trading_days[-days_range].strftime("%Y-%m-%d"), (today + pd.Timedelta(days=1)).strftime("%Y-%m-%d"), "1d")

            # Today is a trading day and the market is still open or waiting to open
            elif today in trading_schedule.index.date and eastern_time < market_close_time:
                # Get all valid trading days up to yesterday
                # Exclude today because the market is still open; the last valid trading day is yesterday
                valid_trading_days = nyse.valid_days(start_date=today - pd.Timedelta(days=StockTracker.MAX_LOOKBACK_DAYS), end_date=(today - pd.Timedelta(days=1)))
                # Start date: valid_trading_days[-days_range] → the Nth most recent trading day (inclusive)
                # End date: today → excludes today (market still open), but includes yesterday’s data
                self.fetch_historical_data([ticker], valid_trading_days[-days_range].strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d"), "1d")

            # Today is not a trading day (weekend/holiday)
            else:
                # Get all valid trading days up to "today" (if today is not a trading day, this will automatically stop at the most recent valid trading day, e.g. Friday if it's the weekend)
                valid_trading_days = nyse.valid_days(start_date=today - pd.Timedelta(days=StockTracker.MAX_LOOKBACK_DAYS), end_date=today)
                most_recent_trading_day = valid_trading_days[-1].date()
                # Start date: valid_trading_days[-days_range] → the Nth most recent trading day (inclusive)
                # End date = most recent trading day + 1 day (exclusive) → ensures the most recent trading day itself is included
                self.fetch_historical_data([ticker], valid_trading_days[-days_range].strftime("%Y-%m-%d"), (most_recent_trading_day + pd.Timedelta(days=1)).strftime("%Y-%m-%d"), "1d")

        return StockTracker.MASTER_HISTORY[StockTracker.MASTER_HISTORY["Ticker"] == ticker].tail(days_range), valid_trading_days, days_range

    @staticmethod
    def get_start_date(today, lower_bound_date):
        while True:
            try:
                start_date = input(f"\nEnter a start date (inclusive) [YYYY-MM-DD]: ")
                parsed_start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
                if parsed_start_date < lower_bound_date:
                    raise ValueError(f"Start date cannot be eariler than {lower_bound_date}")
                if parsed_start_date > today: 
                    raise ValueError("Start date must not be a future date, Please try again")
            except ValueError as e:
                print(e)
            else:
                return start_date, parsed_start_date

    @staticmethod
    def get_end_date(today, parsed_start_date):
        while True:
            try:
                end_date = input(f"\nEnter an end date (exclusive) [YYYY-MM-DD]: ")
                parsed_end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
                if parsed_end_date <= parsed_start_date:
                    raise ValueError("End date must be after start date, Please try again")
                if parsed_end_date > today + pd.Timedelta(days=1):
                    raise ValueError("End date must not be in a future date, Please try again")
            except ValueError as e:
                print(e)
            else:
                return end_date

    @staticmethod
    def get_interval():
        print(f"\nValid intervals:")
        for key in StockTracker.INTERVAL_TO_TIMEDIFF:
            print(key, end=", ")
        print() # Readability purposes
        while True:
            try:
                interval = input(f"\nEnter an interval: ").strip().lower()
                if interval not in StockTracker.INTERVAL_TO_TIMEDIFF.keys():
                    raise ValueError("Invalid interval entered, Please try again")
            except ValueError as e:
                print(e)
            else:
                return interval

    @staticmethod
    def validated_ticker():
        while True:
            try:
                ticker = input(f"\nEnter a ticker: ").strip().upper()
                ticker_object = yf.Ticker(ticker)
                history = ticker_object.history(period="1d")
                if history.empty:
                    raise ValueError("Invalid ticker symbol, Please try again")
            except ValueError as e:
                print(e)
            except Exception as e:
                # Something else went wrong (network down, API error, etc.)
                print(f"\n⚠️  Unexpected error: {e}")
            else:
                return ticker
        
    @staticmethod  
    def validated_option_yes_or_no():
        while True:
            try:
                add_another_ticker = input(f"Would you like to enter another ticker (Yes/No)? ").strip().capitalize()
                if add_another_ticker != "Yes" and add_another_ticker != "No":
                    raise ValueError(f"Incorrect value entered, Please try again\n")
            except ValueError as e:
                print(e)
            else:
                return add_another_ticker

    @staticmethod
    def validated_look_back_value(min_look_back):
        while True:
            try:
                days_back = int(input(f"Enter how far you would like to go back (measured in days) [Max lookback 180 days]: "))
                if days_back > StockTracker.MAX_LOOKBACK_DAYS or days_back < min_look_back:
                    raise ValueError(f"Invalid lookback period, Please enter a value between {min_look_back} and 180 days\n")
            except ValueError as e:
                print(e)
            else:
                return days_back
        
    @staticmethod
    def validated_email_address():
        while True:
            try:
                recipient_email = input(f"\nEnter your email address: ").strip()

                if recipient_email.count("@") != 1:
                    raise ValueError("Invalid email, Please try again")
                
                if " " in recipient_email:
                    raise ValueError("Invalid email, Please try again")
                
                local, domain = recipient_email.split("@")

                if not local or not domain:
                    raise ValueError("Invalid email, Please try again")
                
                if local[0] == "." or local[-1] == "." or ".." in local:
                    raise ValueError("Invalid email, Please try again")
                
                if domain[0] == ".":
                    raise ValueError("Invalid email, Please try again")
                
                if "." not in domain:
                    raise ValueError("Invalid email, Please try again")
                
                if len(domain.split(".")[-1]) < 2:
                    raise ValueError("Invalid email, Please try again")
                
            except ValueError as e:
                print(e)
            else:
                return recipient_email

if __name__ == "__main__":
    tracker = StockTracker()
    tracker.main_menu()