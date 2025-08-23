# Big Three Anime NLP Pipeline - Makefile
# Professional automation for the extraordinary analysis

.PHONY: help install test clean scrape process nlp stats export pipeline full-pipeline baseline-pipeline

# Default target
help:
	@echo "🚀 Big Three Anime NLP Pipeline - Makefile"
	@echo "=========================================="
	@echo ""
	@echo "Available commands:"
	@echo "  install          Install dependencies and setup environment"
	@echo "  test             Run tests and validation"
	@echo "  clean            Clean generated files and data"
	@echo ""
	@echo "Pipeline phases:"
	@echo "  scrape           Phase 1: Scrape reviews and statistics"
	@echo "  process          Phase 2: Process and merge data"
	@echo "  nlp              Phase 3: NLP analysis (sentiment + topics)"
	@echo "  stats            Phase 4: Statistical analysis"
	@echo "  export           Phase 5: Export final datasets"
	@echo ""
	@echo "Full pipelines:"
	@echo "  pipeline         Run complete pipeline with advanced NLP"
	@echo "  baseline-pipeline Run pipeline with baseline NLP only"
	@echo "  full-pipeline    Run pipeline with all features enabled"
	@echo ""
	@echo "Development:"
	@echo "  lint             Run code linting and formatting"
	@echo "  docs             Generate documentation"
	@echo "  docker           Build and run with Docker"
	@echo ""

# Environment setup
install:
	@echo "🔧 Setting up environment..."
	python -m venv .venv
	@echo "✓ Virtual environment created"
	@echo "📦 Installing dependencies..."
	.venv/bin/pip install -r requirements.txt
	@echo "✓ Dependencies installed"
	@echo "🚀 Environment ready! Activate with: source .venv/bin/activate"

# Testing and validation
test:
	@echo "🧪 Running tests..."
	python -m pytest tests/ -v --cov=src --cov-report=html
	@echo "✓ Tests completed"

