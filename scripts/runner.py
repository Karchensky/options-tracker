# runner.py

from options_tracker import SupabaseOptionTracker
from ticker_list import save_sp1500_tickers
import pandas as pd
from datetime import date
from config import EMAIL_PASSWORD, SENDER_EMAIL, RECIPIENT_EMAIL, SUPABASE_DB_URL

# Step 1: Scrape and save the latest ticker list
save_sp1500_tickers("sp1500_tickers.csv")

# Step 2: Load the list
tickers = pd.read_csv("sp1500_tickers.csv")['Symbol'].dropna().tolist()

# Step 3: Run the Supabase-powered options tracker
# tracker = SupabaseOptionTracker(SUPABASE_DB_URL, tickers=tickers)
tracker = SupabaseOptionTracker(SUPABASE_DB_URL, tickers=['AAPL', 'MSFT'])  # Example tickers
tracker.fetch_and_store()
tracker.send_alert_email(
    snapshot_date=date.today(),
    smtp_server='smtp.gmail.com',
    smtp_port=465,
    sender_email=SENDER_EMAIL,
    sender_password=EMAIL_PASSWORD,
    recipient_email=RECIPIENT_EMAIL
)