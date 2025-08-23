"""
Comprehensive Pipeline for Big Three Anime NLP Analysis
Orchestrates the entire workflow from scraping to final outputs
"""

import os
import sys
import time
import argparse
from pathlib import Path
import yaml
from datetime import datetime
import pandas as pd

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.scraping.scrape_reviews_selenium import main as scrape_reviews
from src.scraping.scrape_stats import main as scrape_stats
from src.processing.data_merger import AnimeDataMerger
from src.nlp.sentiment_advanced import AdvancedSentimentAnalyzer
from src.nlp.topic_modeling_advanced import AdvancedTopicModeler
from src.analysis.statistical_analysis import StatisticalAnalyzer

class AnimeAnalysisPipeline:
    """
    End-to-end pipeline for anime review analysis
    """
    
    def __init__(self, config_path: str = "config.yml"):
        self.config = self._load_config(config_path)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.results = {}
        
        # Create output directories
        self._setup_directories()
        
        print(" Big Three Anime NLP Pipeline Initialized")
        print(f" Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
    
    def _load_config(self, config_path: str) -> dict:
        """Load configuration file"""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            return config
        except Exception as e:
            print(f" Failed to load config: {e}")
            return {}
    
    def _setup_directories(self):
        """Create necessary output directories"""
        dirs = [
            "data/raw",
            "data/processed", 
            "data/exports",
            "data/analysis",
            "logs",
            "reports"
        ]
        
        for dir_path in dirs:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
        
        print("✓ Output directories created")
    
    def run_scraping_phase(self, force_scrape: bool = False) -> bool:
        """
        Phase 1: Scrape reviews and statistics from MyAnimeList
        
        Args:
            force_scrape: Force re-scraping even if data exists
        
        Returns:
            True if successful, False otherwise
        """
        print("\n PHASE 1: SCRAPING DATA")
        print("-" * 40)
        
        # Check if data already exists
        if not force_scrape and self._check_existing_data():
            print("✓ Data already exists, skipping scraping phase")
            return True
        
        try:
            # Scrape reviews
            print(" Scraping reviews...")
            start_time = time.time()
            
            # Import and run scraping functions
            from src.scraping.scrape_reviews_selenium import main as scrape_reviews_main
            scrape_reviews_main()
            
            review_time = time.time() - start_time
            print(f"✓ Reviews scraped in {review_time:.1f}s")
            
            # Scrape statistics
            print(" Scraping statistics...")
            start_time = time.time()
            
            from src.scraping.scrape_stats import main as scrape_stats_main
            scrape_stats_main()
            
            stats_time = time.time() - start_time
            print(f"✓ Statistics scraped in {stats_time:.1f}s")
            
            self.results['scraping'] = {
                'reviews_time': review_time,
                'stats_time': stats_time,
                'total_time': review_time + stats_time
            }
            
            return True
            
        except Exception as e:
            print(f" Scraping failed: {e}")
            return False
    
    def run_processing_phase(self) -> bool:
        """
        Phase 2: Process and merge data into combined entities
        
        Returns:
            True if successful, False otherwise
        """
        print("\n PHASE 2: PROCESSING & MERGING DATA")
        print("-" * 40)
        
        try:
            # Initialize data merger
            merger = AnimeDataMerger()
            
            # Merge reviews
            print(" Merging reviews...")
            reviews_output = "data/processed/merged_reviews.csv"
            reviews_df = merger.merge_reviews_data("data/raw", reviews_output)
            
            if reviews_df.empty:
                print(" No reviews data to process")
                return False
            
            # Merge statistics
            print(" Merging statistics...")
            stats_output = "data/processed/merged_stats.csv"
            stats_df = merger.merge_stats_data("data/raw/all_stats_raw.csv", stats_output)
            
            if stats_df.empty:
                print(" No statistics data to process")
                return False
            
            # Create Tableau datasets
            print(" Creating Tableau datasets...")
            merger.create_tableau_datasets(reviews_output, stats_output)
            
            self.results['processing'] = {
                'reviews_count': len(reviews_df),
                'entities_count': reviews_df['entity'].nunique(),
                'stats_entities': len(stats_df)
            }
            
            return True
            
        except Exception as e:
            print(f" Processing failed: {e}")
            return False
    
    def run_nlp_phase(self, use_transformers: bool = True, use_bertopic: bool = True) -> bool:
        """
        Phase 3: Natural Language Processing analysis
        
        Args:
            use_transformers: Use transformer-based sentiment analysis
            use_bertopic: Use BERTopic for topic modeling
        
        Returns:
            True if successful, False otherwise
        """
        print("\n PHASE 3: NATURAL LANGUAGE PROCESSING")
        print("-" * 40)
        
        try:
            # Load merged reviews
            reviews_path = "data/processed/merged_reviews.csv"
            if not os.path.exists(reviews_path):
                print(f" Reviews file not found: {reviews_path}")
                return False
            
            reviews_df = pd.read_csv(reviews_path)
            print(f" Loaded {len(reviews_df)} reviews for NLP analysis")
            
            # Sentiment Analysis
            print("😊 Running sentiment analysis...")
            sentiment_analyzer = AdvancedSentimentAnalyzer(use_transformers=use_transformers)
            sentiment_df = sentiment_analyzer.compare_models(reviews_df)
            
            # Save sentiment results
            sentiment_output = "data/processed/reviews_with_sentiment.csv"
            sentiment_df.to_csv(sentiment_output, index=False, encoding='utf-8')
            print(f"✓ Sentiment analysis completed, saved to {sentiment_output}")
            
            # Topic Modeling
            print(" Running topic modeling...")
            topic_modeler = AdvancedTopicModeler(use_bertopic=use_bertopic, use_lda=True)
            
            # Train models
            texts = reviews_df['review_text'].fillna('').tolist()
            
            if use_bertopic:
                bertopic_results = topic_modeler.train_bertopic(texts, num_topics=8)
            
            lda_results = topic_modeler.train_lda(texts, num_topics=8)
            
            # Assign topics to documents
            topics_df = topic_modeler.assign_topics_to_documents(sentiment_df)
            
            # Save topic results
            topics_output = "data/processed/reviews_with_topics.csv"
            topics_df.to_csv(topics_output, index=False, encoding='utf-8')
            print(f"✓ Topic modeling completed, saved to {topics_output}")
            
            # Generate topic visualizations
            if use_bertopic or lda_results:
                print("📊 Generating topic visualizations...")
                topic_modeler.visualize_topics(save_path="data/analysis/topics")
            
            self.results['nlp'] = {
                'sentiment_models': ['VADER', 'TextBlob'] + (['Transformer'] if use_transformers else []),
                'topic_models': ['LDA'] + (['BERTopic'] if use_bertopic else []),
                'reviews_analyzed': len(topics_df)
            }
            
            return True
            
        except Exception as e:
            print(f" NLP analysis failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def run_statistical_phase(self) -> bool:
        """
        Phase 4: Statistical analysis and comparisons
        
        Returns:
            True if successful, False otherwise
        """
        print("\n PHASE 4: STATISTICAL ANALYSIS")
        print("-" * 40)
        
        try:
            # Load data with NLP results
            data_path = "data/processed/reviews_with_topics.csv"
            if not os.path.exists(data_path):
                print(f" Data file not found: {data_path}")
                return False
            
            data_df = pd.read_csv(data_path)
            print(f" Running statistical analysis on {len(data_df)} reviews")
            
            # Initialize statistical analyzer
            stat_analyzer = StatisticalAnalyzer()
            
            # Run comprehensive analysis
            output_path = "data/analysis/final_analysis.csv"
            stat_analyzer.save_analysis_results(
                data_df, output_path, 
                entity_col='entity', 
                sentiment_col='vader_compound'
            )
            
            # Generate and save report
            report = stat_analyzer.generate_statistical_report(
                data_df, 'entity', 'vader_compound'
            )
            
            report_path = "data/analysis/statistical_report.txt"
            with open(report_path, 'w') as f:
                f.write(report)
            
            print(f"✓ Statistical analysis completed")
            print(f"  Results: {output_path}")
            print(f"  Report: {report_path}")
            
            self.results['statistics'] = {
                'entities_analyzed': data_df['entity'].nunique(),
                'confidence_level': 0.95,
                'bootstrap_samples': 10000
            }
            
            return True
            
        except Exception as e:
            print(f" Statistical analysis failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def run_export_phase(self) -> bool:
        """
        Phase 5: Export final datasets and create Tableau-ready files
        
        Returns:
            True if successful, False otherwise
        """
        print("\n PHASE 5: EXPORT & FINAL PREPARATION")
        print("-" * 40)
        
        try:
            # Load final analysis data
            analysis_path = "data/analysis/final_analysis.csv"
            if not os.path.exists(analysis_path):
                print(f" Analysis file not found: {analysis_path}")
                return False
            
            analysis_df = pd.read_csv(analysis_path)

            # Derive Tableau-friendly features
            def sentiment_bucket(x: float) -> str:
                try:
                    if x > 0.05:
                        return 'Positive'
                    if x < -0.05:
                        return 'Negative'
                    return 'Neutral'
                except Exception:
                    return 'Neutral'

            def length_bucket(n: int) -> str:
                try:
                    if n < 200:
                        return 'Short (<200)'
                    if n < 800:
                        return 'Medium (200-800)'
                    if n < 2000:
                        return 'Long (800-2000)'
                    return 'Very Long (2000+)'
                except Exception:
                    return 'Unknown'

            # Ensure review_length exists
            if 'review_length' not in analysis_df.columns and 'review_text' in analysis_df.columns:
                analysis_df['review_length'] = analysis_df['review_text'].astype(str).str.len()

            # Buckets
            if 'vader_compound' in analysis_df.columns:
                analysis_df['sentiment_bucket'] = analysis_df['vader_compound'].apply(sentiment_bucket)
            analysis_df['review_length_bucket'] = analysis_df['review_length'].apply(length_bucket)

            # Keyword flags for Tableau filters
            def flag(pattern: str, text: str) -> int:
                try:
                    return 1 if re.search(pattern, text, flags=re.I) else 0
                except Exception:
                    return 0

            import re
            analysis_df['mentions_filler'] = analysis_df['review_text'].astype(str).apply(lambda t: flag(r'\bfiller(s)?\b', t))
            analysis_df['mentions_animation'] = analysis_df['review_text'].astype(str).apply(lambda t: flag(r'\banimation|animat(ed|ing|ion)\b', t))
            analysis_df['mentions_character'] = analysis_df['review_text'].astype(str).apply(lambda t: flag(r'\bcharacter(s)?\b', t))
            analysis_df['mentions_pacing'] = analysis_df['review_text'].astype(str).apply(lambda t: flag(r'\bpacing|slow|drag(s|ging)?\b', t))
            analysis_df['mentions_fight'] = analysis_df['review_text'].astype(str).apply(lambda t: flag(r'\bfight(s|ing)?|battle(s)?|combat\b', t))
            analysis_df['mentions_story'] = analysis_df['review_text'].astype(str).apply(lambda t: flag(r'\bstory|plot\b', t))
            analysis_df['mentions_world'] = analysis_df['review_text'].astype(str).apply(lambda t: flag(r'\bworld(-)?building\b', t))

            # Readability & linguistic features (lightweight)
            def tokenize(s: str) -> list:
                s = re.sub(r'[^A-Za-z0-9\s\.!?]', ' ', s)
                return [w for w in s.split() if w]

            def split_sentences(s: str) -> list:
                parts = re.split(r'[\.!?]+', s)
                return [p.strip() for p in parts if p.strip()]

            toks = analysis_df['review_text'].astype(str).apply(tokenize)
            sents = analysis_df['review_text'].astype(str).apply(split_sentences)
            analysis_df['tokens_count'] = toks.apply(len)
            analysis_df['sentences_count'] = sents.apply(len)
            analysis_df['avg_sentence_length'] = (analysis_df['tokens_count'] / analysis_df['sentences_count'].replace(0, 1)).round(2)
            analysis_df['unique_words_pct'] = toks.apply(lambda ts: (len(set([t.lower() for t in ts])) / max(1, len(ts)))).round(3)

            # Topic labels from guide (business-readable)
            topic_labels = {
                0: 'Bleach Fan Debates',
                1: 'One Piece Enthusiasm',
                2: 'Niche Criticisms',
                3: 'Universal Shonen Themes',
                4: 'Bleach Character Focus',
                5: 'Cross-Series Comparisons',
                6: 'Animation & Production',
                7: 'Franchise Legacy',
            }
            if 'lda_topic_id' in analysis_df.columns:
                def map_label(x):
                    try:
                        xi = int(x)
                        return topic_labels.get(xi, 'Unknown Topic')
                    except Exception:
                        return 'Unknown Topic'
                analysis_df['lda_topic_label'] = analysis_df['lda_topic_id'].apply(map_label)
            
            # Create final Tableau datasets
            print(" Creating final Tableau datasets...")
            
            # Reviews dataset
            keep_cols = [
                'entity', 'series_component', 'review_id', 'review_text', 'user_score',
                'recommendation', 'review_date', 'review_length', 'vader_compound',
                'sentiment_bucket', 'review_length_bucket', 'sentiment_residual',
                'residual_category', 'lda_topic_id', 'lda_topic_label', 'bertopic_topic_id',
                'mentions_filler', 'mentions_animation', 'mentions_character',
                'mentions_pacing', 'mentions_fight', 'mentions_story', 'mentions_world',
                'tokens_count', 'sentences_count', 'avg_sentence_length', 'unique_words_pct'
            ]
            keep_cols = [c for c in keep_cols if c in analysis_df.columns]
            tableau_reviews = analysis_df[keep_cols].copy()
            
            # Stats dataset (from merged stats)
            stats_path = "data/processed/merged_stats.csv"
            if os.path.exists(stats_path):
                stats_df = pd.read_csv(stats_path)
                tableau_stats = stats_df.copy()
            else:
                tableau_stats = pd.DataFrame()
            
            # Save final exports
            reviews_export = "data/exports/tableau_reviews_final.csv"
            stats_export = "data/exports/tableau_stats_final.csv"
            
            tableau_reviews.to_csv(reviews_export, index=False, encoding='utf-8')
            if not tableau_stats.empty:
                tableau_stats.to_csv(stats_export, index=False, encoding='utf-8')
            
            print(f"✓ Final exports created:")
            print(f"  Reviews: {reviews_export}")
            if not tableau_stats.empty:
                print(f"  Stats: {stats_export}")
            
            # Additional aggregated exports for Tableau
            print(" Creating KPI and topic summary datasets...")
            kpi = []
            if 'entity' in analysis_df.columns and 'vader_compound' in analysis_df.columns:
                for ent, g in analysis_df.groupby('entity'):
                    kpi.append({
                        'entity': ent,
                        'num_reviews': int(len(g)),
                        'mean_vader': float(g['vader_compound'].mean()),
                        'median_vader': float(g['vader_compound'].median()),
                        'std_vader': float(g['vader_compound'].std()),
                        'positive_pct': float((g['vader_compound'] > 0.05).mean()),
                        'negative_pct': float((g['vader_compound'] < -0.05).mean()),
                    })
            kpi_df = pd.DataFrame(kpi)
            kpi_export = "data/exports/tableau_kpis.csv"
            if not kpi_df.empty:
                kpi_df.to_csv(kpi_export, index=False, encoding='utf-8')

            topics_summary_export = "data/exports/tableau_topics_by_entity.csv"
            if 'entity' in analysis_df.columns and 'lda_topic_id' in analysis_df.columns:
                topics_summary = (
                    analysis_df.dropna(subset=['lda_topic_id'])
                    .groupby(['entity', 'lda_topic_id', 'lda_topic_label']).size().reset_index(name='num_reviews')
                )
                if not topics_summary.empty:
                    topics_summary.to_csv(topics_summary_export, index=False, encoding='utf-8')

            # Topic impact metrics (mean sentiment per topic × entity)
            topic_impact_export = "data/exports/tableau_topic_impact.csv"
            if {'entity', 'lda_topic_id', 'vader_compound'}.issubset(analysis_df.columns):
                topic_impact = (
                    analysis_df.dropna(subset=['lda_topic_id'])
                    .groupby(['entity', 'lda_topic_id', 'lda_topic_label'])
                    .agg(
                        num_reviews=('vader_compound', 'size'),
                        mean_vader=('vader_compound', 'mean'),
                        median_vader=('vader_compound', 'median')
                    )
                    .reset_index()
                )
                if not topic_impact.empty:
                    topic_impact.to_csv(topic_impact_export, index=False, encoding='utf-8')

            # Overrated/underrated index by entity (residuals)
            overrated_export = "data/exports/tableau_overrated_index.csv"
            if {'entity', 'sentiment_residual', 'residual_category', 'sentiment_residual_abs'}.issubset(analysis_df.columns):
                base_idx = (
                    analysis_df.groupby('entity')
                    .agg(
                        residual_mean=('sentiment_residual', 'mean'),
                        residual_abs_mean=('sentiment_residual_abs', 'mean')
                    )
                    .reset_index()
                )
                high_share = (
                    analysis_df
                    .assign(_high=lambda d: d['residual_category'].isin(['High', 'Very High']).astype(float))
                    .groupby('entity')['_high'].mean()
                    .reset_index(name='high_share')
                )
                over_idx = base_idx.merge(high_share, on='entity', how='left')
                if not over_idx.empty:
                    over_idx.to_csv(overrated_export, index=False, encoding='utf-8')

            # Aspect sentiment pivots and lifts
            aspects = [
                ('filler', 'mentions_filler'),
                ('animation', 'mentions_animation'),
                ('character', 'mentions_character'),
                ('pacing', 'mentions_pacing'),
                ('fight', 'mentions_fight'),
                ('story', 'mentions_story'),
                ('world', 'mentions_world'),
            ]

            if 'vader_compound' in analysis_df.columns and 'entity' in analysis_df.columns:
                # Aspect sentiment per entity
                rows = []
                for aspect_name, col in aspects:
                    if col not in analysis_df.columns:
                        continue
                    sub = analysis_df[analysis_df[col] == 1]
                    if sub.empty:
                        continue
                    grp = sub.groupby('entity')['vader_compound'].agg(['count', 'mean', 'median']).reset_index()
                    for _, r in grp.iterrows():
                        rows.append({
                            'entity': r['entity'],
                            'aspect': aspect_name,
                            'num_reviews': int(r['count']),
                            'mean_vader': float(r['mean']),
                            'median_vader': float(r['median'])
                        })
                aspect_export = "data/exports/tableau_aspect_sentiment.csv"
                if rows:
                    pd.DataFrame(rows).to_csv(aspect_export, index=False, encoding='utf-8')

                # Aspect lift (difference if mentioned vs not) per entity
                lift_rows = []
                for aspect_name, col in aspects:
                    if col not in analysis_df.columns:
                        continue
                    for ent, g in analysis_df.groupby('entity'):
                        if len(g) < 5:
                            continue
                        with_aspect = g[g[col] == 1]['vader_compound']
                        without_aspect = g[g[col] == 0]['vader_compound']
                        if len(with_aspect) >= 5 and len(without_aspect) >= 5:
                            lift = float(with_aspect.mean() - without_aspect.mean())
                            lift_rows.append({
                                'entity': ent,
                                'aspect': aspect_name,
                                'lift_mean_vader': lift,
                                'with_n': int(len(with_aspect)),
                                'without_n': int(len(without_aspect))
                            })
                aspect_lift_export = "data/exports/tableau_aspect_lift.csv"
                if lift_rows:
                    pd.DataFrame(lift_rows).to_csv(aspect_lift_export, index=False, encoding='utf-8')

            # Create data dictionary
            self._create_data_dictionary(tableau_reviews, tableau_stats)
            
            self.results['export'] = {
                'reviews_exported': len(tableau_reviews),
                'stats_exported': len(tableau_stats) if not tableau_stats.empty else 0
            }
            
            return True
            
        except Exception as e:
            print(f" Export failed: {e}")
            return False
    
    def _create_data_dictionary(self, reviews_df: pd.DataFrame, stats_df: pd.DataFrame):
        """Create comprehensive data dictionary"""
        print("📚 Creating data dictionary...")
        
        dictionary = []
        dictionary.append("# Big Three Anime NLP - Data Dictionary")
        dictionary.append("")
        dictionary.append("## Reviews Dataset (tableau_reviews_final.csv)")
        dictionary.append("")
        
        for col in reviews_df.columns:
            description = self._get_column_description(col)
            dictionary.append(f"### {col}")
            dictionary.append(f"- **Type**: {reviews_df[col].dtype}")
            dictionary.append(f"- **Description**: {description}")
            dictionary.append(f"- **Sample Values**: {str(reviews_df[col].dropna().head(3).tolist())}")
            dictionary.append("")
        
        if not stats_df.empty:
            dictionary.append("## Statistics Dataset (tableau_stats_final.csv)")
            dictionary.append("")
            
            for col in stats_df.columns:
                description = self._get_column_description(col)
                dictionary.append(f"### {col}")
                dictionary.append(f"- **Type**: {stats_df[col].dtype}")
                dictionary.append(f"- **Description**: {description}")
                dictionary.append(f"- **Sample Values**: {str(stats_df[col].dropna().head(3).tolist())}")
                dictionary.append("")
        
        # Save dictionary
        dict_path = "data/exports/data_dictionary.md"
        with open(dict_path, 'w') as f:
            f.write('\n'.join(dictionary))
        
        print(f"✓ Data dictionary created: {dict_path}")
    
    def _get_column_description(self, column_name: str) -> str:
        """Get human-readable description for a column"""
        descriptions = {
            'entity': 'Combined anime entity (Naruto, One Piece, or Bleach)',
            'series_component': 'Individual series within the entity',
            'review_id': 'Unique identifier for each review',
            'review_text': 'Full text content of the review',
            'user_score': 'User rating from 1-10',
            'recommendation': 'Reviewer tag: Recommended / Mixed Feelings / Not Recommended',
            'review_date': 'Date when review was posted',
            'review_length': 'Character count of review text',
            'vader_compound': 'VADER sentiment compound score (-1 to 1)',
            'textblob_polarity': 'TextBlob polarity score (-1 to 1)',
            'textblob_subjectivity': 'TextBlob subjectivity score (0 to 1)',
            'lda_topic_id': 'LDA topic assignment ID',
            'bertopic_topic_id': 'BERTopic topic assignment ID',
            'combined_mean_score': 'Weighted average score from score distribution',
            'members': 'Total number of MAL members',
            'favorites': 'Total number of favorites',
            'sentiment_bucket': 'Categorized sentiment based on VADER compound: Positive/Neutral/Negative',
            'review_length_bucket': 'Binned review length: Short/Medium/Long/Very Long',
            'sentiment_residual': 'Difference between text sentiment and normalized user score',
            'residual_category': 'Binned absolute residual: Low/Medium/High/Very High',
            'mentions_filler': 'Flag if review mentions filler episodes',
            'mentions_animation': 'Flag if review mentions animation/visuals',
            'mentions_character': 'Flag if review mentions characters',
            'mentions_pacing': 'Flag if review mentions pacing/slow/dragging',
            'mentions_fight': 'Flag if review mentions fights/battles/combat',
            'mentions_story': 'Flag if review mentions story/plot',
            'mentions_world': 'Flag if review mentions world-building'
        }
        
        return descriptions.get(column_name, 'No description available')
    
    def _check_existing_data(self) -> bool:
        """Check if data already exists from previous runs"""
        required_files = [
            "data/raw/all_reviews_raw.csv",
            "data/raw/all_stats_raw.csv"
        ]
        
        return all(os.path.exists(f) for f in required_files)
    
    def generate_pipeline_report(self) -> str:
        """Generate comprehensive pipeline execution report"""
        report = []
        report.append("=" * 80)
        report.append("BIG THREE ANIME NLP PIPELINE EXECUTION REPORT")
        report.append("=" * 80)
        report.append(f"Execution Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Pipeline ID: {self.timestamp}")
        report.append("")
        
        # Summary
        report.append("## EXECUTION SUMMARY")
        report.append("-" * 20)
        
        total_phases = 5
        successful_phases = sum(1 for phase in ['scraping', 'processing', 'nlp', 'statistics', 'export'] 
                              if phase in self.results)
        
        report.append(f"Phases Completed: {successful_phases}/{total_phases}")
        report.append(f"Overall Status: {'✅ SUCCESS' if successful_phases == total_phases else '⚠️ PARTIAL'}")
        report.append("")
        
        # Phase details
        for phase_name in ['scraping', 'processing', 'nlp', 'statistics', 'export']:
            report.append(f"## PHASE: {phase_name.upper()}")
            report.append("-" * (len(phase_name) + 8))
            
            if phase_name in self.results:
                phase_results = self.results[phase_name]
                for key, value in phase_results.items():
                    report.append(f"- **{key}**: {value}")
                report.append(" COMPLETED")
            else:
                report.append(" NOT COMPLETED")
            report.append("")
        
        # File outputs
        report.append("## OUTPUT FILES")
        report.append("-" * 15)
        
        output_files = [
            "data/processed/merged_reviews.csv",
            "data/processed/merged_stats.csv", 
            "data/analysis/final_analysis.csv",
            "data/exports/tableau_reviews_final.csv",
            "data/exports/tableau_stats_final.csv",
            "data/exports/data_dictionary.md"
        ]
        
        for file_path in output_files:
            if os.path.exists(file_path):
                size = os.path.getsize(file_path) / 1024  # KB
                report.append(f" {file_path} ({size:.1f} KB)")
            else:
                report.append(f" {file_path} (missing)")
        
        report.append("")
        report.append("=" * 80)
        
        return '\n'.join(report)
    
    def run_full_pipeline(self, force_scrape: bool = False, 
                          use_transformers: bool = True, 
                          use_bertopic: bool = True) -> bool:
        """
        Run the complete pipeline end-to-end
        
        Args:
            force_scrape: Force re-scraping of data
            use_transformers: Use transformer sentiment analysis
            use_bertopic: Use BERTopic for topic modeling
        
        Returns:
            True if all phases successful, False otherwise
        """
        print(" Starting Big Three Anime NLP Pipeline")
        print("=" * 60)
        
        phases = [
            ("Scraping", lambda: self.run_scraping_phase(force_scrape)),
            ("Processing", self.run_processing_phase),
            ("NLP Analysis", lambda: self.run_nlp_phase(use_transformers, use_bertopic)),
            ("Statistical Analysis", self.run_statistical_phase),
            ("Export", self.run_export_phase)
        ]
        
        successful_phases = 0
        
        for phase_name, phase_func in phases:
            try:
                print(f"\n Running {phase_name} phase...")
                if phase_func():
                    successful_phases += 1
                    print(f" {phase_name} phase completed successfully")
                else:
                    print(f" {phase_name} phase failed")
                    break
            except Exception as e:
                print(f" {phase_name} phase failed with error: {e}")
                break
        
        # Generate final report
        print("\n Generating pipeline report...")
        report = self.generate_pipeline_report()
        
        report_path = f"reports/pipeline_report_{self.timestamp}.txt"
        with open(report_path, 'w') as f:
            f.write(report)
        
        print(f" Pipeline report saved to: {report_path}")
        
        # Final status
        if successful_phases == len(phases):
            print("\n🎉 PIPELINE COMPLETED SUCCESSFULLY!")
            print("=" * 60)
            print("Next steps:")
            print("1. Review the generated datasets in data/exports/")
            print("2. Import tableau_reviews_final.csv and tableau_stats_final.csv into Tableau")
            print("3. Create your dashboard using the data dictionary as reference")
            print("4. Check the analysis results in data/analysis/")
        else:
            print(f"\n PIPELINE COMPLETED WITH {len(phases) - successful_phases} FAILED PHASES")
        
        return successful_phases == len(phases)


def main():
    """Main function for command-line usage"""
    parser = argparse.ArgumentParser(description='Big Three Anime NLP Pipeline')
    parser.add_argument('--force-scrape', action='store_true', 
                       help='Force re-scraping of data')
    parser.add_argument('--no-transformers', action='store_true',
                       help='Skip transformer-based sentiment analysis')
    parser.add_argument('--no-bertopic', action='store_true',
                       help='Skip BERTopic topic modeling')
    parser.add_argument('--config', default='config.yml',
                       help='Path to configuration file')
    
    args = parser.parse_args()
    
    # Initialize pipeline
    pipeline = AnimeAnalysisPipeline(args.config)
    
    # Run pipeline
    success = pipeline.run_full_pipeline(
        force_scrape=args.force_scrape,
        use_transformers=not args.no_transformers,
        use_bertopic=not args.no_bertopic
    )
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    # Import pandas here to avoid circular imports
    import pandas as pd
    main() 