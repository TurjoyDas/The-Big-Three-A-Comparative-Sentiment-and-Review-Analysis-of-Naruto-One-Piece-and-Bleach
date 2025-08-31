#  Big Three Anime NLP — The Extraordinary Analysis

> **How fan sentiment and topics differ across Naruto (incl. Shippuden), One Piece, and Bleach (incl. TYBW Part 1 & 2) — and where text sentiment clashes with numeric scores.**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Ready%20for%20Analysis-brightgreen.svg)]()

## 🌟 The Spark — Why This Project?

The "Big Three" — **Naruto**, **One Piece**, and **Bleach** — are cultural icons in anime, shaping global fandom for over two decades. Yet fan opinions often differ sharply between casual viewers, hardcore fans, and review scores.

This project goes beyond "average ratings" to uncover:

- **What fans actually say** in their reviews
- **How they feel** about different arcs and series
- **What topics dominate** fan discussions
- **Where sentiment diverges** from numeric scores

## 🎯 The Challenge — More Than Just Scraping

https://myanimelist.net/ is one of the largest anime review platforms, but reviews are hidden behind "Read More" buttons, loaded dynamically, and spread across multiple versions of the same franchise — like Naruto Shippuden and Bleach's Thousand-Year Blood War.

To compare them fairly, we needed to:

- **Scrape dynamically** with Selenium
- **Merge related series** into unified entities
- **Extract emotions and themes** from thousands of fan-written reviews
- **Respect privacy** by collecting no personal information

##  The Architecture — Technical Excellence

### **Multi-Model NLP Pipeline**

- **Baseline**: VADER + TextBlob sentiment analysis
- **Advanced**: Transformer-based sentiment (RoBERTa) for credibility
- **Topic Modeling**: LDA + BERTopic for theme discovery
- **Statistical Rigor**: Bootstrap CIs, effect sizes, nonparametric tests

### **Entity Mapping Strategy**

```
Naruto (combined) = Naruto + Naruto Shippuden
Bleach (combined) = Bleach + TYBW (Part 1 & 2)
One Piece = One Piece
```

### **Production-Grade Engineering**

- **Config-driven** pipeline with YAML configuration
- **Modular architecture** with clear separation of concerns
- **Comprehensive error handling** and logging
- **Reproducible results** with pinned dependencies
- **Automated testing** and validation

## 🚀 Quick Start

### **1. Environment Setup (Windows-friendly)**

```bash
# Clone and setup
git clone <your-repo>
cd big-three-anime-nlp-starter

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install minimal dependencies
pip install -r requirements.txt
# Optional advanced models (large): transformers torch bertopic spacy
```

### **2. Run the Complete Pipeline (skips scraping if data exists)**

```bash
# Run everything end-to-end
python -m src.pipeline

# Or run with specific options
python -m src.pipeline --no-transformers --no-bertopic  # Baseline only
python -m src.pipeline --force-scrape  # Re-scrape data (not needed if raw CSVs present)
```

### **3. Individual Components**

```bash
# Scrape reviews and stats
python -m src.scraping.scrape_reviews_selenium
python -m src.scraping.scrape_stats

# Process and merge data
python -m src.processing.data_merger --create-tableau

# NLP analysis
python -m src.nlp.sentiment_advanced data/processed/merged_reviews.csv data/processed/reviews_with_sentiment.csv
python -m src.nlp.topic_modeling_advanced data/processed/reviews_with_sentiment.csv data/processed/reviews_with_topics.csv --visualize

# Statistical analysis
python -m src.analysis.statistical_analysis data/processed/reviews_with_topics.csv output.csv
```

## 📊 What You'll Discover

### **Sentiment vs. User Score Divergence**

- **High MAL ratings but low sentiment**: Often due to pacing/filler complaints
- **Low MAL ratings but high sentiment**: Hidden gems or niche appeal
- **Sentiment agreement rates** between different NLP models

### **Topic Analysis Insights**

