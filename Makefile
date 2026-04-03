.PHONY: setup crawl classify market chart all clean

# Setup virtual environment
setup:
	python -m venv venv
	./venv/bin/pip install -r requirements.txt
	@echo "✅ Setup done. Activate with: source venv/bin/activate"

# Individual steps
crawl:
	cd src && python rss_crawler.py

classify:
	cd src && python news_classifier.py

market:
	cd src && python market_data.py

# Generate all charts (runs full pipeline)
chart:
	cd src && python chart_timeline.py

# Run everything
all: chart

# Clean generated files
clean:
	rm -f data/*.csv data/*.json
	rm -f output/*.png output/*.pdf
	@echo "🧹 Cleaned data and output"