# Clean generated files
clean:
	@echo "🧹 Cleaning generated files..."
	rm -rf data/raw/*.csv
	rm -rf data/processed/*.csv
	rm -rf data/analysis/*.csv
	rm -rf data/exports/*.csv
	rm -rf reports/*.txt
	rm -rf logs/*.log
	@echo "✓ Cleanup completed"

# Pipeline phases
scrape:
	@echo "🔍 Phase 1: Scraping data..."
	python -m src.scraping.scrape_reviews_selenium
	python -m src.scraping.scrape_stats
	@echo "✓ Scraping completed"

process:
	@echo "🔄 Phase 2: Processing and merging data..."
	python -m src.processing.data_merger --create-tableau
	@echo "✓ Processing completed"

nlp:
	@echo "🧠 Phase 3: NLP analysis..."
	python -m src.nlp.sentiment_advanced data/processed/merged_reviews.csv data/processed/reviews_with_sentiment.csv --use-transformers
	python -m src.nlp.topic_modeling_advanced data/processed/reviews_with_sentiment.csv data/processed/reviews_with_topics.csv --use-bertopic --visualize
	@echo "✓ NLP analysis completed"

stats:
	@echo "📈 Phase 4: Statistical analysis..."
	python -m src.analysis.statistical_analysis data/processed/reviews_with_topics.csv data/analysis/final_analysis.csv
	@echo "✓ Statistical analysis completed"

export:
	@echo "📤 Phase 5: Exporting final datasets..."
	python -c "
from src.processing.data_merger import AnimeDataMerger
merger = AnimeDataMerger()
merger.create_tableau_datasets('data/processed/merged_reviews.csv', 'data/processed/merged_stats.csv')
"
	@echo "✓ Export completed"

# Full pipelines
pipeline:
	@echo "🚀 Running complete pipeline..."
	python -m src.pipeline
	@echo "✓ Pipeline completed"

baseline-pipeline:
	@echo "🚀 Running baseline pipeline (VADER + LDA only)..."
	python -m src.pipeline --no-transformers --no-bertopic
	@echo "✓ Baseline pipeline completed"

full-pipeline:
	@echo "🚀 Running full pipeline with all features..."
	python -m src.pipeline --force-scrape
	@echo "✓ Full pipeline completed"

# Development tools
lint:
	@echo "🔍 Running code linting..."
	black src/ --check
	flake8 src/ --max-line-length=100
	@echo "✓ Linting completed"

format:
	@echo "🎨 Formatting code..."
	black src/
	@echo "✓ Code formatting completed"

docs:
	@echo "📚 Generating documentation..."
	pydoc -w src/
	@echo "✓ Documentation generated"

# Docker support
docker-build:
	@echo "🐳 Building Docker image..."
	docker build -t big-three-anime-nlp .
	@echo "✓ Docker image built"

docker-run:
	@echo "🐳 Running with Docker..."
	docker run -it --rm -v $(PWD)/data:/app/data big-three-anime-nlp
	@echo "✓ Docker execution completed"

# Quick analysis (for development)
quick-analysis:
	@echo "⚡ Running quick analysis on existing data..."
	python -c "
import pandas as pd
df = pd.read_csv('data/processed/merged_reviews.csv')
print(f'Total reviews: {len(df)}')
print(f'Entities: {df.entity.unique()}')
print(f'Average review length: {df.review_text.str.len().mean():.1f} chars')
"
	@echo "✓ Quick analysis completed"

# Data validation
validate:
	@echo "✅ Validating data integrity..."
	python -c "
import pandas as pd
import os

# Check required files
required_files = [
    'data/raw/all_reviews_raw.csv',
    'data/raw/all_stats_raw.csv',
    'data/processed/merged_reviews.csv',
    'data/processed/merged_stats.csv'
]

for file_path in required_files:
    if os.path.exists(file_path):
        df = pd.read_csv(file_path)
        print(f'✅ {file_path}: {len(df)} rows')
    else:
        print(f'❌ {file_path}: Missing')

# Check data quality
if os.path.exists('data/processed/merged_reviews.csv'):
    df = pd.read_csv('data/processed/merged_reviews.csv')
    print(f'\\n📊 Data Quality Check:')
    print(f'  - Duplicates: {df.duplicated(subset=[\"review_text\"]).sum()}')
    print(f'  - Missing text: {df.review_text.isna().sum()}')
    print(f'  - Short reviews (<50 chars): {(df.review_text.str.len() < 50).sum()}')
"
	@echo "✓ Validation completed"

# Performance monitoring
monitor:
	@echo "📊 Monitoring pipeline performance..."
	python -c "
import os
import time
from pathlib import Path

# Check file sizes
data_dir = Path('data')
total_size = 0
file_count = 0

for file_path in data_dir.rglob('*.csv'):
    if file_path.is_file():
        size = file_path.stat().st_size / 1024  # KB
        total_size += size
        file_count += 1
        print(f'📁 {file_path}: {size:.1f} KB')

print(f'\\n📈 Summary:')
print(f'  - Total files: {file_count}')
print(f'  - Total size: {total_size:.1f} KB ({total_size/1024:.1f} MB)')
"
	@echo "✓ Monitoring completed"

# Helpers
setup-dirs:
	@echo "📁 Setting up directory structure..."
	mkdir -p data/raw data/processed data/analysis data/exports logs reports tests
	@echo "✓ Directories created"

check-env:
	@echo "🔍 Checking environment..."
	@python -c "
import sys
print(f'Python version: {sys.version}')
try:
    import pandas as pd
    print(f'Pandas version: {pd.__version__}')
except ImportError:
    print('❌ Pandas not installed')
try:
    import selenium
    print(f'Selenium version: {selenium.__version__}')
except ImportError:
    print('❌ Selenium not installed')
"
	@echo "✓ Environment check completed"

# Default target
.DEFAULT_GOAL := help 