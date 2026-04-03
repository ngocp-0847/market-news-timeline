"""RSS Feed Crawler — Fetch and parse news from financial RSS feeds."""

import feedparser
import pandas as pd
from datetime import datetime, timedelta
from dateutil import parser as dateparser
import pytz
import json
import sys
from pathlib import Path

from utils import load_config, get_project_root, ensure_dirs


def crawl_feed(feed_key: str, feed_config: dict) -> list[dict]:
    """Crawl a single RSS feed and return parsed articles."""
    url = feed_config["url"]
    name = feed_config["name"]
    region = feed_config["region"]

    print(f"  📡 Crawling {name} ({region})...")

    try:
        feed = feedparser.parse(url)
    except Exception as e:
        print(f"  ❌ Error crawling {name}: {e}")
        return []

    articles = []
    for entry in feed.entries:
        # Parse publication date
        pub_date = None
        for date_field in ["published", "updated", "created"]:
            if hasattr(entry, date_field) and getattr(entry, date_field):
                try:
                    pub_date = dateparser.parse(getattr(entry, date_field))
                    if pub_date.tzinfo is None:
                        pub_date = pytz.utc.localize(pub_date)
                    # Convert to Vietnam time
                    pub_date = pub_date.astimezone(pytz.timezone("Asia/Ho_Chi_Minh"))
                    break
                except (ValueError, TypeError):
                    continue

        if pub_date is None:
            continue

        title = entry.get("title", "").strip()
        description = entry.get("description", entry.get("summary", "")).strip()
        link = entry.get("link", "")

        if not title:
            continue

        articles.append(
            {
                "source": feed_key,
                "source_name": name,
                "region": region,
                "title": title,
                "description": description,
                "link": link,
                "published": pub_date.isoformat(),
                "published_date": pub_date.strftime("%Y-%m-%d"),
                "published_ts": pub_date.timestamp(),
            }
        )

    print(f"  ✅ {name}: {len(articles)} articles")
    return articles


def crawl_all_feeds(config: dict = None) -> pd.DataFrame:
    """Crawl all configured RSS feeds and return a DataFrame."""
    if config is None:
        config = load_config()

    all_articles = []
    feeds = config.get("rss_feeds", {})

    print(f"\n🔄 Crawling {len(feeds)} RSS feeds...\n")

    for feed_key, feed_config in feeds.items():
        articles = crawl_feed(feed_key, feed_config)
        all_articles.extend(articles)

    if not all_articles:
        print("⚠️  No articles found!")
        return pd.DataFrame()

    df = pd.DataFrame(all_articles)
    df["published"] = pd.to_datetime(df["published"])
    df = df.sort_values("published", ascending=False).reset_index(drop=True)

    print(f"\n📊 Total: {len(df)} articles from {len(feeds)} sources")
    return df


def save_articles(df: pd.DataFrame, filename: str = "news_raw.csv"):
    """Save crawled articles to CSV."""
    ensure_dirs()
    output_path = get_project_root() / "data" / filename
    df.to_csv(output_path, index=False, encoding="utf-8")
    print(f"💾 Saved to {output_path}")
    return output_path


def main():
    """Main entry point for RSS crawler."""
    print("=" * 60)
    print("📰 Market News Timeline — RSS Crawler")
    print("=" * 60)

    config = load_config()
    df = crawl_all_feeds(config)

    if df.empty:
        print("No data to save.")
        sys.exit(1)

    save_articles(df)

    # Print summary
    print("\n📋 Summary by source:")
    for source, count in df["source_name"].value_counts().items():
        print(f"  • {source}: {count} articles")

    print(f"\n📅 Date range: {df['published_date'].min()} → {df['published_date'].max()}")


if __name__ == "__main__":
    main()
