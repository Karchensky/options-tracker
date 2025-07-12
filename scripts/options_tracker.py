import yfinance as yf
import time
from datetime import date, timedelta
import smtplib
from email.message import EmailMessage
import traceback
import numpy as np
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, UniqueConstraint, NullPool, event, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base, Mapper
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import insert as pg_insert

Base = declarative_base()

class OptionData(Base):
    __tablename__ = "option_data"
    id = Column(Integer, primary_key=True)
    symbol = Column(String)
    expiration = Column(Date)
    contract_symbol = Column(String)
    strike = Column(Float)
    last_price = Column(Float)
    bid = Column(Float)
    ask = Column(Float)
    volume = Column(Integer)
    open_interest = Column(Integer)
    implied_volatility = Column(Float)
    side = Column(String)
    snapshot_date = Column(Date)
    insert_timestamp = Column(DateTime, server_default=func.now(), nullable=False)
    update_timestamp = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    __table_args__ = (UniqueConstraint('contract_symbol', 'snapshot_date'),)

class StockPriceSnapshot(Base):
    __tablename__ = "stock_price_snapshot"
    symbol = Column(String, primary_key=True)
    snapshot_date = Column(Date, primary_key=True)
    close_price = Column(Float)
    insert_timestamp = Column(DateTime, server_default=func.now(), nullable=False)
    update_timestamp = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

class OptionAnomaly(Base):
    __tablename__ = "option_anomalies"
    id = Column(Integer, primary_key=True)
    symbol = Column(String)
    snapshot_date = Column(Date)
    ov_call_vol = Column(Integer)
    ov_call_baseline = Column(Float)
    ov_call_ratio = Column(Float)
    ov_trigger_ind = Column(Integer)
    ov_put_vol = Column(Integer)
    ov_put_baseline = Column(Float)
    ov_put_ratio = Column(Float)
    ov_put_trigger_ind = Column(Integer)
    short_call_vol = Column(Integer)
    short_call_baseline = Column(Float)
    short_call_ratio = Column(Float)
    short_call_trigger_ind = Column(Integer)
    otm_call_vol = Column(Integer)
    otm_call_baseline = Column(Float)
    otm_call_ratio = Column(Float)
    otm_call_trigger_ind = Column(Integer)
    oi_call_delta = Column(Integer)
    oi_call_baseline = Column(Float)
    oi_call_ratio = Column(Float)
    oi_call_trigger_ind = Column(Integer)
    insert_timestamp = Column(DateTime, server_default=func.now(), nullable=False)
    update_timestamp = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    __table_args__ = (UniqueConstraint('symbol', 'snapshot_date'),)

# Convert NumPy float and int types to native Python types before insert/update
@event.listens_for(Mapper, "before_insert")
@event.listens_for(Mapper, "before_update")
def convert_numpy_types(mapper, connection, target):
    for key, value in vars(target).items():
        if isinstance(value, np.generic):
            setattr(target, key, value.item())

