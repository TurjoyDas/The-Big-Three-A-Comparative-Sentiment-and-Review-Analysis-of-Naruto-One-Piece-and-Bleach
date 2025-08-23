"""
Data Processing and Merging for Big Three Anime Reviews
- Merge reviews into combined entities
- Merge stats (percent histograms + status counts) with proper weighting
- Create Tableau-friendly exports
"""

import os
import re
from typing import Dict, List
import yaml
import numpy as np
import pandas as pd


# ---------------------------
# Merger
# ---------------------------

class AnimeDataMerger:
    def __init__(self, config_path: str = "config.yml"):
        self.config = self._load_config(config_path)
        self.entity_mapping = self._build_entity_mapping()
        self.filename_mapping = self._build_filename_mapping()
        print("✓ Data merger initialized")

    # ---------- config & mappings ----------

    def _load_config(self, config_path: str) -> Dict:
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"⚠ Failed to load config: {e}")
            return {}

    def _build_entity_mapping(self) -> Dict[str, str]:
        """from config.yml entities list"""
        mapping = {}
        for e in self.config.get("entities", []):
            mapping[e["series_component"]] = e["entity"]
        return mapping

    def _build_filename_mapping(self) -> Dict[str, str]:
        """filename (without suffix) -> combined entity"""
        return {
            "naruto": "Naruto (combined)",
            "naruto_shippuden": "Naruto (combined)",
            "one_piece": "One Piece",
            "bleach": "Bleach (combined)",
            "bleach_tybw_part_1": "Bleach (combined)",
            "bleach_tybw_part_2": "Bleach (combined)",
        }

    # ---------- reviews ----------

    def merge_reviews_data(self, reviews_dir: str, output_path: str) -> pd.DataFrame:
        """
        Merge review CSVs into a single file with combined entity labels.
        Expects files like *_reviews_raw.csv written by the Selenium scraper.
        """
        print("Merging reviews data...")
        all_reviews: List[pd.DataFrame] = []

        if not os.path.isdir(reviews_dir):
            print(f"⚠ Reviews directory not found: {reviews_dir}")
            return pd.DataFrame()

        for filename in os.listdir(reviews_dir):
            if not filename.endswith("_reviews_raw.csv"):
                continue
            if filename.startswith("all_"):  # avoid all_reviews_raw.csv
                continue

            path = os.path.join(reviews_dir, filename)
            try:
                df = pd.read_csv(path)
            except Exception as e:
                print(f"  ⚠ Failed to read {filename}: {e}")
                continue

            if df.empty:
                continue

            key = filename.replace("_reviews_raw.csv", "")
            if key in self.filename_mapping:
                df["entity"] = self.filename_mapping[key]
                # keep human-readable component name
                df["series_component"] = key.replace("_", " ").title()
                all_reviews.append(df)
                print(f"  Loaded {len(df)} reviews from {key} → {df['entity'].iloc[0]}")
            else:
                print(f"  ⚠ No entity mapping for {key}; skipping.")

        if not all_reviews:
            print("⚠ No review data found")
            return pd.DataFrame()

        merged = pd.concat(all_reviews, ignore_index=True)
        merged = self._clean_reviews_data(merged)

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        merged.to_csv(output_path, index=False, encoding="utf-8")
        print(f"✓ Merged {len(merged)} reviews into {merged['entity'].nunique()} entities")
        print(f"  Entities: {', '.join(sorted(merged['entity'].unique()))}")
        return merged

    def _clean_reviews_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize, de-dup, keep >=50 chars, coerce score to 1..10/NA, add review_length.
        """
        print("Cleaning reviews data...")
        df = df.copy()

        # Ensure expected cols exist
        for col in [
            "review_text",
            "user_score",
            "review_date",
            "recommendation",
            "entity",
            "series_component",
            "series_id",
            "review_id",
            "page_number",
        ]:
            if col not in df.columns:
                df[col] = np.nan

        import unicodedata

        def normalize_text(t: str) -> str:
            if not isinstance(t, str):
                return ""
            t = unicodedata.normalize("NFC", t)
            # remove boilerplate & urls
            t = re.sub(r"(?i)(this review (may|might) contain spoilers|spoiler(s)? warning|click to read more)\.?", " ", t)
            t = re.sub(r"https?://\S+|www\.\S+", " ", t)
            t = re.sub(r"\s+", " ", t).strip()
            return t

        df["review_text"] = df["review_text"].astype(str).apply(normalize_text)

        # de-dup by normalized alnum key
        def norm_key(t: str) -> str:
            t = t.lower()
            t = re.sub(r"[^a-z0-9 ]+", " ", t)
            t = re.sub(r"\s+", " ", t).strip()
            return t

        df["_k"] = df["review_text"].apply(norm_key)
        before = len(df)
        df = df.drop_duplicates(subset=["_k"]).drop(columns=["_k"])
        removed = before - len(df)
        if removed:
            print(f"  Removed {removed} duplicate reviews")

        # keep >= 50 chars
        df = df[df["review_text"].str.len() >= 50].copy()
        print(f"  Kept reviews with 50+ chars: {len(df)}")

        # score to numeric 1..10/NA
        df["user_score"] = pd.to_numeric(df["user_score"], errors="coerce")
        df.loc[(df["user_score"] < 1) | (df["user_score"] > 10), "user_score"] = np.nan

        df["review_length"] = df["review_text"].str.len()

        # drop legacy helpful_votes if present
        if "helpful_votes" in df.columns:
            df = df.drop(columns=["helpful_votes"])

        print(f"✓ Final cleaned dataset: {len(df)} reviews")
        return df

    # ---------- stats ----------

    def merge_stats_data(self, stats_file: str, output_path: str) -> pd.DataFrame:
        """
        Merge stats (already per-series) into combined entities using:
        - weighted average for score_X_pct columns using score_total_votes
        - sum for status_ columns
        - keep score_total_votes and combined_mean_score
        """
        print("Merging statistics data...")

        if not os.path.exists(stats_file):
            print(f"⚠ Stats file not found: {stats_file}")
            return pd.DataFrame()

        stats = pd.read_csv(stats_file)
        if stats.empty:
            print("⚠ No stats data found")
            return pd.DataFrame()

        # Ensure types
        if "score_total_votes" in stats.columns:
            stats["score_total_votes"] = pd.to_numeric(stats["score_total_votes"], errors="coerce").fillna(0).astype(int)

        pct_cols = [c for c in stats.columns if c.startswith("score_") and c.endswith("_pct")]
        status_cols = [c for c in stats.columns if c.startswith("status_")]

        merged_entities: List[dict] = []
        for entity in sorted(stats["entity"].unique()):
            sub = stats[stats["entity"] == entity].copy()

            # series_components (plural) for clarity in merged stats
            series_components = ", ".join(sub["series_component"].astype(str).tolist())
            total_series = len(sub)

            # Weighted percentages
            total_votes = int(sub["score_total_votes"].sum()) if "score_total_votes" in sub.columns else 0

            combined_row = {
                "entity": entity,
                "series_components": series_components,
                "total_series": total_series,
                "score_total_votes": total_votes,
            }

            if total_votes > 0 and pct_cols:
                for col in pct_cols:
                    # numeric & weighted
                    vals = pd.to_numeric(sub[col], errors="coerce").fillna(0.0)
                    w = (vals * sub["score_total_votes"]).sum()
                    combined_row[col] = round(float(w) / total_votes, 2)
            else:
                for col in pct_cols:
                    combined_row[col] = 0.0

            # Sum statuses
            for col in status_cols:
                combined_row[col] = int(pd.to_numeric(sub[col], errors="coerce").fillna(0).sum())

            # Combined mean score from the combined percentages
            mean_sum = 0.0
            for col in pct_cols:
                try:
                    score = int(col.replace("score_", "").replace("_pct", ""))
                except ValueError:
                    continue
                pct = combined_row.get(col, 0.0)  # 0..100
                mean_sum += score * (pct / 100.0)
            combined_row["combined_mean_score"] = round(mean_sum, 2)

            merged_entities.append(combined_row)

        merged_df = pd.DataFrame(merged_entities)

        # Write
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        merged_df.to_csv(output_path, index=False, encoding="utf-8")
        print(f"✓ Merged stats for {len(merged_df)} entities")
        return merged_df

    # ---------- Tableau exports ----------

    def create_tableau_datasets(self, reviews_path: str, stats_path: str, output_dir: str = "data/exports"):
        """
        Create streamlined CSVs for Tableau.
        """
        print("Creating Tableau datasets...")

        if not (os.path.exists(reviews_path) and os.path.exists(stats_path)):
            print("⚠ Required data files not found")
            return

        reviews = pd.read_csv(reviews_path)
        stats = pd.read_csv(stats_path)

        t_reviews = self._prepare_tableau_reviews(reviews)
        t_stats = self._prepare_tableau_stats(stats)

        os.makedirs(output_dir, exist_ok=True)
        reviews_out = os.path.join(output_dir, "tableau_reviews.csv")
        stats_out = os.path.join(output_dir, "tableau_stats.csv")

        t_reviews.to_csv(reviews_out, index=False, encoding="utf-8")
        t_stats.to_csv(stats_out, index=False, encoding="utf-8")

        print("✓ Tableau datasets created:")
        print(f"  Reviews: {reviews_out}")
        print(f"  Stats:   {stats_out}")

    def _prepare_tableau_reviews(self, df: pd.DataFrame) -> pd.DataFrame:
        tdf = df.copy()
        req = [
            "entity",
            "series_component",
            "review_id",
            "review_text",
            "user_score",
            "recommendation",
            "review_date",
        ]
        for c in req:
            if c not in tdf.columns:
                tdf[c] = np.nan
        if "review_length" not in tdf.columns:
            tdf["review_length"] = tdf["review_text"].astype(str).str.len()

        # Optional sentiment/topic cols preserved if present
        keep = req + ["review_length"]
        for c in ["vader_compound", "vader_pos", "vader_neu", "vader_neg",
                  "lda_topic_id", "bertopic_topic_id"]:
            if c in tdf.columns:
                keep.append(c)
        return tdf[keep]

    def _prepare_tableau_stats(self, df: pd.DataFrame) -> pd.DataFrame:
        """Preserve mean & votes; do not overwrite existing values."""
        tdf = df.copy()

        for c in ["entity", "series_components", "total_series", "combined_mean_score"]:
            if c not in tdf.columns:
                tdf[c] = np.nan

        # Numeric coercions
        tdf["total_series"] = pd.to_numeric(tdf["total_series"], errors="coerce").fillna(0).astype(int)
        tdf["combined_mean_score"] = pd.to_numeric(tdf["combined_mean_score"], errors="coerce").round(2)
        if "score_total_votes" in tdf.columns:
            tdf["score_total_votes"] = pd.to_numeric(tdf["score_total_votes"], errors="coerce").fillna(0).astype(int)

        pct_cols = [c for c in tdf.columns if c.startswith("score_") and c.endswith("_pct")]
        status_cols = [c for c in tdf.columns if c.startswith("status_")]

        cols = ["entity", "series_components", "total_series", "combined_mean_score"]
        cols += pct_cols + status_cols
        if "score_total_votes" in tdf.columns:
            cols.append("score_total_votes")

        cols = [c for c in cols if c in tdf.columns]
        return tdf[cols]

    # ---------- summary ----------

    def generate_data_summary(self, reviews_path: str, stats_path: str) -> str:
        lines = []
        lines.append("=" * 60)
        lines.append("DATA MERGING SUMMARY")
        lines.append("=" * 60)
        lines.append("")

        if os.path.exists(reviews_path):
            r = pd.read_csv(reviews_path)
            lines.append("REVIEWS DATA:")
            lines.append("-" * 15)
            lines.append(f"Total reviews: {len(r):,}")
            lines.append(f"Entities: {r['entity'].nunique()}")
            lines.append(f"Series components: {r['series_component'].nunique()}")
            for ent in sorted(r["entity"].unique()):
                lines.append(f"  {ent}: {len(r[r['entity']==ent]):,} reviews")
            lines.append("")

        if os.path.exists(stats_path):
            s = pd.read_csv(stats_path)
            lines.append("STATISTICS DATA:")
            lines.append("-" * 18)
            lines.append(f"Total entities: {len(s)}")
            for _, row in s.iterrows():
                ent = row.get("entity", "Unknown")
                mean = row.get("combined_mean_score", np.nan)
                votes = row.get("score_total_votes", np.nan)
                try:
                    mean = float(mean)
                except Exception:
                    mean = np.nan
                try:
                    votes_str = f"{int(votes):,}" if pd.notna(votes) else "N/A"
                except Exception:
                    votes_str = "N/A"
                mean_str = f"{mean:.2f}" if pd.notna(mean) else "N/A"
                lines.append(f"  {ent}: Score {mean_str}, Votes {votes_str}")
            lines.append("")

        lines.append("=" * 60)
        return "\n".join(lines)


# ---------------------------
# CLI
# ---------------------------

def main():
    import argparse

    p = argparse.ArgumentParser(description="Merge anime data into combined entities")
    p.add_argument("--reviews-dir", default="data/raw", help="Directory with review CSV files")
    p.add_argument("--stats-file", default="data/raw/all_stats_raw.csv", help="Path to stats CSV file")
    p.add_argument("--output-dir", default="data/processed", help="Directory for merged data")
    p.add_argument("--create-tableau", action="store_true", help="Also create Tableau CSVs")
    args = p.parse_args()

    merger = AnimeDataMerger()

    # Reviews
    reviews_out = os.path.join(args.output_dir, "merged_reviews.csv")
    merger.merge_reviews_data(args.reviews_dir, reviews_out)

    # Stats
    stats_out = os.path.join(args.output_dir, "merged_stats.csv")
    merger.merge_stats_data(args.stats_file, stats_out)

    # Tableau
    if args.create_tableau:
        merger.create_tableau_datasets(reviews_out, stats_out)

    # Summary
    print()
    print(merger.generate_data_summary(reviews_out, stats_out))


if __name__ == "__main__":
    main()
