#!/bin/bash
# Quick run script — crawl, classify, fetch prices, generate charts

set -e

echo "🚀 Market News Timeline — Full Pipeline"
echo "========================================="

cd "$(dirname "$0")"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found!"
    exit 1
fi

# Install deps if needed
if [ ! -d "venv" ]; then
    echo "📦 Setting up virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Run pipeline
echo ""
cd src
python chart_timeline.py

echo ""
echo "🎉 Done! Charts are in the output/ directory."
echo "   Open: output/vnindex_news_timeline.png"