class SupabaseOptionTracker:
    def __init__(self, database, tickers):
        self.engine = create_engine(
            database,
            pool_pre_ping=True,  # Detect broken connections and reconnect automatically
            poolclass=NullPool   # Avoid maintaining persistent connections
        )
        self.Session = sessionmaker(bind=self.engine)
        self.tickers = tickers or []
        Base.metadata.create_all(self.engine)

    def upsert(self, session, model, insert_values, conflict_cols, update_cols):
        # Convert all np.generic types to native Python types
        clean_values = {
            k: (v.item() if isinstance(v, np.generic) else v)
            for k, v in insert_values.items()
        }

        stmt = pg_insert(model).values(**clean_values)
        update_dict = {col: stmt.excluded[col] for col in update_cols}
        update_dict["update_timestamp"] = func.now()
        stmt = stmt.on_conflict_do_update(
            index_elements=conflict_cols,
            set_=update_dict
        )
        session.execute(stmt)

    def fetch_and_store(self):
        today = date.today()
        session = self.Session()
        for symbol in self.tickers:
            try:
                tk = yf.Ticker(symbol)
                hist = tk.history(period='1d')
                if hist.empty:
                    continue
                close_price = hist['Close'].iloc[-1]

                self.upsert(
                    session,
                    StockPriceSnapshot,
                    {
                        "symbol": symbol,
                        "snapshot_date": today,
                        "close_price": close_price
                    },
                    conflict_cols=["symbol", "snapshot_date"],
                    update_cols=["close_price"]
                )

                for exp in tk.options:
                    try:
                        oc = tk.option_chain(exp)
                        for side, df in [('CALL', oc.calls), ('PUT', oc.puts)]:
                            for _, r in df.iterrows():
                                self.upsert(
                                    session,
                                    OptionData,
                                    {
                                        "symbol": symbol,
                                        "expiration": exp,
                                        "contract_symbol": r.contractSymbol,
                                        "strike": float(r.strike) if not np.isnan(r.strike) else None,
                                        "last_price": float(r.lastPrice) if not np.isnan(r.lastPrice) else None,
                                        "bid": float(r.bid) if not np.isnan(r.bid) else None,
                                        "ask": float(r.ask) if not np.isnan(r.ask) else None,
                                        "volume": int(r.volume) if not np.isnan(r.volume) else 0,
                                        "open_interest": int(r.openInterest) if not np.isnan(r.openInterest) else 0,
                                        "implied_volatility": float(r.impliedVolatility) if not np.isnan(r.impliedVolatility) else None,
                                        "side": side,
                                        "snapshot_date": today,
                                    },
                                    conflict_cols=["contract_symbol", "snapshot_date"],
                                    update_cols=[
                                        "symbol", "expiration", "strike", "last_price", "bid", "ask",
                                        "volume", "open_interest", "implied_volatility", "side"
                                    ]
                                )
                    except Exception as e:
                        print(f"{symbol} @ {exp} failed: {e}")
                    time.sleep(0.5)
                print(f"Fetched {symbol} successfully")
            except Exception as e:
                print(f"Failed to fetch data for {symbol}: {e}")
        session.commit()
        session.close()
        print("Data fetch complete for", today)
        self.detect_anomalies(today)

    def detect_anomalies(self, today):
        session = self.Session()
        two_weeks_ago = today - timedelta(days=14)
        for symbol in self.tickers:
            try:
                row = session.query(StockPriceSnapshot).filter_by(symbol=symbol, snapshot_date=today).first()
                if not row:
                    continue
                close_price = row.close_price

                def get_avg_volume(side, filter_clause=None):
                    q = session.query(OptionData).filter(
                        OptionData.symbol == symbol,
                        OptionData.side == side,
                        OptionData.snapshot_date.between(two_weeks_ago, today)
                    )
                    if filter_clause is not None:
                        q = q.filter(filter_clause)
                    results = q.all()
                    return (sum(r.volume for r in results if r.volume) / len(set(r.snapshot_date for r in results))) if results else 0

                def get_today_volume(side, filter_clause=None):
                    q = session.query(OptionData).filter(
                        OptionData.symbol == symbol,
                        OptionData.side == side,
                        OptionData.snapshot_date == today
                    )
                    if filter_clause is not None:
                        q = q.filter(filter_clause)
                    return sum(r.volume for r in q.all() if r.volume)

                from sqlalchemy import and_, cast, Date
                short_filter = OptionData.expiration <= today + timedelta(days=7)
                otm_filter = OptionData.strike > close_price * 1.1

                ov_call_base = get_avg_volume('CALL')
                ov_call_today = get_today_volume('CALL')
                ov_call_ratio = ov_call_today / ov_call_base if ov_call_base > 0 else 0
                ov_call_flag = int(ov_call_ratio >= 5)

                ov_put_base = get_avg_volume('PUT')
                ov_put_today = get_today_volume('PUT')
                ov_put_ratio = ov_put_today / ov_put_base if ov_put_base > 0 else 0
                ov_put_flag = int(ov_put_ratio >= 5)

                short_call_base = get_avg_volume('CALL', short_filter)
                short_call_today = get_today_volume('CALL', short_filter)
                short_call_ratio = short_call_today / short_call_base if short_call_base > 0 else 0
                short_call_flag = int(short_call_ratio >= 5)

                otm_call_base = get_avg_volume('CALL', otm_filter)
                otm_call_today = get_today_volume('CALL', otm_filter)
                otm_call_ratio = otm_call_today / otm_call_base if otm_call_base > 0 else 0
                otm_call_flag = int(otm_call_ratio >= 5)

                oi_today = sum(r.open_interest for r in session.query(OptionData).filter_by(symbol=symbol, side='CALL', snapshot_date=today).all())
                yesterday = today - timedelta(days=1)
                oi_yesterday = sum(r.open_interest for r in session.query(OptionData).filter_by(symbol=symbol, side='CALL', snapshot_date=yesterday).all())
                oi_delta = oi_today - oi_yesterday
                oi_base = oi_yesterday if oi_yesterday > 0 else 1
                oi_ratio = oi_today / oi_base if oi_base > 1 else 1
                oi_flag = int(oi_ratio >= 2)

                self.upsert(
                    session,
                    OptionAnomaly,
                    {
                        "symbol": symbol,
                        "snapshot_date": today,
                        "ov_call_vol": ov_call_today,
                        "ov_call_baseline": ov_call_base,
                        "ov_call_ratio": ov_call_ratio,
                        "ov_trigger_ind": ov_call_flag,
                        "ov_put_vol": ov_put_today,
                        "ov_put_baseline": ov_put_base,
                        "ov_put_ratio": ov_put_ratio,
                        "ov_put_trigger_ind": ov_put_flag,
                        "short_call_vol": short_call_today,
                        "short_call_baseline": short_call_base,
                        "short_call_ratio": short_call_ratio,
                        "short_call_trigger_ind": short_call_flag,
                        "otm_call_vol": otm_call_today,
                        "otm_call_baseline": otm_call_base,
                        "otm_call_ratio": otm_call_ratio,
                        "otm_call_trigger_ind": otm_call_flag,
                        "oi_call_delta": oi_delta,
                        "oi_call_baseline": oi_base,
                        "oi_call_ratio": oi_ratio,
                        "oi_call_trigger_ind": oi_flag
                    },
                    conflict_cols=["symbol", "snapshot_date"],
                    update_cols=[
                        "ov_call_vol", "ov_call_baseline", "ov_call_ratio", "ov_trigger_ind",
                        "ov_put_vol", "ov_put_baseline", "ov_put_ratio", "ov_put_trigger_ind",
                        "short_call_vol", "short_call_baseline", "short_call_ratio", "short_call_trigger_ind",
                        "otm_call_vol", "otm_call_baseline", "otm_call_ratio", "otm_call_trigger_ind",
                        "oi_call_delta", "oi_call_baseline", "oi_call_ratio", "oi_call_trigger_ind"
                    ]
                )

                session.commit()
                
            except Exception as e:
                print(f"Anomaly check failed for {symbol}: {e}")
        session.close()

    def send_alert_email(self, snapshot_date, smtp_server, smtp_port, sender_email, sender_password, recipient_email):
        session = self.Session()
        anomalies = session.query(OptionAnomaly).filter(
            OptionAnomaly.snapshot_date == snapshot_date,
            (OptionAnomaly.ov_trigger_ind == 1) |
            (OptionAnomaly.ov_put_trigger_ind == 1) |
            (OptionAnomaly.short_call_trigger_ind == 1) |
            (OptionAnomaly.otm_call_trigger_ind == 1) |
            (OptionAnomaly.oi_call_trigger_ind == 1)
        ).all()

        msg = EmailMessage()
        msg['From'] = sender_email
        msg['To'] = recipient_email

        if not anomalies:
            print("No anomalies triggered today.")
            msg['Subject'] = f"No Anomalies Detected for {snapshot_date}"
            msg.set_content(f"No unusual options activity was detected for {snapshot_date}.")
        else:
            msg['Subject'] = f"Options Anomaly Alerts for {snapshot_date}"
            body = f"Anomalies detected for {len(anomalies)} ticker(s):\n\n"
            for row in anomalies:
                body += f"\n🔹 {row.symbol}\n"
                body += f"  OV_CALL_VOL: {row.ov_call_vol} (x{row.ov_call_ratio:.1f}) {'✅' if row.ov_trigger_ind else ''}\n"
                body += f"  OV_PUT_VOL:  {row.ov_put_vol} (x{row.ov_put_ratio:.1f}) {'✅' if row.ov_put_trigger_ind else ''}\n"
                body += f"  SHORT_CALL_VOL: {row.short_call_vol} (x{row.short_call_ratio:.1f}) {'✅' if row.short_call_trigger_ind else ''}\n"
                body += f"  OTM_CALL_VOL:   {row.otm_call_vol} (x{row.otm_call_ratio:.1f}) {'✅' if row.otm_call_trigger_ind else ''}\n"
                body += f"  OI_CALL_DELTA:  {row.oi_call_delta} (x{row.oi_call_ratio:.1f}) {'✅' if row.oi_call_trigger_ind else ''}\n"
            msg.set_content(body)

        try:
            with smtplib.SMTP_SSL(smtp_server, smtp_port) as smtp:
                smtp.login(sender_email, sender_password)
                smtp.send_message(msg)
            print(f"Alert email sent to {recipient_email}")
        except Exception as e:
            print("Failed to send email:")
            traceback.print_exc()