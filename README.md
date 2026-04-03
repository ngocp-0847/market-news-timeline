# 📈 Market News Timeline — VNIndex & Global Events

Trực quan hóa dòng thời gian biến động cổ phiếu theo tin tức địa chính trị và tài chính, sử dụng Python + Seaborn.

## Features

- 🔗 Crawl RSS từ CNBC, Bloomberg, FT, SCMP (tin Mỹ + Trung Quốc)
- 📰 Phân loại tin tức theo category (geopolitical, monetary, trade, energy, earnings)
- 📊 Chart timeline: VNIndex + sự kiện tin tức overlay
- 🎨 Seaborn + Matplotlib visualization
- 💾 Export chart PNG + CSV dữ liệu

## Quick Start

```bash
# 1. Clone & setup
git clone <repo-url>
cd market-news-timeline
pip install -r requirements.txt

# 2. Crawl RSS feeds
python src/rss_crawler.py

# 3. Generate timeline chart
python src/chart_timeline.py

# Output: output/vnindex_news_timeline.png
```

## Project Structure

```
market-news-timeline/
├── README.md
├── requirements.txt
├── config.yaml              # RSS feeds & settings
├── src/
│   ├── __init__.py
│   ├── rss_crawler.py       # Crawl & parse RSS feeds
│   ├── news_classifier.py   # Classify news by category
│   ├── market_data.py       # Fetch VNIndex price data
│   ├── chart_timeline.py    # Main chart generation
│   └── utils.py             # Helper functions
├── data/
│   └── .gitkeep
└── output/
    └── .gitkeep
```

## RSS Sources

| Source | Region | Feed |
|--------|--------|------|
| CNBC | US | Top News & Analysis |
| Bloomberg | US | Markets |
| Financial Times | US/Global | Home International |
| SCMP | China/Asia | World |

## Chart Output

Timeline chart hiển thị:
- Đường giá VNIndex (line chart)
- Markers tin tức quan trọng trên timeline
- Color-coded theo category
- Annotations cho sự kiện lớn

## Configuration

Edit `config.yaml` để thêm/bớt RSS feeds, thay đổi thời gian crawl, hoặc tùy chỉnh chart style.

## License

MIT
