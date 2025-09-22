import json
from main import percentage_change_alert

data = None

with open("alert_config.json", "r") as f:
    data = json.load(f)

list_of_tickers = data["tickers"]
threshold_value = data["threshold"]
recipient_email = data["recipient_email"]

percentage_change_alert(list_of_tickers, threshold_value, recipient_email, verbose=False)
