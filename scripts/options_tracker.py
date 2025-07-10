import yfinance as yf
import sqlite3
import time
from datetime import date, timedelta
import smtplib
from email.message import EmailMessage

class YFinanceOptionsTracker:
    def __init__(self, db_path="options_data.db", tickers=None):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self._create_tables()
        self.tickers = tickers or []

    def _create_tables(self):
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS OPTION_DATA (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            SYMBOL TEXT,
            EXPIRATION TEXT,
            CONTRACT_SYMBOL TEXT,
            STRIKE REAL,
            LAST_PRICE REAL,
            BID REAL,
            ASK REAL,
            VOLUME INTEGER,
            OPEN_INTEREST INTEGER,
            IMPLIED_VOLATILITY REAL,
            SIDE TEXT,
            SNAPSHOT_DATE DATE,
            UNIQUE (CONTRACT_SYMBOL, SNAPSHOT_DATE)
        );
        """)

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS STOCK_PRICE_SNAPSHOT (
            SYMBOL TEXT,
            SNAPSHOT_DATE DATE,
            CLOSE_PRICE REAL,
            PRIMARY KEY (SYMBOL, SNAPSHOT_DATE)
        );
        """)

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS OPTION_ANOMALIES (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            SYMBOL TEXT,
            SNAPSHOT_DATE DATE,
            OV_CALL_VOL INTEGER,
            OV_CALL_BASELINE REAL,
            OV_CALL_RATIO REAL,
            OV_TRIGGER_IND INTEGER,
            OV_PUT_VOL INTEGER,
            OV_PUT_BASELINE REAL,
            OV_PUT_RATIO REAL,
            OV_PUT_TRIGGER_IND INTEGER,
            SHORT_CALL_VOL INTEGER,
            SHORT_CALL_BASELINE REAL,
            SHORT_CALL_RATIO REAL,
            SHORT_CALL_TRIGGER_IND INTEGER,
            OTM_CALL_VOL INTEGER,
            OTM_CALL_BASELINE REAL,
            OTM_CALL_RATIO REAL,
            OTM_CALL_TRIGGER_IND INTEGER,
            OI_CALL_DELTA INTEGER,
            OI_CALL_BASELINE REAL,
            OI_CALL_RATIO REAL,
            OI_CALL_TRIGGER_IND INTEGER,
            UNIQUE (SYMBOL, SNAPSHOT_DATE)
        );
        """)
        self.conn.commit()

    def fetch_and_store(self):
        today = date.today().isoformat()
        for symbol in self.tickers:
            try:
                tk = yf.Ticker(symbol)
                hist = tk.history(period='1d')
                if hist.empty:
                    continue
                close_price = hist['Close'].iloc[-1]

                self.cursor.execute("""
                    INSERT OR REPLACE INTO STOCK_PRICE_SNAPSHOT (SYMBOL, SNAPSHOT_DATE, CLOSE_PRICE)
                    VALUES (?, ?, ?)
                """, (symbol, today, close_price))

                for exp in tk.options:
                    try:
                        oc = tk.option_chain(exp)
                        for side, df in [('CALL', oc.calls), ('PUT', oc.puts)]:
                            for _, r in df.iterrows():
                                self.cursor.execute("""
                                INSERT OR IGNORE INTO OPTION_DATA
                                (SYMBOL, EXPIRATION, CONTRACT_SYMBOL, STRIKE, LAST_PRICE,
                                 BID, ASK, VOLUME, OPEN_INTEREST, IMPLIED_VOLATILITY,
                                 SIDE, SNAPSHOT_DATE)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """, (
                                    symbol, exp, r.contractSymbol, r.strike,
                                    r.lastPrice, r.bid, r.ask, r.volume,
                                    r.openInterest, r.impliedVolatility,
                                    side, today
                                ))
                        self.conn.commit()
                    except Exception as e:
                        print(f"{symbol} @ {exp} failed: {e}")
                    time.sleep(0.5)
            except Exception as e:
                print(f"Failed to fetch data for {symbol}: {e}")

        print("Data fetch complete for", today)
        self.detect_anomalies(today)

    def detect_anomalies(self, today):
        two_weeks_ago = (date.fromisoformat(today) - timedelta(days=14)).isoformat()
        for symbol in self.tickers:
            try:
                self.cursor.execute("SELECT CLOSE_PRICE FROM STOCK_PRICE_SNAPSHOT WHERE SYMBOL = ? AND SNAPSHOT_DATE = ?", (symbol, today))
                row = self.cursor.fetchone()
                if not row:
                    continue
                close_price = row[0]

                def get_avg_volume(side, filter_clause=""):
                    q = f"""
                        SELECT SUM(VOLUME) / COUNT(DISTINCT SNAPSHOT_DATE) FROM OPTION_DATA
                        WHERE SYMBOL = ? AND SIDE = ? AND SNAPSHOT_DATE BETWEEN ? AND ? {filter_clause}
                    """
                    self.cursor.execute(q, (symbol, side, two_weeks_ago, today))
                    return self.cursor.fetchone()[0] or 0

                def get_today_volume(side, filter_clause=""):
                    q = f"""
                        SELECT SUM(VOLUME) FROM OPTION_DATA
                        WHERE SYMBOL = ? AND SIDE = ? AND SNAPSHOT_DATE = ? {filter_clause}
                    """
                    self.cursor.execute(q, (symbol, side, today))
                    return self.cursor.fetchone()[0] or 0

                ov_call_base = get_avg_volume('CALL')
                ov_call_today = get_today_volume('CALL')
                ov_call_ratio = ov_call_today / ov_call_base if ov_call_base > 0 else 0
                ov_call_flag = int(ov_call_ratio >= 5)

                ov_put_base = get_avg_volume('PUT')
                ov_put_today = get_today_volume('PUT')
                ov_put_ratio = ov_put_today / ov_put_base if ov_put_base > 0 else 0
                ov_put_flag = int(ov_put_ratio >= 5)

                short_filter = "AND julianday(EXPIRATION) - julianday(SNAPSHOT_DATE) < 7"
                short_call_base = get_avg_volume('CALL', short_filter)
                short_call_today = get_today_volume('CALL', short_filter)
                short_call_ratio = short_call_today / short_call_base if short_call_base > 0 else 0
                short_call_flag = int(short_call_ratio >= 5)

                otm_filter = f"AND STRIKE > {close_price * 1.1}"
                otm_call_base = get_avg_volume('CALL', otm_filter)
                otm_call_today = get_today_volume('CALL', otm_filter)
                otm_call_ratio = otm_call_today / otm_call_base if otm_call_base > 0 else 0
                otm_call_flag = int(otm_call_ratio >= 5)

                self.cursor.execute("""
                    SELECT SUM(OPEN_INTEREST) FROM OPTION_DATA
                    WHERE SYMBOL = ? AND SIDE = 'CALL' AND SNAPSHOT_DATE = ?
                """, (symbol, today))
                oi_today = self.cursor.fetchone()[0] or 0

                yesterday = (date.fromisoformat(today) - timedelta(days=1)).isoformat()
                self.cursor.execute("""
                    SELECT SUM(OPEN_INTEREST) FROM OPTION_DATA
                    WHERE SYMBOL = ? AND SIDE = 'CALL' AND SNAPSHOT_DATE = ?
                """, (symbol, yesterday))
                oi_yesterday = self.cursor.fetchone()[0] or 0

                oi_delta = oi_today - oi_yesterday
                oi_base = oi_yesterday if oi_yesterday > 0 else 1
                oi_ratio = oi_today / oi_base if oi_base > 1 else 1
                oi_flag = int(oi_ratio >= 2)

                self.cursor.execute("""
                    INSERT OR IGNORE INTO OPTION_ANOMALIES
                    (SYMBOL, SNAPSHOT_DATE,
                     OV_CALL_VOL, OV_CALL_BASELINE, OV_CALL_RATIO, OV_TRIGGER_IND,
                     OV_PUT_VOL, OV_PUT_BASELINE, OV_PUT_RATIO, OV_PUT_TRIGGER_IND,
                     SHORT_CALL_VOL, SHORT_CALL_BASELINE, SHORT_CALL_RATIO, SHORT_CALL_TRIGGER_IND,
                     OTM_CALL_VOL, OTM_CALL_BASELINE, OTM_CALL_RATIO, OTM_CALL_TRIGGER_IND,
                     OI_CALL_DELTA, OI_CALL_BASELINE, OI_CALL_RATIO, OI_CALL_TRIGGER_IND)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    symbol, today,
                    ov_call_today, ov_call_base, ov_call_ratio, ov_call_flag,
                    ov_put_today, ov_put_base, ov_put_ratio, ov_put_flag,
                    short_call_today, short_call_base, short_call_ratio, short_call_flag,
                    otm_call_today, otm_call_base, otm_call_ratio, otm_call_flag,
                    oi_delta, oi_base, oi_ratio, oi_flag
                ))
                self.conn.commit()
            except Exception as e:
                print(f"Anomaly check failed for {symbol}: {e}")

    def send_alert_email(self, snapshot_date, smtp_server, smtp_port, sender_email, sender_password, recipient_email):
        # Fetch all tickers with any trigger == 1
        query = f'''
            SELECT SYMBOL, 
                OV_CALL_VOL, OV_CALL_BASELINE, OV_CALL_RATIO, OV_TRIGGER_IND,
                OV_PUT_VOL, OV_PUT_BASELINE, OV_PUT_RATIO, OV_PUT_TRIGGER_IND,
                SHORT_CALL_VOL, SHORT_CALL_BASELINE, SHORT_CALL_RATIO, SHORT_CALL_TRIGGER_IND,
                OTM_CALL_VOL, OTM_CALL_BASELINE, OTM_CALL_RATIO, OTM_CALL_TRIGGER_IND,
                OI_CALL_DELTA, OI_CALL_BASELINE, OI_CALL_RATIO, OI_CALL_TRIGGER_IND
            FROM OPTION_ANOMALIES
            WHERE SNAPSHOT_DATE = ?
            AND (OV_TRIGGER_IND = 1 OR OV_PUT_TRIGGER_IND = 1 OR SHORT_CALL_TRIGGER_IND = 1 OR OTM_CALL_TRIGGER_IND = 1 OR OI_CALL_TRIGGER_IND = 1)
        '''
        self.cursor.execute(query, (snapshot_date,))
        rows = self.cursor.fetchall()

        if not rows:
            print("No anomalies triggered today.")
            msg = EmailMessage()
            msg['Subject'] = f"No Anomalies Detected for {snapshot_date}"
            try:
                with smtplib.SMTP_SSL(smtp_server, smtp_port) as smtp:
                    smtp.login(sender_email, sender_password)
                    smtp.send_message(msg)
                print(f"Alert email sent to {recipient_email}")
            except Exception as e:
                print(f"Failed to send email: {e}")
            return

        # Format email
        msg = EmailMessage()
        msg['Subject'] = f"Options Anomaly Alerts for {snapshot_date}"
        msg['From'] = sender_email
        msg['To'] = recipient_email

        body = f"Anomalies detected for {len(rows)} ticker(s):\n\n"
        for row in rows:
            sym = row[0]
            body += f"\n🔹 {sym}\n"
            body += f"  OV_CALL_VOL: {row[1]} (x{row[3]:.1f}) {'✅' if row[4] else ''}\n"
            body += f"  OV_PUT_VOL:  {row[5]} (x{row[7]:.1f}) {'✅' if row[8] else ''}\n"
            body += f"  SHORT_CALL_VOL: {row[9]} (x{row[11]:.1f}) {'✅' if row[12] else ''}\n"
            body += f"  OTM_CALL_VOL:   {row[13]} (x{row[15]:.1f}) {'✅' if row[16] else ''}\n"
            body += f"  OI_CALL_DELTA:  {row[17]} (x{row[19]:.1f}) {'✅' if row[20] else ''}\n"

        msg.set_content(body)

        try:
            with smtplib.SMTP_SSL(smtp_server, smtp_port) as smtp:
                smtp.login(sender_email, sender_password)
                smtp.send_message(msg)
            print(f"Alert email sent to {recipient_email}")
        except Exception as e:
            print(f"Failed to send email: {e}")

    def close(self):
        self.conn.close()