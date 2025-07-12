from sqlalchemy import create_engine, NullPool
from config import SUPABASE_DB_URL

engine = create_engine(
    SUPABASE_DB_URL,
    pool_pre_ping=True,  # Detect broken connections and reconnect automatically
    poolclass=NullPool   # Avoid maintaining persistent connections
)

with engine.connect() as conn:
    print("Connection to Supabase PostgreSQL successful.")