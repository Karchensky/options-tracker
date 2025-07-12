import pandas as pd

def get_sp_list(url, symbol_col='Symbol'):
    tables = pd.read_html(url)
    for table in tables:
        if symbol_col in table.columns:
            return table[symbol_col].str.replace(r'\.', '-', regex=True).tolist()
    return []

def save_sp1500_tickers(csv_path="sp1500_tickers.csv"):
    urls = {
        'S&P 500': "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
        'S&P 400': "https://en.wikipedia.org/wiki/List_of_S%26P_400_companies",
        'S&P 600': "https://en.wikipedia.org/wiki/List_of_S%26P_600_companies",
    }

    tickers = []
    for name, url in urls.items():
        try:
            lst = get_sp_list(url)
            tickers.extend(lst)
            print(f"{name}: {len(lst)} tickers")
        except Exception as e:
            print(f"Failed to fetch {name}: {e}")

    # Dedupe and save
    unique_tickers = sorted(set(tickers))
    df = pd.DataFrame(unique_tickers, columns=["Symbol"])
    df.to_csv(csv_path, index=False)
    print(f"Saved {len(unique_tickers)} tickers to {csv_path}")

if __name__ == "__main__":
    save_sp1500_tickers()