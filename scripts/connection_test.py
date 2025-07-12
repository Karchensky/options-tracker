import os
from sqlalchemy import create_engine, NullPool
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection details
DB_URL = os.getenv("SUPABASE_DB_URL")  # This is now fully ready-to-go

engine = create_engine(
    DB_URL,
    pool_pre_ping=True,  # Detect broken connections and reconnect automatically
    poolclass=NullPool   # Avoid maintaining persistent connections
)

with engine.connect() as conn:
    print("Connection to Supabase PostgreSQL successful.")