- **Filler episodes** and pacing discussions
- **Animation quality** and fight scene commentary
- **Character development** and arc progression
- **World-building** and lore discussions

### **Statistical Rigor**

- **95% confidence intervals** via bootstrap resampling
- **Effect sizes** (Cliff's Delta) for entity comparisons
- **Nonparametric tests** avoiding distribution assumptions
- **Residual analysis** showing sentiment-score mismatches

## 🎨 Tableau Dashboard Features

The pipeline generates **Tableau-ready datasets**:

- **tableau_reviews_final.csv**: Review-level data incl. `vader_compound`, `lda_topic_id`, `lda_topic_label`, buckets, flags, readability
- **tableau_stats_final.csv**: Entity-level stats (score histograms, statuses)
- **tableau_kpis.csv**: KPI metrics (counts, mean/median sentiment, +/- rates)
- **tableau_topics_by_entity.csv**: Topic distribution by entity
- **tableau_topic_impact.csv**: Mean/median sentiment per topic × entity
- **tableau_overrated_index.csv**: Residual-based overrated/underrated index
- **tableau_aspect_sentiment.csv**: Sentiment where aspects are mentioned
- **tableau_aspect_lift.csv**: Impact lift when aspects are mentioned
- **data_dictionary.md**: Field-by-field definitions

## 📁 Project Structure

```
The-Big-Three-A-Comparative-Sentiment-and-Review-Analysis-of-Naruto-One-Piece-and-Bleach/
├── data/ # Data storage
│ ├── raw/ # Scraped data (direct from MyAnimeList)
│ ├── processed/ # Cleaned & merged datasets
│ ├── analysis/ # NLP results (sentiment, topics, stats)
│ └── exports/ # Tableau-ready datasets and summaries
│
├── docs/ # Documentation and reports
│ ├── implementation_summary.md # Technical architecture & pipeline phases
│ ├── pipeline_success_summary.md # End-to-end run results & discoveries
│ └── topic_interpretation.md # Guide to LDA/BERTopic topic meaning
│
├── src/ # Source code
│ ├── scraping/ # Web scraping modules (reviews, stats)
│ ├── processing/ # Data cleaning & entity merging
│ ├── nlp/ # Sentiment analysis + topic modeling
│ ├── analysis/ # Statistical testing & effect sizes
│ └── pipeline.py # Orchestrates full 5-phase pipeline
│
├── .gitignore # Git ignore rules (cache, data dumps, logs)
├── Dockerfile # Containerization for reproducible environment
├── LICENSE # License information (MIT)
├── Makefile # Automation commands (install, test, run pipeline)
├── README.md # Project overview (this file)
├── config.yml # Configuration file (entities, scraping params)
└── requirements.txt # Python dependencies
```

## 🔧 Configuration

Edit `config.yml` to customize:

- **Page limits** and scraping delays
- **Entity mappings** for series combinations
- **MAL URLs** and series IDs
- **Output directories** and file paths

## 📈 Status & Success Metrics

I processed 1,796 usable reviews (after cleaning/dedup from ~1,800 scraped) across 3 entities and generated multiple Tableau-ready datasets. The pipeline runs end‑to‑end on Windows and skips scraping if raw CSVs exist.


- ✅ **≥1500 quality reviews** with <5% duplicates
- ✅ **Clear sentiment divergences** between text and scores
- ✅ **Coherent topics** matching anime themes
- ✅ **Fast dashboard** (<2s interactions)
- ✅ **Statistical significance** with effect sizes
- ✅ **Production-ready** pipeline with CI/CD



## 🤝 Contributing

This project welcomes contributions! Areas for enhancement:

- **Additional NLP models** and techniques
- **Enhanced visualizations** and dashboard features
- **Performance optimizations** for large-scale scraping
- **Testing and validation** improvements

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- **MyAnimeList** for providing the review platform
- **Open source NLP community** for the amazing tools
- **Anime fandom** for the passionate reviews that make this analysis possible

---

**Ready to discover what fans really think about the Big Three?** 

Run `python -m src.pipeline` and let the analysis begin!
