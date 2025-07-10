# runner.py

from options_tracker import YFinanceOptionsTracker
from ticker_list import save_sp1500_tickers
import pandas as pd
from datetime import date

# Step 1: Scrape and save the latest ticker list
save_sp1500_tickers("sp1500_tickers.csv")

# Step 2: Load the list
tickers = pd.read_csv("sp1500_tickers.csv")['Symbol'].dropna().tolist()

# Step 3: Run the options tracker
# tracker = YFinanceOptionsTracker(db_path="options_data.db", tickers=tickers)
tracker = YFinanceOptionsTracker(db_path="options_data.db", tickers=['AAPL', 'MSFT', 'GOOGL'])  # Example tickers
tracker.fetch_and_store()
# tracker.send_alert_email(
#     snapshot_date=date.today().isoformat(),
#     smtp_server='smtp.gmail.com',
#     smtp_port=465,
#     sender_email='bryankarchensky@gmail.com',
#     sender_password='nfec qdoy qpui oqan',
#     recipient_email='bryankarchensky@gmail.com'
# )
tracker.close()