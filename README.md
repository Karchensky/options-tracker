# Options Tracker - Insider Trading Detection System

A sophisticated options trading anomaly detection system designed to identify potential insider trading activity by monitoring unusual options volume, open interest patterns, and other suspicious trading behaviors.

## Overview

This system tracks daily options activity across thousands of stocks and identifies anomalous patterns that might indicate insider trading. It uses multiple data sources, advanced anomaly detection algorithms, and provides real-time alerts via email and a comprehensive web dashboard.

## Key Features

- **Multi-Source Data Collection**: Supports Polygon.io, Alpha Vantage, and other data providers with automatic fallback
- **Comprehensive Stock Coverage**: Tracks S&P 500, S&P 400, S&P 600, NASDAQ, and NYSE stocks
- **Advanced Anomaly Detection**: Machine learning-based detection of unusual options activity
- **Real-Time Alerts**: Email notifications for detected anomalies with risk scoring
- **Beautiful Dashboard**: Sleek Streamlit interface with interactive visualizations
- **Robust Database**: PostgreSQL with proper indexing, RLS, and migration support
- **Scalable Architecture**: Modular design with proper error handling and logging

## Architecture

```
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

**Note**: The migrations directory is already configured. If you get errors about missing files, ensure you're in the `migrations` directory when running Alembic commands.

### 4. Test Configuration

```bash
# Test database connection
python -c "from database.connection import db_manager; print(db_manager.test_connection())"

# Test email configuration (optional)
python -c "from utils.notifications import NotificationManager; nm = NotificationManager(); print(nm.send_test_email())"
```

### 5. Troubleshooting

**Common Installation Issues:**

**Package Installation Errors:**
```bash
# If you get permission errors on Windows:
pip install -r requirements.txt --user

# If smtplib2 error occurs:
# Remove smtplib2 from requirements.txt (it's part of Python standard library)
```

**Database Connection Issues:**
- Verify your `.env` file has correct Supabase credentials
- Use pooler connection string: `postgresql://postgres.[PROJECT_REF]:[PASSWORD]@aws-0-us-east-2.pooler.supabase.com:5432/postgres`
- Check Supabase Dashboard → Settings → Database → Connection Pooling for IP restrictions

**Migration Issues:**
```bash
# If migrations fail, ensure you're in the migrations directory:
cd migrations
python -m alembic current
python -m alembic upgrade head
```

**API Key Issues:**
- Start with Alpha Vantage (free tier) for testing
- Polygon.io requires paid plan for options data
- Ensure API keys are correctly formatted in `.env` file

## Usage

### Daily Analysis

Run the daily options analysis:

```bash
python runner.py
```

This will:
1. Update the comprehensive ticker list
2. Fetch options data from all configured sources
3. Detect anomalies using multiple algorithms
4. Send email alerts for suspicious activity
5. Store results in the database

### Web Dashboard

**Local Development:**
```bash
streamlit run app/main.py
```

**Cloud Deployment:**
- **URL**: https://bk-options-tracker.streamlit.app/
- **Auto-updates**: Connected to your database
- **Real-time data**: Shows latest analysis results

The dashboard provides:
- Real-time anomaly overview
- Detailed analysis by symbol
- Interactive visualizations
- Historical trend analysis
- Risk scoring and probability assessment

### Manual Ticker List Update

```bash
python -c "from data.ticker_manager import ticker_manager; ticker_manager.get_comprehensive_ticker_list()"
```

## Data Sources

