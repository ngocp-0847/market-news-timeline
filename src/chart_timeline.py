"""Chart Timeline — Generate VNIndex + News Events visualization using Seaborn."""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
from matplotlib.offsetbox import AnchoredText
import seaborn as sns
from datetime import datetime
from pathlib import Path
import textwrap
import sys

from utils import load_config, get_project_root, ensure_dirs, truncate_text

# ─── Pipeline ────────────────────────────────────────────────────────────────

from rss_crawler import crawl_all_feeds, save_articles
from news_classifier import classify_dataframe, filter_relevant, save_classified
from market_data import fetch_vnindex, save_market_data


def run_pipeline(config: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run full data pipeline: crawl → classify → fetch prices."""
    # Step 1: Crawl RSS
    news_df = crawl_all_feeds(config)
    if news_df.empty:
        print("❌ No news data. Exiting.")
        sys.exit(1)
    save_articles(news_df)

    # Step 2: Classify
    news_df = classify_dataframe(news_df, config)
    news_df = filter_relevant(news_df, min_confidence=0.2)
    save_classified(news_df)

    # Step 3: Fetch market data
    days = config.get("market", {}).get("days_lookback", 90)
    price_df = fetch_vnindex(days)
    save_market_data(price_df)

    return news_df, price_df


def load_cached_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load previously saved data from CSV files."""
    root = get_project_root()
    news_path = root / "data" / "news_classified.csv"
    price_path = root / "data" / "vnindex_prices.csv"

    if not news_path.exists() or not price_path.exists():
        return None, None

    news_df = pd.read_csv(news_path)
    news_df["published"] = pd.to_datetime(news_df["published"])

    price_df = pd.read_csv(price_path)
    price_df["date"] = pd.to_datetime(price_df["date"])

    return news_df, price_df


# ─── Chart Generation ────────────────────────────────────────────────────────


def create_timeline_chart(
    news_df: pd.DataFrame,
    price_df: pd.DataFrame,
    config: dict,
    output_path: str = None,
):
    """Create the main timeline visualization."""
    chart_cfg = config.get("chart", {})
    categories = config.get("categories", {})

    figsize = tuple(chart_cfg.get("figsize", [20, 12]))
    dpi = chart_cfg.get("dpi", 150)
    style = chart_cfg.get("style", "whitegrid")
    max_annotations = chart_cfg.get("max_annotations", 25)

    # ── Setup ──
    sns.set_theme(style=style, font_scale=1.1)
    fig, (ax_price, ax_vol) = plt.subplots(
        2, 1, figsize=figsize, height_ratios=[4, 1],
        gridspec_kw={"hspace": 0.08}, sharex=True
    )

    # ── Price Chart ──
    price_color = chart_cfg.get("price_line_color", "#2c3e50")
    lw = chart_cfg.get("price_line_width", 2.5)

    # Price area fill
    ax_price.fill_between(
        price_df["date"], price_df["close"],
        alpha=0.08, color=price_color
    )
    ax_price.plot(
        price_df["date"], price_df["close"],
        color=price_color, linewidth=lw, label="VNIndex Close", zorder=3
    )

    # Moving averages
    if len(price_df) >= 20:
        ma20 = price_df["close"].rolling(20).mean()
        ax_price.plot(
            price_df["date"], ma20,
            color="#e74c3c", linewidth=1, linestyle="--",
            alpha=0.7, label="MA20"
        )
    if len(price_df) >= 50:
        ma50 = price_df["close"].rolling(50).mean()
        ax_price.plot(
            price_df["date"], ma50,
            color="#3498db", linewidth=1, linestyle="--",
            alpha=0.7, label="MA50"
        )

    # ── News Events on Price Chart ──
    # Map news dates to closest trading dates for y-position
    news_df = news_df.copy()
    news_df["event_date"] = pd.to_datetime(news_df["published"]).dt.normalize()

    # Get price at closest trading day
    price_dates = set(price_df["date"].dt.normalize())
    date_to_price = dict(zip(price_df["date"].dt.normalize(), price_df["close"]))

    def get_nearest_price(event_date):
        """Find the closest trading day's price."""
        if event_date in date_to_price:
            return date_to_price[event_date]
        # Search nearby days
        for delta in range(1, 8):
            for d in [event_date - pd.Timedelta(days=delta),
                       event_date + pd.Timedelta(days=delta)]:
                if d in date_to_price:
                    return date_to_price[d]
        return None

    news_df["y_price"] = news_df["event_date"].apply(get_nearest_price)
    news_with_price = news_df.dropna(subset=["y_price"])

    # Plot events by category
    for cat_name, cat_cfg in categories.items():
        cat_news = news_with_price[news_with_price["category"] == cat_name]
        if cat_news.empty:
            continue

        color = cat_cfg.get("color", "#95a5a6")
        marker = cat_cfg.get("marker", "o")

        ax_price.scatter(
            cat_news["event_date"],
            cat_news["y_price"],
            c=color, marker=marker, s=100, alpha=0.8,
            edgecolors="white", linewidths=0.8,
            zorder=5, label=cat_name.replace("_", " ").title()
        )

    # ── Annotations for top events ──
    if not news_with_price.empty:
        top_news = (
            news_with_price
            .sort_values("confidence", ascending=False)
            .drop_duplicates(subset=["title"])
            .head(max_annotations)
        )

        fontsize = chart_cfg.get("annotation_fontsize", 7)
        y_offsets = _compute_annotation_offsets(top_news, price_df)

        for idx, (_, row) in enumerate(top_news.iterrows()):
            short_title = truncate_text(row["title"], 50)
            cat_color = row.get("category_color", "#666")

            y_offset = y_offsets[idx]
            x_offset = 10 if idx % 2 == 0 else -10

            ax_price.annotate(
                short_title,
                xy=(row["event_date"], row["y_price"]),
                xytext=(x_offset, y_offset),
                textcoords="offset points",
                fontsize=fontsize,
                color=cat_color,
                fontweight="bold",
                alpha=0.85,
                arrowprops=dict(
                    arrowstyle="-",
                    color=cat_color,
                    alpha=0.4,
                    lw=0.8,
                ),
                bbox=dict(
                    boxstyle="round,pad=0.2",
                    facecolor="white",
                    edgecolor=cat_color,
                    alpha=0.7,
                    linewidth=0.5,
                ),
                ha="left" if x_offset > 0 else "right",
                va="center",
            )

    # ── Volume Chart ──
    if "volume" in price_df.columns:
        vol_colors = [
            "#2ecc71" if c >= o else "#e74c3c"
            for c, o in zip(price_df["close"], price_df["open"])
        ]
        ax_vol.bar(
            price_df["date"],
            price_df["volume"] / 1e9,
            color=vol_colors, alpha=0.6, width=0.8
        )
        ax_vol.set_ylabel("Volume (tỷ)", fontsize=10)
        ax_vol.yaxis.set_label_position("right")
        ax_vol.yaxis.tick_right()

    # ── Formatting ──
    title = chart_cfg.get("title", "VNIndex Timeline với Tin tức Toàn cầu")
    ax_price.set_title(title, fontsize=16, fontweight="bold", pad=20)
    ax_price.set_ylabel("VNIndex", fontsize=12)
    ax_price.yaxis.set_label_position("right")
    ax_price.yaxis.tick_right()
    ax_price.grid(True, alpha=0.3)

    # Date formatting
    ax_vol.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
    ax_vol.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
    plt.setp(ax_vol.xaxis.get_majorticklabels(), rotation=45, ha="right")

    # Legend
    ax_price.legend(
        loc="upper left", fontsize=8, framealpha=0.9,
        ncol=2, borderpad=0.8
    )

    # ── Info box ──
    info_text = (
        f"Data: {price_df['date'].min().strftime('%d/%m/%Y')} → "
        f"{price_df['date'].max().strftime('%d/%m/%Y')}\n"
        f"News events: {len(news_with_price)} | "
        f"Sources: CNBC, Bloomberg, FT, SCMP\n"
        f"Generated: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )
    anchored_text = AnchoredText(
        info_text, loc="lower left", prop=dict(size=7, alpha=0.6),
        frameon=True, pad=0.5
    )
    anchored_text.patch.set_boxstyle("round,pad=0.3")
    anchored_text.patch.set_alpha(0.5)
    ax_price.add_artist(anchored_text)

    plt.tight_layout()

    # ── Save ──
    if output_path is None:
        ensure_dirs()
        output_dir = get_project_root() / chart_cfg.get("output_dir", "output")
        output_filename = chart_cfg.get("output_filename", "vnindex_news_timeline.png")
        output_path = output_dir / output_filename

    fig.savefig(output_path, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    print(f"\n🎨 Chart saved to: {output_path}")
    return str(output_path)


def _compute_annotation_offsets(top_news: pd.DataFrame, price_df: pd.DataFrame) -> list:
    """Compute y-offsets for annotations to minimize overlap."""
    n = len(top_news)
    offsets = []
    for i in range(n):
        # Alternate above/below, with increasing distance
        direction = 1 if i % 2 == 0 else -1
        magnitude = 25 + (i // 2) * 18
        offsets.append(direction * magnitude)
    return offsets


# ─── Additional Charts ────────────────────────────────────────────────────────


def create_category_heatmap(news_df: pd.DataFrame, config: dict):
    """Create a heatmap showing news density by category and date."""
    ensure_dirs()

    news_df = news_df.copy()
    news_df["date"] = pd.to_datetime(news_df["published"]).dt.date

    pivot = news_df.groupby(["date", "category"]).size().unstack(fill_value=0)

    sns.set_theme(style="white", font_scale=0.9)
    fig, ax = plt.subplots(figsize=(16, 6))

    sns.heatmap(
        pivot.T, cmap="YlOrRd", linewidths=0.5,
        cbar_kws={"label": "Số tin"}, ax=ax
    )

    ax.set_title("Mật độ Tin tức theo Chủ đề & Ngày", fontsize=14, fontweight="bold")
    ax.set_xlabel("")
    ax.set_ylabel("")

    # Rotate x labels
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right", fontsize=7)
    plt.tight_layout()

    output_path = get_project_root() / "output" / "news_category_heatmap.png"
    fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"🎨 Heatmap saved to: {output_path}")


def create_source_distribution(news_df: pd.DataFrame, config: dict):
    """Create a pie/bar chart showing news distribution by source."""
    ensure_dirs()
    sns.set_theme(style="whitegrid", font_scale=1.0)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # By source
    source_counts = news_df["source_name"].value_counts()
    colors = sns.color_palette("Set2", len(source_counts))
    ax1.pie(
        source_counts, labels=source_counts.index, autopct="%1.0f%%",
        colors=colors, startangle=90
    )
    ax1.set_title("Phân bố theo Nguồn", fontweight="bold")

    # By category
    cat_counts = news_df["category"].value_counts()
    categories = config.get("categories", {})
    cat_colors = [categories.get(c, {}).get("color", "#95a5a6") for c in cat_counts.index]

    sns.barplot(x=cat_counts.values, y=cat_counts.index, palette=cat_colors, ax=ax2)
    ax2.set_title("Phân bố theo Chủ đề", fontweight="bold")
    ax2.set_xlabel("Số tin")

    plt.suptitle("Tổng quan Dữ liệu Tin tức", fontsize=14, fontweight="bold", y=1.02)
    plt.tight_layout()

    output_path = get_project_root() / "output" / "news_distribution.png"
    fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"🎨 Distribution chart saved to: {output_path}")


# ─── Main ─────────────────────────────────────────────────────────────────────


def main():
    """Main entry point — run pipeline and generate all charts."""
    print("=" * 60)
    print("📊 Market News Timeline — Chart Generator")
    print("=" * 60)

    config = load_config()

    # Try cached data first
    news_df, price_df = load_cached_data()

    if news_df is None or price_df is None:
        print("\n🔄 No cached data found, running full pipeline...")
        news_df, price_df = run_pipeline(config)
    else:
        print(f"\n📂 Using cached data: {len(news_df)} news, {len(price_df)} trading days")
        # Always re-crawl for fresh data in non-interactive mode
        news_df, price_df = run_pipeline(config)

    # Generate charts
    print("\n" + "─" * 40)
    print("🎨 Generating charts...\n")

    create_timeline_chart(news_df, price_df, config)
    create_category_heatmap(news_df, config)
    create_source_distribution(news_df, config)

    print("\n" + "=" * 60)
    print("✅ All charts generated! Check the output/ directory.")
    print("=" * 60)


if __name__ == "__main__":
    main()
