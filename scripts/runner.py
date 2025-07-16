# runner.py

from options_tracker import SupabaseOptionTracker
from ticker_list import save_sp1500_tickers
import pandas as pd
from datetime import datetime
import pytz
from config import EMAIL_PASSWORD, SENDER_EMAIL, RECIPIENT_EMAIL, SUPABASE_DB_URL

# Step 1: Scrape and save the latest ticker list
save_sp1500_tickers("sp1500_tickers.csv")

# Step 2: Load the list
tickers = pd.read_csv("sp1500_tickers.csv")['Symbol'].dropna().tolist()

# Step 3: Check for US market holidays
holidays_df = pd.read_csv("us_market_holidays.csv")
holiday_dates = set(pd.to_datetime(holidays_df['date']).dt.date)

# Step 3a: Get today's date in US/Eastern
today = datetime.now(pytz.timezone("US/Eastern")).date()

# Step 4: Run the Supabase-powered options tracker. Skip weekends and holidays
if today.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
    print(f"Today ({today}) is a weekend. Skipping today's run as markets are closed.")
elif today in holiday_dates:
    print(f"Today ({today}) is a US market holiday. Skipping today's run as markets are closed.")
else:
    # tracker = SupabaseOptionTracker(SUPABASE_DB_URL, tickers=['AAPL', 'MSFT'])  # Example tickers
    tracker = SupabaseOptionTracker(SUPABASE_DB_URL, tickers=tickers)
    tracker.fetch_and_store()
    tracker.send_alert_email(
        snapshot_date=today,
        smtp_server='smtp.gmail.com',
        smtp_port=465,
        sender_email=SENDER_EMAIL,
        sender_password=EMAIL_PASSWORD,
        recipient_email=RECIPIENT_EMAIL
    )