### Recommended: Polygon.io
- **Pros**: Reliable options data, good API limits, comprehensive coverage
- **Cons**: Paid service (free tier available)
- **Setup**: Get API key from [polygon.io](https://polygon.io)

### Alternative: Alpha Vantage
- **Pros**: Free tier available, good stock data
- **Cons**: Limited options data, rate limits
- **Setup**: Get API key from [alphavantage.co](https://alphavantage.co)

### Backup: Quandl
- **Pros**: Free tier, good historical data
- **Cons**: Limited real-time data
- **Setup**: Get API key from [quandl.com](https://quandl.com)

## Configuration

### Anomaly Detection Settings

Adjust detection sensitivity in your `.env` file:

```env
# Volume threshold (3.0 = 3x normal volume)
VOLUME_THRESHOLD=3.0

# Open Interest threshold (2.5 = 2.5x normal OI change)
OI_THRESHOLD=2.5

# Short-term options (days to expiration)
SHORT_TERM_DAYS=7

# OTM percentage (10% above current price)
OTM_PERCENTAGE=10.0
```

### Rate Limiting

Control API request rates:

```env
# Delay between requests (seconds)
RATE_LIMIT_DELAY=0.1

# Batch size for processing
BATCH_SIZE=50

# Maximum retries for failed requests
MAX_RETRIES=3
```

## Database Schema

The system uses a normalized database schema with the following main tables:

- **stocks**: Stock information and metadata
- **stock_price_snapshots**: Daily stock price data
- **option_data**: Options chain data with Greeks
- **option_anomalies**: Anomaly detection results
- **data_source_logs**: System operation logs
- **alert_logs**: Notification delivery logs

**Database Setup:**
The migration system automatically creates all tables with proper indexes and relationships. No manual database setup required.

## Monitoring & Logging

### Log Files

- `options_tracker.log`: Main application logs
- Database logs: Stored in `data_source_logs` table

### Health Checks

```bash
# Check system status
python -c "from core.options_tracker import options_tracker; print('System ready')"

# Test data sources
python -c "from data.data_sources import data_source_manager; print(data_source_manager.test_connection('polygon'))"
```

## Alert System

### Email Alerts

The system sends HTML email alerts containing:
- Risk-scored anomaly list
- Detailed metrics and ratios
- Visual indicators for severity
- Links to dashboard for further analysis

### Alert Types

1. **High Risk**: >70% insider probability
2. **Medium Risk**: 40-70% insider probability  
3. **Low Risk**: <40% insider probability

## Testing

### Unit Tests

```bash
pytest tests/
```

### Integration Tests

```bash
# Test full pipeline with sample data
python -c "from core.options_tracker import options_tracker; options_tracker.run_daily_analysis(symbols=['AAPL', 'MSFT'])"
```

## Deployment

### GitHub Actions (Automated Analysis)

The system runs automatically Monday-Friday at 4:30 PM EST (after market close at 4:00 PM):

1. **Set up secrets**: Add required secrets to GitHub repository (see `.github/workflows/setup-secrets.md`)
2. **Monitor runs**: Check Actions tab in your repository
3. **Manual trigger**: Available in GitHub Actions tab

### Streamlit Cloud (Dashboard)

Deploy your dashboard to the cloud:

1. **Connect repository**: Go to [share.streamlit.io](https://share.streamlit.io)
2. **Select repository**: Choose your options-tracker repo
3. **Set main file**: `app/main.py`
4. **Deploy**: Your dashboard will be available at https://bk-options-tracker.streamlit.app/

**Environment Variables**: Add your database and API keys in Streamlit Cloud settings.

## Security

### Row Level Security (RLS)

The database includes RLS policies for:
- Data access control
- Audit logging
- User permissions

### API Security

- API keys stored in environment variables
- Rate limiting to prevent abuse
- Request validation and sanitization

## Performance

### Optimization Features

- Database connection pooling
- Cached data loading
- Batch processing
- Parallel data fetching
- Efficient indexing

### Expected Performance

- **Processing Speed**: ~1000 symbols/hour
- **Memory Usage**: ~500MB peak
- **Database Size**: ~1GB/month for full coverage

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This system is for educational and research purposes only. It does not constitute financial advice or guarantee the detection of insider trading. Always conduct your own research and consult with financial professionals before making investment decisions.

## Support

For issues and questions:
1. Check the logs for error details
2. Review the configuration
3. Test individual components
4. Open an issue with detailed information

## Future Enhancements

- Real-time streaming data
- Additional anomaly detection algorithms
- Machine learning model improvements
- Mobile app
- API endpoints for external integration
- Advanced visualization features
