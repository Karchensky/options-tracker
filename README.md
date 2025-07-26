# Options Tracker

A comprehensive system for tracking options volume & open interest daily, detecting anomalous behavior, and providing email alerts. Built with Python, PostgreSQL, and Streamlit.

## Features

- **Daily Data Collection**: Automated options data collection from multiple sources
- **Anomaly Detection**: Machine learning-based detection of suspicious options activity
- **Email Alerts**: Automated notifications for detected anomalies
- **Beautiful Dashboard**: Sleek Streamlit interface with interactive visualizations
- **Robust Database**: PostgreSQL with proper indexing, RLS, and migration support
- **Scalable Architecture**: Modular design with proper error handling and logging

## Architecture

```mermaid
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Data Sources  │    │   Core System   │    │   Outputs       │
│                 │    │                 │    │                 │
│ • Polygon.io    │───▶│ • Data Manager  │───▶│ • Email Alerts  │
│ • Alpha Vantage │    │ • Anomaly Det.  │    │ • Dashboard     │
│ • Quandl        │    │ • Database      │    │ • Logs          │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Anomaly Detection Methods

The system detects several types of suspicious options activity:

1. **Volume Anomalies**: Unusual call/put volume compared to historical baselines
2. **Short-Term Options**: High volume in near-expiration options
3. **OTM Options**: Unusual activity in out-of-the-money calls
4. **Open Interest Changes**: Significant changes in options open interest
5. **Composite Scoring**: Machine learning-based insider probability assessment

## Quick Start

### Local Development

1. Install dependencies: `pip install -r requirements.txt --user`
2. Set up Supabase: Create project at [supabase.com](https://supabase.com)
3. Get API keys: [Polygon.io](https://polygon.io) (recommended) or [Alpha Vantage](https://alphavantage.co) (free)
4. Create `.env` file: Copy template below and add your credentials
5. Run migrations: `cd migrations && python -m alembic upgrade head`
6. Test connection: `python -c "from database.connection import db_manager; print(db_manager.test_connection())"`
7. Run system: `python runner.py`

### Automated Deployment

1. Set up GitHub Actions: Add secrets (see `.github/workflows/setup-secrets.md`)
2. Deploy to Streamlit Cloud: Connect repository to [share.streamlit.io](https://share.streamlit.io)
3. Monitor: Check GitHub Actions tab for automated runs

## Installation & Setup

### Prerequisites

- Python 3.10+
- PostgreSQL database (Supabase recommended)
- API keys for data sources (Polygon.io, Alpha Vantage, etc.)

### 1. Clone and Install

```bash
git clone <repository-url>
cd options-tracker

# Install dependencies (use --user flag on Windows if you get permission errors)
pip install -r requirements.txt --user
```

### 2. Environment Configuration

Create a `.env` file in the project root with your configuration:

```env
# Database Configuration (Required)
SUPABASE_DB_URL=postgresql://postgres.[PROJECT_REF]:[PASSWORD]@aws-0-us-east-2.pooler.supabase.com:5432/postgres
SUPABASE_API_KEY=your_supabase_anon_key
SUPABASE_URL=https://your-project.supabase.co

# Email Configuration (Optional - for alerts)
SENDER_EMAIL=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
RECIPIENT_EMAIL=alerts@yourdomain.com
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=465

# Data Source APIs (Required - get at least one)
POLYGON_API_KEY=your_polygon_api_key
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key
QUANDL_API_KEY=your_quandl_key

# Application Settings
MAX_RETRIES=3
REQUEST_TIMEOUT=30
BATCH_SIZE=50
RATE_LIMIT_DELAY=0.1

# Anomaly Detection Thresholds
VOLUME_THRESHOLD=3.0
OI_THRESHOLD=2.5
SHORT_TERM_DAYS=7
OTM_PERCENTAGE=10.0
```

**Required API Keys:**

- **Polygon.io** (Recommended): [Get API Key](https://polygon.io) - Best for options data
- **Alpha Vantage** (Free tier): [Get API Key](https://alphavantage.co) - Good for stock data
- **Quandl** (Free tier): [Get API Key](https://quandl.com) - Historical data backup

**Supabase Setup:**

1. Create a project at [supabase.com](https://supabase.com)
2. Get your database URL from Settings → Database
3. Get your anon key from Settings → API
4. Use the pooler connection string for better reliability

### 3. Database Setup

The project includes pre-configured Alembic migrations. Run these commands to set up your database:

```bash
# Navigate to migrations directory
cd migrations

# Create initial migration (creates all tables)
python -m alembic revision --autogenerate -m "Initial schema"

# Apply migrations to create database tables
python -m alembic upgrade head

# Verify migration status
python -m alembic current

# Return to project root
cd ..
```

### 4. Test Your Setup

Run these commands to verify everything is working:

```bash
# Test database connection
python -c "from database.connection import db_manager; print(db_manager.test_connection())"

