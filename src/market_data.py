"""Market Data — Fetch VNIndex historical prices."""

import pandas as pd
from datetime import datetime, timedelta
import sys
from pathlib import Path

from utils import load_config, get_project_root, ensure_dirs


def fetch_vnindex(days_lookback: int = 90) -> pd.DataFrame:
    """
    Fetch VNIndex historical data using vnstock.
    Falls back to sample data if vnstock is unavailable.
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_lookback)

    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    print(f"\n📈 Fetching VNIndex data: {start_str} → {end_str}")

    try:
        from vnstock import Vnstock
        stock = Vnstock().stock(symbol="VNINDEX", source="VCI")
        df = stock.quote.history(start=start_str, end=end_str, interval="1D")

        # Normalize column names
        col_map = {}
        for col in df.columns:
            cl = col.lower()
            if "time" in cl or "date" in cl:
                col_map[col] = "date"
            elif "close" in cl:
                col_map[col] = "close"
            elif "open" in cl:
                col_map[col] = "open"
            elif "high" in cl:
                col_map[col] = "high"
            elif "low" in cl:
                col_map[col] = "low"
            elif "vol" in cl:
                col_map[col] = "volume"

        df = df.rename(columns=col_map)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)

        print(f"  ✅ Got {len(df)} trading days from vnstock")
        return df

    except Exception as e:
        print(f"  ⚠️  vnstock failed ({e}), generating sample data...")
        return _generate_sample_data(start_str, end_str)


def _generate_sample_data(start_str: str, end_str: str) -> pd.DataFrame:
    """
    Generate realistic sample VNIndex data for demo/testing.
    Based on actual VNIndex movements in Q1 2026.
    """
    import numpy as np

    dates = pd.bdate_range(start=start_str, end=end_str)

    # Simulate VNIndex path: started ~1750, dropped to ~1580 in March, recovered to ~1700
    np.random.seed(42)
    n = len(dates)

    # Create a realistic price path
    base_price = 1750
    trend = []
    price = base_price

    for i in range(n):
        pct = i / n
        # Phase 1 (0-30%): gradual decline from 1750 to 1700
        if pct < 0.3:
            drift = -0.15
        # Phase 2 (30-50%): sharp drop to 1580 (Iran war shock)
        elif pct < 0.5:
            drift = -0.8
        # Phase 3 (50-70%): volatile bottom around 1580-1620
        elif pct < 0.7:
            drift = 0.1
        # Phase 4 (70-100%): recovery to 1700
        else:
            drift = 0.5

        daily_return = (drift + np.random.normal(0, 1.2)) / 100
        price *= 1 + daily_return
        price = max(price, 1500)  # Floor
        trend.append(price)

    df = pd.DataFrame(
        {
            "date": dates[:n],
            "open": [p * (1 + np.random.uniform(-0.005, 0.005)) for p in trend],
            "high": [p * (1 + abs(np.random.normal(0, 0.008))) for p in trend],
            "low": [p * (1 - abs(np.random.normal(0, 0.008))) for p in trend],
            "close": trend,
            "volume": [np.random.randint(400_000_000, 1_200_000_000) for _ in trend],
        }
    )

    df["date"] = pd.to_datetime(df["date"])
    print(f"  📊 Generated {len(df)} sample trading days")
    print(f"  📉 Range: {df['close'].min():.0f} — {df['close'].max():.0f}")
    return df


def save_market_data(df: pd.DataFrame, filename: str = "vnindex_prices.csv"):
    """Save market data to CSV."""
    ensure_dirs()
    output_path = get_project_root() / "data" / filename
    df.to_csv(output_path, index=False)
    print(f"💾 Saved market data to {output_path}")
    return output_path


def main():
    """Fetch and save VNIndex data."""
    print("=" * 60)
    print("📈 Market News Timeline — Market Data Fetcher")
    print("=" * 60)

    config = load_config()
    days = config.get("market", {}).get("days_lookback", 90)

    df = fetch_vnindex(days)
    save_market_data(df)

    print(f"\n📊 VNIndex Summary:")
    print(f"  • Latest close: {df['close'].iloc[-1]:.2f}")
    print(f"  • Period high: {df['close'].max():.2f}")
    print(f"  • Period low: {df['close'].min():.2f}")
    print(f"  • Trading days: {len(df)}")


if __name__ == "__main__":
    main()
