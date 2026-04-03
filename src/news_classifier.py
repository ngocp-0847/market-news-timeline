"""News Classifier — Categorize articles by topic using keyword matching."""

import pandas as pd
import re
from utils import load_config, get_project_root, ensure_dirs


def classify_article(title: str, description: str, categories: dict) -> tuple[str, float]:
    """
    Classify a single article into a category based on keyword matching.
    Returns (category_name, confidence_score).
    """
    text = f"{title} {description}".lower()
    best_category = "other"
    best_score = 0

    for cat_name, cat_config in categories.items():
        keywords = cat_config.get("keywords", [])
        score = 0
        for kw in keywords:
            # Count occurrences, weight title matches 2x
            title_matches = len(re.findall(re.escape(kw.lower()), title.lower()))
            desc_matches = len(re.findall(re.escape(kw.lower()), description.lower()))
            score += title_matches * 2 + desc_matches

        if score > best_score:
            best_score = score
            best_category = cat_name

    # Normalize confidence (0-1)
    confidence = min(best_score / 5.0, 1.0)
    return best_category, confidence


def classify_dataframe(df: pd.DataFrame, config: dict = None) -> pd.DataFrame:
    """Classify all articles in a DataFrame."""
    if config is None:
        config = load_config()

    categories = config.get("categories", {})

    print(f"\n🏷️  Classifying {len(df)} articles into {len(categories)} categories...\n")

    results = df.apply(
        lambda row: classify_article(
            row.get("title", ""), row.get("description", ""), categories
        ),
        axis=1,
    )

    df["category"] = [r[0] for r in results]
    df["confidence"] = [r[1] for r in results]

    # Add category metadata
    df["category_color"] = df["category"].map(
        {cat: cfg.get("color", "#95a5a6") for cat, cfg in categories.items()}
    ).fillna("#95a5a6")

    df["category_marker"] = df["category"].map(
        {cat: cfg.get("marker", "o") for cat, cfg in categories.items()}
    ).fillna("o")

    # Print summary
    print("📋 Classification results:")
    for cat, count in df["category"].value_counts().items():
        color = categories.get(cat, {}).get("color", "—")
        print(f"  • {cat}: {count} articles ({color})")

    return df


def filter_relevant(df: pd.DataFrame, min_confidence: float = 0.2) -> pd.DataFrame:
    """Filter out low-confidence and 'other' category articles."""
    filtered = df[(df["category"] != "other") & (df["confidence"] >= min_confidence)]
    print(f"\n🔍 Filtered: {len(filtered)}/{len(df)} articles (confidence >= {min_confidence})")
    return filtered.reset_index(drop=True)


def save_classified(df: pd.DataFrame, filename: str = "news_classified.csv"):
    """Save classified articles to CSV."""
    ensure_dirs()
    output_path = get_project_root() / "data" / filename
    df.to_csv(output_path, index=False, encoding="utf-8")
    print(f"💾 Saved classified data to {output_path}")
    return output_path


def main():
    """Classify previously crawled articles."""
    print("=" * 60)
    print("🏷️  Market News Timeline — News Classifier")
    print("=" * 60)

    # Load raw articles
    raw_path = get_project_root() / "data" / "news_raw.csv"
    if not raw_path.exists():
        print("❌ No raw data found. Run rss_crawler.py first!")
        return

    df = pd.read_csv(raw_path)
    config = load_config()

    df = classify_dataframe(df, config)
    df = filter_relevant(df)
    save_classified(df)


if __name__ == "__main__":
    main()
