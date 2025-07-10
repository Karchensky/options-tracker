# runner.py

from options_tracker import YFinanceOptionsTracker
from ticker_list import save_sp1500_tickers
import pandas as pd
from datetime import date
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")

# Step 1: Scrape and save the latest ticker list
save_sp1500_tickers("sp1500_tickers.csv")

# Step 2: Load the list
tickers = pd.read_csv("sp1500_tickers.csv")['Symbol'].dropna().tolist()

# Step 3: Run the options tracker
tracker = YFinanceOptionsTracker(db_path="options_data.db", tickers=tickers)
# tracker = YFinanceOptionsTracker(db_path="options_data.db", tickers=['AAPL', 'MSFT', 'GOOGL','ABBV'])  # Example tickers
# tracker.fetch_and_store()
tracker.send_alert_email(
    snapshot_date=date.today().isoformat(),
    smtp_server='smtp.gmail.com',
    smtp_port=465,
    sender_email=SENDER_EMAIL,
    sender_password=EMAIL_PASSWORD,
    recipient_email=RECIPIENT_EMAIL
)
tracker.close()