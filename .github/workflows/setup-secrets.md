# GitHub Actions Setup Instructions

## Required Secrets

You need to add these secrets to your GitHub repository:

1. Go to your repository on GitHub
2. Click "Settings" tab
3. Click "Secrets and variables" → "Actions"
4. Click "New repository secret" for each of these:

### Database Secrets
- `SUPABASE_DB_URL` = Your Supabase database connection string
- `SUPABASE_API_KEY` = Your Supabase anon key
- `SUPABASE_URL` = Your Supabase project URL

### Email Configuration
- `SENDER_EMAIL` = Your Gmail address
- `EMAIL_PASSWORD` = Your Gmail app password
- `RECIPIENT_EMAIL` = Where to send alerts

### API Keys
- `POLYGON_API_KEY` = Your Polygon.io API key
- `ALPHA_VANTAGE_API_KEY` = Your Alpha Vantage API key
- `QUANDL_API_KEY` = Your Quandl API key

## After Adding Secrets

The GitHub Actions workflow will automatically run:
- Every weekday at 4:30 PM EST (after market close)
- Manual trigger available in Actions tab
- Results stored in database
- Email notifications sent for anomalies 