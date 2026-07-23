import yfinance as yf
from sqlalchemy import text

from backend.app.database.database import engine
from backend.repositories.company_repository import get_all_companies


def download_price_history(symbol):
    """
    Download historical price data for a stock.
    """
    print(f"Processing {symbol}")

    ticker = yf.Ticker(f"{symbol}.NS")
    return ticker.history(period="5d")


def save_price_history(symbol, data):
    """
    Save historical price data to PostgreSQL.
    """
    with engine.begin() as conn:
        for date, row in data.iterrows():
            conn.execute(
                text("""
                    INSERT INTO stock_prices
                    (symbol, trade_date, open, high, low, close, volume)
                    VALUES
                    (:symbol, :trade_date, :open, :high, :low, :close, :volume)
                    ON CONFLICT (symbol, trade_date)
                    DO NOTHING
                """),
                {
                    "symbol": symbol,
                    "trade_date": date.date(),
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "volume": int(row["Volume"]),
                },
            )


def process_company(symbol):
    """
    Download and save data for one company.
    """
    data = download_price_history(symbol)
    save_price_history(symbol, data)


def main():
    """
    Main entry point.
    """
    companies = get_all_companies()

    for company in companies:
        symbol = company[0]
        process_company(symbol)

    print("Saved data to PostgreSQL successfully!")


if __name__ == "__main__":
    main()
