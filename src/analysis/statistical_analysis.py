"""
Statistical Analysis for Big Three Anime Reviews
Provides rigorous statistical comparisons with confidence intervals, effect sizes, and nonparametric tests
"""

import os
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import warnings
from scipy import stats
from scipy.stats import bootstrap
import statsmodels.stats.multicomp as mc
from statsmodels.stats.multitest import multipletests

class StatisticalAnalyzer:
    """
    Comprehensive statistical analysis for anime review comparisons
    """
    
    def __init__(self):
        self.results = {}
        print("✓ Statistical analyzer initialized")
    
    def bootstrap_confidence_interval(self, data: pd.Series, statistic: str = 'mean', 
                                   confidence_level: float = 0.95, n_bootstrap: int = 10000) -> Dict:
        """
        Calculate bootstrap confidence intervals for various statistics
        
        Args:
            data: Series of numerical data
            statistic: 'mean', 'median', 'std', or custom function
            confidence_level: Confidence level (e.g., 0.95 for 95%)
            n_bootstrap: Number of bootstrap samples
        
        Returns:
            Dictionary with confidence interval bounds and point estimate
        """
        if len(data) < 10:
            warnings.warn(f"Insufficient data for bootstrap: {len(data)} samples")
            return {}
        
        try:
            # Define statistic function
            if statistic == 'mean':
                stat_func = np.mean
            elif statistic == 'median':
                stat_func = np.median
            elif statistic == 'std':
                stat_func = np.std
            else:
                stat_func = statistic
            
            # Calculate bootstrap confidence interval
            bootstrap_result = bootstrap(
                (data,), stat_func, confidence_level=confidence_level, 
                n_resamples=n_bootstrap, random_state=42
            )
            
            # Extract results
            ci_lower, ci_upper = bootstrap_result.confidence_interval
            point_estimate = stat_func(data)
            
            return {
                'statistic': statistic,
                'point_estimate': point_estimate,
                'ci_lower': ci_lower,
                'ci_upper': ci_upper,
                'confidence_level': confidence_level,
                'n_bootstrap': n_bootstrap,
                'n_samples': len(data)
            }
            
        except Exception as e:
            warnings.warn(f"Bootstrap failed: {e}")
            return {}
    
    def effect_size_cliffs_delta(self, group1: pd.Series, group2: pd.Series) -> Dict:
        """
        Calculate Cliff's Delta effect size (nonparametric alternative to Cohen's d)
        
        Args:
            group1: First group data
            group2: Second group data
        
        Returns:
            Dictionary with effect size and interpretation
        """
        try:
            # Calculate Cliff's Delta
            n1, n2 = len(group1), len(group2)
            
            # Count wins for each group
            wins1 = 0
            wins2 = 0
            ties = 0
            
            for x in group1:
                for y in group2:
                    if x > y:
                        wins1 += 1
                    elif x < y:
                        wins2 += 1
                    else:
                        ties += 1
            
            total = n1 * n2
            delta = (wins1 - wins2) / total
            
            # Interpret effect size
            if abs(delta) < 0.147:
                interpretation = "negligible"
            elif abs(delta) < 0.33:
                interpretation = "small"
            elif abs(delta) < 0.474:
                interpretation = "medium"
            else:
                interpretation = "large"
            
            return {
                'cliffs_delta': delta,
                'interpretation': interpretation,
                'wins_group1': wins1,
                'wins_group2': wins2,
                'ties': ties,
                'total_comparisons': total,
                'n1': n1,
                'n2': n2
            }
            
        except Exception as e:
            warnings.warn(f"Cliff's Delta calculation failed: {e}")
            return {}
    
    def nonparametric_comparison(self, data: pd.DataFrame, value_col: str, 
                                group_col: str, test_type: str = 'kruskal') -> Dict:
        """
        Perform nonparametric statistical tests for group comparisons
        
        Args:
            data: DataFrame with data
            value_col: Column name for numerical values
            group_col: Column name for group labels
            test_type: 'kruskal' (Kruskal-Wallis) or 'mannwhitney' (Mann-Whitney U)
        
        Returns:
            Dictionary with test results and post-hoc analysis
        """
        try:
            # Group data
            groups = data.groupby(group_col)[value_col].apply(list)
            group_names = list(groups.keys())
            
            if len(group_names) < 2:
                warnings.warn("Need at least 2 groups for comparison")
                return {}
            
            # Perform main test
            if test_type == 'kruskal' and len(group_names) > 2:
                # Kruskal-Wallis H-test for multiple groups
                stat, p_value = stats.kruskal(*groups.values)
                test_name = "Kruskal-Wallis H-test"
                
            elif test_type == 'mannwhitney' or len(group_names) == 2:
                # Mann-Whitney U-test for two groups
                stat, p_value = stats.mannwhitneyu(groups.iloc[0], groups.iloc[1], alternative='two-sided')
                test_name = "Mann-Whitney U-test"
                
            else:
                warnings.warn(f"Invalid test type '{test_type}' for {len(group_names)} groups")
                return {}
            
            # Calculate effect sizes for each pair
            effect_sizes = {}
            for i, name1 in enumerate(group_names):
                for j, name2 in enumerate(group_names):
                    if i < j:
                        pair_key = f"{name1}_vs_{name2}"
                        effect_sizes[pair_key] = self.effect_size_cliffs_delta(
                            pd.Series(groups[name1]), pd.Series(groups[name2])
                        )
            
            # Post-hoc analysis for multiple groups
            post_hoc = {}
            if len(group_names) > 2 and p_value < 0.05:
                try:
                    # Dunn's test for multiple comparisons
                    dunn_result = mc.MultiComparison(data[value_col], data[group_col])
                    dunn_table = dunn_result.dunn_test()
                    post_hoc['dunn_test'] = dunn_table.pvalues.to_dict()
                except Exception as e:
                    warnings.warn(f"Post-hoc analysis failed: {e}")
            
            return {
                'test_name': test_name,
                'statistic': stat,
                'p_value': p_value,
                'significant': p_value < 0.05,
                'alpha': 0.05,
                'n_groups': len(group_names),
                'group_names': group_names,
                'effect_sizes': effect_sizes,
                'post_hoc': post_hoc
            }
            
        except Exception as e:
            warnings.warn(f"Nonparametric comparison failed: {e}")
            return {}
    
    def sentiment_score_residuals(self, df: pd.DataFrame, sentiment_col: str = 'vader_compound',
                                score_col: str = 'user_score') -> pd.DataFrame:
        """
        Calculate residuals between text sentiment and user scores
        
        Args:
            df: DataFrame with sentiment and score data
            sentiment_col: Column name for sentiment scores
            score_col: Column name for user scores
        
        Returns:
            DataFrame with additional residual columns
        """
        result_df = df.copy()
        
        # Normalize user scores to [-1, 1] scale to match sentiment
        if score_col in result_df.columns and sentiment_col in result_df.columns:
            # Convert 1-10 scale to -1 to 1 scale
            normalized_scores = (result_df[score_col] - 5.5) / 4.5
            
            # Calculate residuals
            result_df['sentiment_residual'] = result_df[sentiment_col] - normalized_scores
            result_df['sentiment_residual_abs'] = abs(result_df['sentiment_residual'])
            
            # Categorize residuals
            result_df['residual_category'] = pd.cut(
                result_df['sentiment_residual_abs'],
                bins=[0, 0.2, 0.5, 1.0, np.inf],
                labels=['Low', 'Medium', 'High', 'Very High'],
                include_lowest=True
            )
        
        return result_df
    
    def analyze_entity_comparisons(self, df: pd.DataFrame, entity_col: str = 'entity',
                                 sentiment_col: str = 'vader_compound') -> Dict:
        """
        Comprehensive analysis comparing entities across multiple metrics
        
        Args:
            df: DataFrame with entity and sentiment data
            entity_col: Column name for entity labels
            sentiment_col: Column name for sentiment scores
        
        Returns:
            Dictionary with comprehensive comparison results
        """
        results = {}
        
        # Basic statistics by entity
        entity_stats = df.groupby(entity_col)[sentiment_col].agg([
            'count', 'mean', 'std', 'median', 'min', 'max'
        ]).round(4)
        
        results['entity_statistics'] = entity_stats.to_dict('index')
        
        # Bootstrap confidence intervals for each entity
        bootstrap_cis = {}
        for entity in df[entity_col].unique():
            entity_data = df[df[entity_col] == entity][sentiment_col].dropna()
            if len(entity_data) >= 10:
                bootstrap_cis[entity] = self.bootstrap_confidence_interval(
                    entity_data, statistic='mean', confidence_level=0.95
                )
        
        results['bootstrap_confidence_intervals'] = bootstrap_cis
        
        # Nonparametric comparison across entities
        comparison_result = self.nonparametric_comparison(
            df, sentiment_col, entity_col, test_type='kruskal'
        )
        results['group_comparison'] = comparison_result
        
        # Effect sizes between entity pairs
        entity_pairs = []
        entities = df[entity_col].unique()
        for i, entity1 in enumerate(entities):
            for j, entity2 in enumerate(entities):
                if i < j:
                    data1 = df[df[entity_col] == entity1][sentiment_col].dropna()
                    data2 = df[df[entity_col] == entity2][sentiment_col].dropna()
                    
                    if len(data1) >= 5 and len(data2) >= 5:
                        effect_size = self.effect_size_cliffs_delta(data1, data2)
                        entity_pairs.append({
                            'entity1': entity1,
                            'entity2': entity2,
                            'effect_size': effect_size
                        })
        
        results['entity_pair_effects'] = entity_pairs
        
        return results
    
    def generate_statistical_report(self, df: pd.DataFrame, entity_col: str = 'entity',
                                  sentiment_col: str = 'vader_compound') -> str:
        """
        Generate a human-readable statistical report
        
        Args:
            df: DataFrame with analysis data
            entity_col: Column name for entity labels
            sentiment_col: Column name for sentiment scores
        
        Returns:
            Formatted statistical report string
        """
        # Run comprehensive analysis
        analysis = self.analyze_entity_comparisons(df, entity_col, sentiment_col)
        
        report = []
        report.append("=" * 60)
        report.append("STATISTICAL ANALYSIS REPORT")
        report.append("=" * 60)
        report.append("")
        
        # Entity statistics
        report.append("ENTITY STATISTICS:")
        report.append("-" * 20)
        for entity, stats in analysis['entity_statistics'].items():
            report.append(f"{entity}:")
            report.append(f"  Count: {stats['count']}")
            report.append(f"  Mean: {stats['mean']:.4f}")
            report.append(f"  Std: {stats['std']:.4f}")
            report.append(f"  95% CI: [{analysis['bootstrap_confidence_intervals'].get(entity, {}).get('ci_lower', 'N/A'):.4f}, "
                        f"{analysis['bootstrap_confidence_intervals'].get(entity, {}).get('ci_upper', 'N/A'):.4f}]")
            report.append("")
        
        # Group comparison results
        if 'group_comparison' in analysis and analysis['group_comparison']:
            comp = analysis['group_comparison']
            report.append("GROUP COMPARISON:")
            report.append("-" * 20)
            report.append(f"Test: {comp['test_name']}")
            report.append(f"Statistic: {comp['statistic']:.4f}")
            report.append(f"P-value: {comp['p_value']:.6f}")
            report.append(f"Significant: {'Yes' if comp['significant'] else 'No'}")
            report.append("")
        
        # Effect sizes
        if 'entity_pair_effects' in analysis:
            report.append("EFFECT SIZES (Cliff's Delta):")
            report.append("-" * 30)
            for pair in analysis['entity_pair_effects']:
                if 'effect_size' in pair and pair['effect_size']:
                    effect = pair['effect_size']
                    report.append(f"{pair['entity1']} vs {pair['entity2']}:")
                    report.append(f"  Delta: {effect['cliffs_delta']:.4f} ({effect['interpretation']})")
                    report.append("")
        
        report.append("=" * 60)
        return "\n".join(report)
    
    def save_analysis_results(self, df: pd.DataFrame, output_path: str,
                             entity_col: str = 'entity', sentiment_col: str = 'vader_compound'):
        """
        Save comprehensive analysis results to files
        
        Args:
            df: DataFrame with analysis data
            output_path: Base path for output files
            entity_col: Column name for entity labels
            sentiment_col: Column name for sentiment scores
        """
        # Generate analysis
        analysis = self.analyze_entity_comparisons(df, entity_col, sentiment_col)
        
        # Save detailed results as JSON
        import json
        json_path = output_path.replace('.csv', '_statistical_analysis.json')
        with open(json_path, 'w') as f:
            json.dump(analysis, f, indent=2, default=str)
        print(f"✓ Statistical analysis saved to {json_path}")
        
        # Save statistical report as text
        report = self.generate_statistical_report(df, entity_col, sentiment_col)
        report_path = output_path.replace('.csv', '_statistical_report.txt')
        with open(report_path, 'w') as f:
            f.write(report)
        print(f"✓ Statistical report saved to {report_path}")
        
        # Add residual analysis to DataFrame
        result_df = self.sentiment_score_residuals(df, sentiment_col)
        
        # Save enhanced DataFrame
        result_df.to_csv(output_path, index=False, encoding='utf-8')
        print(f"✓ Enhanced data with residuals saved to {output_path}")


def main():
    """Main function for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Statistical analysis for anime reviews')
    parser.add_argument('input', help='Input CSV file path')
    parser.add_argument('output', help='Output CSV file path')
    parser.add_argument('--entity-col', default='entity', help='Column name for entity labels')
    parser.add_argument('--sentiment-col', default='vader_compound', help='Column name for sentiment scores')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"Error: Input file {args.input} not found")
        return
    
    # Load data
    print(f"Loading data from {args.input}")
    df = pd.read_csv(args.input)
    
    # Initialize analyzer
    analyzer = StatisticalAnalyzer()
    
    # Run analysis and save results
    analyzer.save_analysis_results(
        df, args.output, args.entity_col, args.sentiment_col
    )
    
    # Print summary report
    report = analyzer.generate_statistical_report(df, args.entity_col, args.sentiment_col)
    print("\n" + report)


if __name__ == "__main__":
    main() 