# Test data source connection
python -c "from data.data_sources import data_source_manager; print('Data sources ready')"

# Test anomaly detection
python -c "from analysis.anomaly_detector import anomaly_detector; print('Anomaly detector ready')"

# Run a test analysis
python runner.py
```

## Usage

### Manual Run

```bash
# Run analysis for today
python runner.py

# Run analysis for specific date
python runner.py --date 2024-01-15

# Run analysis for specific symbols
python runner.py --symbols AAPL,MSFT,GOOGL
```

### Automated Daily Runs

The system is configured to run automatically via GitHub Actions:

- **Schedule**: Every weekday at 5:45 PM EST (after market close)
- **Manual Trigger**: Available in GitHub Actions tab
- **Monitoring**: Check Actions tab for run status and logs

### Dashboard Access

Launch the Streamlit dashboard:

```bash
streamlit run app/main.py
```

The dashboard provides:

- Real-time options data visualization
- Anomaly detection results
- Historical trend analysis
- Interactive filtering and search

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SUPABASE_DB_URL` | Database connection string | Yes |
| `SUPABASE_API_KEY` | Supabase anon key | Yes |
| `SUPABASE_URL` | Supabase project URL | Yes |
| `POLYGON_API_KEY` | Polygon.io API key | Yes* |
| `ALPHA_VANTAGE_API_KEY` | Alpha Vantage API key | No |
| `QUANDL_API_KEY` | Quandl API key | No |
| `SENDER_EMAIL` | Gmail address for alerts | No |
| `EMAIL_PASSWORD` | Gmail app password | No |
| `RECIPIENT_EMAIL` | Alert recipient email | No |

*At least one data source API key is required

### Anomaly Detection Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `VOLUME_THRESHOLD` | 3.0 | Volume anomaly threshold multiplier |
| `OI_THRESHOLD` | 2.5 | Open interest anomaly threshold |
| `SHORT_TERM_DAYS` | 7 | Days to expiration for short-term options |
| `OTM_PERCENTAGE` | 10.0 | OTM percentage threshold |

## Data Sources

The system supports multiple data sources with automatic fallback:

### Primary Sources

- **Polygon.io**: Best for options data, real-time quotes
- **Alpha Vantage**: Good for stock data, free tier available
- **Yahoo Finance**: Free fallback for basic data
- **Quandl**: Historical data backup

### Data Collection

- **Frequency**: Daily after market close
- **Coverage**: S&P 500 + additional symbols
- **Data Types**: Options chains, volume, open interest, implied volatility
- **Storage**: PostgreSQL with proper indexing

## Anomaly Detection

### Detection Methods

1. **Volume Analysis**: Compares current volume to 30-day historical baseline
2. **Open Interest Changes**: Tracks significant OI changes
3. **Short-Term Options**: Identifies unusual activity in near-expiration options
4. **OTM Options**: Detects unusual out-of-the-money call activity
5. **Machine Learning**: Isolation Forest algorithm for composite scoring

### Alert System

- **Email Notifications**: Automated alerts for detected anomalies
- **Dashboard Alerts**: Real-time display in Streamlit interface
- **Logging**: Comprehensive logging for monitoring and debugging

## Development

### Project Structure

```
options-tracker/
├── app/                    # Streamlit dashboard
├── core/                   # Core business logic
├── data/                   # Data sources and models
├── database/               # Database connection and models
├── analysis/               # Anomaly detection algorithms
├── utils/                  # Utilities and helpers
├── migrations/             # Database migrations
├── .github/workflows/      # GitHub Actions
└── requirements.txt        # Python dependencies
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

### Testing

```bash
# Run all tests
python -m pytest

# Test specific module
python -m pytest tests/test_anomaly_detector.py

# Run with coverage
python -m pytest --cov=.
```

## Troubleshooting

### Common Issues

**Database Connection Failed:**
- Verify Supabase credentials in `.env`
- Check network connectivity
- Ensure database is active

**API Rate Limits:**
- The system includes built-in rate limiting
- Check API key validity
- Consider upgrading API plan if needed

**Email Notifications Not Working:**
- Verify Gmail app password (not regular password)
- Check SMTP settings
- Ensure recipient email is correct

### Logs

Check the following log files for debugging:

- `options_tracker.log`: Main application logs
- GitHub Actions logs: Available in Actions tab
- Streamlit logs: Displayed in terminal when running dashboard

## Support

For questions or issues:

- Check the troubleshooting section above
- Review the documentation
- Ensure all API keys and database credentials are properly configured

## Data Sources

This system integrates with multiple data providers to ensure comprehensive coverage:

- **Polygon.io**: Primary options data source with real-time quotes
- **Alpha Vantage**: Stock data and backup options data
- **Yahoo Finance**: Free fallback for basic market data
- **Quandl**: Historical data and market information
- **Supabase**: Database hosting and management
- **Streamlit**: Dashboard framework and deployment
