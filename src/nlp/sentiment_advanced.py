"""
Advanced Sentiment Analysis for Big Three Anime Reviews
Combines VADER baseline with transformer-based sentiment for credibility
"""

import os
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from textblob import TextBlob
import warnings

# Optional transformer imports for advanced analysis
try:
    from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
    TRANSFORMER_AVAILABLE = True
except ImportError:
    TRANSFORMER_AVAILABLE = False
    warnings.warn("Transformers not available. Install with: pip install transformers torch")

class AdvancedSentimentAnalyzer:
    """
    Multi-model sentiment analysis with statistical comparison
    """
    
    def __init__(self, use_transformers: bool = True):
        self.vader = SentimentIntensityAnalyzer()
        self.use_transformers = use_transformers and TRANSFORMER_AVAILABLE
        
        if self.use_transformers:
            try:
                # Use a robust sentiment model
                self.transformer_pipeline = pipeline(
                    "sentiment-analysis",
                    model="cardiffnlp/twitter-roberta-base-sentiment-latest",
                    return_all_scores=True
                )
                print("✓ Transformer sentiment model loaded")
            except Exception as e:
                print(f"⚠ Transformer model failed to load: {e}")
                self.use_transformers = False
        
        # Sentiment mapping for transformer output
        self.sentiment_mapping = {
            'LABEL_0': 'negative',
            'LABEL_1': 'neutral', 
            'LABEL_2': 'positive'
        }
    
    def analyze_vader(self, text: str) -> Dict[str, float]:
        """VADER sentiment analysis"""
        scores = self.vader.polarity_scores(text)
        return {
            'vader_pos': scores['pos'],
            'vader_neu': scores['neu'],
            'vader_neg': scores['neg'],
            'vader_compound': scores['compound']
        }
    
    def analyze_textblob(self, text: str) -> Dict[str, float]:
        """TextBlob sentiment analysis as additional baseline"""
        blob = TextBlob(text)
        return {
            'textblob_polarity': blob.sentiment.polarity,
            'textblob_subjectivity': blob.sentiment.subjectivity
        }
    
    def analyze_transformer(self, text: str) -> Optional[Dict[str, float]]:
        """Transformer-based sentiment analysis"""
        if not self.use_transformers:
            return None
            
        try:
            # Truncate very long texts to avoid token limits
            if len(text) > 500:
                text = text[:500]
            
            results = self.transformer_pipeline(text)
            
            # Extract scores for each label
            scores = {}
            for result in results:
                label = result['label']
                score = result['score']
                sentiment = self.sentiment_mapping.get(label, label)
                scores[f'transformer_{sentiment}'] = score
            
            return scores
            
        except Exception as e:
            print(f"Transformer analysis failed for text: {e}")
            return None
    
    def analyze_text(self, text: str) -> Dict[str, float]:
        """Complete sentiment analysis with all available models"""
        results = {}
        
        # VADER (baseline)
        results.update(self.analyze_vader(text))
        
        # TextBlob (additional baseline)
        results.update(self.analyze_textblob(text))
        
        # Transformer (advanced)
        if self.use_transformers:
            transformer_results = self.analyze_transformer(text)
            if transformer_results:
                results.update(transformer_results)
        
        return results
    
    def compare_models(self, df: pd.DataFrame, text_col: str = 'review_text') -> pd.DataFrame:
        """
        Compare sentiment across different models and add comparison metrics
        """
        print("Running multi-model sentiment analysis...")
        
        # Apply sentiment analysis
        sentiment_results = df[text_col].fillna('').astype(str).apply(self.analyze_text)
        
        # Convert to DataFrame
        sentiment_df = pd.DataFrame(sentiment_results.tolist())
        
        # Combine with original data
        result_df = pd.concat([df, sentiment_df], axis=1)
        
        # Add comparison metrics if transformer is available
        if self.use_transformers and 'transformer_positive' in result_df.columns:
            # Sentiment agreement between VADER and Transformer
            result_df['sentiment_agreement'] = np.where(
                (result_df['vader_compound'] > 0) == (result_df['transformer_positive'] > result_df['transformer_negative']),
                1, 0
            )
            
            # Sentiment intensity difference
            result_df['sentiment_intensity_diff'] = abs(
                result_df['vader_compound'] - (result_df['transformer_positive'] - result_df['transformer_negative'])
            )
        
        return result_df
    
    def generate_sentiment_summary(self, df: pd.DataFrame) -> Dict:
        """Generate comprehensive sentiment summary statistics"""
        summary = {}
        
        # VADER summary
        if 'vader_compound' in df.columns:
            summary['vader'] = {
                'mean_compound': df['vader_compound'].mean(),
                'std_compound': df['vader_compound'].std(),
                'positive_pct': (df['vader_compound'] > 0.05).mean(),
                'negative_pct': (df['vader_compound'] < -0.05).mean(),
                'neutral_pct': ((df['vader_compound'] >= -0.05) & (df['vader_compound'] <= 0.05)).mean()
            }
        
        # Transformer summary
        if 'transformer_positive' in df.columns:
            summary['transformer'] = {
                'mean_positive': df['transformer_positive'].mean(),
                'mean_negative': df['transformer_negative'].mean(),
                'mean_neutral': df['transformer_neutral'].mean(),
                'positive_pct': (df['transformer_positive'] > df['transformer_negative']).mean(),
                'negative_pct': (df['transformer_negative'] > df['transformer_positive']).mean()
            }
        
        # Model comparison
        if 'sentiment_agreement' in df.columns:
            summary['model_comparison'] = {
                'agreement_rate': df['sentiment_agreement'].mean(),
                'mean_intensity_diff': df['sentiment_intensity_diff'].mean()
            }
        
        return summary


def main():
    """Main function for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Advanced sentiment analysis for anime reviews')
    parser.add_argument('input', help='Input CSV file path')
    parser.add_argument('output', help='Output CSV file path')
    parser.add_argument('--use-transformers', action='store_true', 
                       help='Use transformer models (requires more memory)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"Error: Input file {args.input} not found")
        return
    
    # Load data
    print(f"Loading data from {args.input}")
    df = pd.read_csv(args.input)
    
    # Initialize analyzer
    analyzer = AdvancedSentimentAnalyzer(use_transformers=args.use_transformers)
    
    # Run analysis
    result_df = analyzer.compare_models(df)
    
    # Generate summary
    summary = analyzer.generate_sentiment_summary(result_df)
    print("\nSentiment Summary:")
    for model, stats in summary.items():
        print(f"\n{model.upper()}:")
        for metric, value in stats.items():
            print(f"  {metric}: {value:.4f}")
    
    # Save results
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    result_df.to_csv(args.output, index=False, encoding='utf-8')
    print(f"\nResults saved to {args.output}")
    print(f"Total reviews analyzed: {len(result_df)}")


if __name__ == "__main__":
    main() 