"""
Advanced Topic Modeling for Big Three Anime Reviews

Provides LDA (gensim) as a reliable baseline and optional BERTopic for
state-of-the-art topic discovery and interactive visualizations.

Outputs document-level topic assignments compatible with the pipeline:
- LDA: columns 'lda_topic_id', 'lda_topic_prob'
- BERTopic (optional): column 'bertopic_topic_id'
"""

from __future__ import annotations

import os
import re
from typing import List, Tuple, Dict, Optional

import numpy as np
import pandas as pd

# Gensim for LDA
from gensim import corpora
from gensim.models.ldamulticore import LdaMulticore

# Lightweight stopwords without requiring external downloads
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

# Optional BERTopic
try:
    from bertopic import BERTopic
    _BER_TOPIC_AVAILABLE = True
except Exception:
    _BER_TOPIC_AVAILABLE = False


class AdvancedTopicModeler:
    """
    Topic modeling helper supporting LDA and optional BERTopic.
    """

    def __init__(self, use_bertopic: bool = True, use_lda: bool = True, random_state: int = 42):
        self.use_lda = use_lda
        self.use_bertopic = use_bertopic and _BER_TOPIC_AVAILABLE
        self.random_state = random_state

        # LDA artifacts
        self._dictionary: Optional[corpora.Dictionary] = None
        self._corpus: Optional[List[List[Tuple[int, int]]]] = None
        self._lda_model: Optional[LdaMulticore] = None
        self._lda_num_topics: Optional[int] = None

        # BERTopic artifacts
        self._bertopic_model: Optional[BERTopic] = None
        self._bertopic_topics: Optional[List[int]] = None

    # -----------------------------
    # Text preprocessing
    # -----------------------------
    def _tokenize_for_lda(self, text: str) -> List[str]:
        if not isinstance(text, str):
            return []
        text = text.lower()
        text = re.sub(r"https?://\S+|www\.\S+", " ", text)
        text = re.sub(r"[^a-z\s]", " ", text)
        tokens = [t for t in text.split() if t not in ENGLISH_STOP_WORDS and len(t) > 2]
        return tokens

    def _prepare_lda_inputs(self, texts: List[str], min_doc_freq: int = 5) -> Tuple[corpora.Dictionary, List[List[Tuple[int, int]]]]:
        token_docs = [self._tokenize_for_lda(t) for t in texts]
        dictionary = corpora.Dictionary(token_docs)
        # Filter very rare and extremely common tokens
        dictionary.filter_extremes(no_below=min_doc_freq, no_above=0.6, keep_n=5000)
        corpus = [dictionary.doc2bow(doc) for doc in token_docs]
        return dictionary, corpus

    # -----------------------------
    # LDA
    # -----------------------------
    def train_lda(self, texts: List[str], num_topics: int = 8, passes: int = 2, workers: int = 0):
        """
        Train an LDA model and keep model artifacts in-memory for assignment.
        """
        if not self.use_lda:
            return None

        dictionary, corpus = self._prepare_lda_inputs(texts)
        # Default to all available cores if workers not provided
        if workers is None or workers <= 0:
            try:
                import multiprocessing as mp
                workers = max(1, mp.cpu_count() - 1)
            except Exception:
                workers = 1

        lda_model = LdaMulticore(
            corpus=corpus,
            id2word=dictionary,
            num_topics=num_topics,
            random_state=self.random_state,
            chunksize=2000,
            passes=passes,
            workers=workers,
            minimum_probability=0.0,
        )

        self._dictionary = dictionary
        self._corpus = corpus
        self._lda_model = lda_model
        self._lda_num_topics = num_topics

        # Return simple topic summaries
        topics: Dict[int, List[Tuple[str, float]]] = {}
        for topic_id in range(num_topics):
            topics[topic_id] = lda_model.show_topic(topic_id, topn=10)
        return {
            "num_topics": num_topics,
            "topics": topics,
        }

    # -----------------------------
    # BERTopic
    # -----------------------------
    def train_bertopic(self, texts: List[str], num_topics: Optional[int] = None):
        """
        Fit BERTopic on raw texts. If BERTopic is unavailable, this is a no-op.
        """
        if not self.use_bertopic:
            return None

        # Let BERTopic decide the number of topics; optionally reduce_outliers later
        model = BERTopic(verbose=False, calculate_probabilities=False, random_state=self.random_state)
        topics, _ = model.fit_transform(texts)

        self._bertopic_model = model
        self._bertopic_topics = topics
        return {"n_topics": len(set([t for t in topics if t != -1]))}

    # -----------------------------
    # Assignment
    # -----------------------------
    def _assign_lda_to_text(self, text: str) -> Tuple[int, float]:
        if self._lda_model is None or self._dictionary is None:
            return -1, 0.0
        bow = self._dictionary.doc2bow(self._tokenize_for_lda(text))
        if not bow:
            return -1, 0.0
        distr = self._lda_model.get_document_topics(bow, minimum_probability=0.0)
        if not distr:
            return -1, 0.0
        topic_id, prob = max(distr, key=lambda x: x[1])
        return int(topic_id), float(prob)

    def assign_topics_to_documents(self, df: pd.DataFrame, text_col: str = "review_text") -> pd.DataFrame:
        """
        Assign topics from the trained models to each document.
        """
        result = df.copy()

        # LDA assignments
        if self._lda_model is not None:
            lda_ids: List[int] = []
            lda_probs: List[float] = []
            for text in result[text_col].fillna("").astype(str).tolist():
                tid, prob = self._assign_lda_to_text(text)
                lda_ids.append(tid)
                lda_probs.append(prob)
            result["lda_topic_id"] = lda_ids
            result["lda_topic_prob"] = np.round(lda_probs, 4)

        # BERTopic assignments (if model was trained here)
        if self._bertopic_model is not None:
            topics = self._bertopic_model.transform(result[text_col].fillna("").astype(str).tolist())[0]
            result["bertopic_topic_id"] = topics

        return result

    # -----------------------------
    # Visualization
    # -----------------------------
    def visualize_topics(self, save_path: str = "data/analysis/topics"):
        os.makedirs(save_path, exist_ok=True)

        # LDA: save top words per topic as simple TSV and word bars
        if self._lda_model is not None and self._lda_num_topics:
            # Save top terms table
            lines = ["topic_id\tterm\tweight"]
            for topic_id in range(self._lda_num_topics):
                for term, weight in self._lda_model.show_topic(topic_id, topn=15):
                    lines.append(f"{topic_id}\t{term}\t{weight:.4f}")
            with open(os.path.join(save_path, "lda_top_terms.tsv"), "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

        # BERTopic: interactive HTML visualizations
        if self._bertopic_model is not None:
            try:
                fig = self._bertopic_model.visualize_topics()
                fig.write_html(os.path.join(save_path, "bertopic_topics.html"))
            except Exception:
                # Skip visualization if environment lacks plotly kaleido
                pass


def main():
    """CLI entrypoint for topic modeling.

    Usage:
      python -m src.nlp.topic_modeling_advanced INPUT_CSV OUTPUT_CSV [--use-bertopic] [--num-topics N] [--visualize]
    """
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Advanced topic modeling (LDA + optional BERTopic)")
    parser.add_argument("input", help="Input CSV path (expects 'review_text' column)")
    parser.add_argument("output", help="Output CSV path with topic assignments")
    parser.add_argument("--use-bertopic", action="store_true", help="Enable BERTopic if installed")
    parser.add_argument("--num-topics", type=int, default=8, help="Number of LDA topics")
    parser.add_argument("--visualize", action="store_true", help="Save topic visualizations")

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: input file not found: {args.input}")
        sys.exit(1)

    df = pd.read_csv(args.input)
    texts = df.get("review_text", pd.Series([])).fillna("").astype(str).tolist()

    modeler = AdvancedTopicModeler(use_bertopic=args.use_bertopic, use_lda=True)

    print(f"Training LDA with {args.num_topics} topics on {len(texts)} documents...")
    lda_info = modeler.train_lda(texts, num_topics=args.num_topics)
    if lda_info:
        print(f"✓ LDA trained with {lda_info['num_topics']} topics")

    if args.use_bertopic and not _BER_TOPIC_AVAILABLE:
        print("⚠ BERTopic requested but not installed. Skipping.")

    if args.use_bertopic and _BER_TOPIC_AVAILABLE:
        print("Training BERTopic (this can take a while)...")
        bt_info = modeler.train_bertopic(texts)
        if bt_info:
            print(f"✓ BERTopic trained with ~{bt_info['n_topics']} topics")

    # Assign topics
    out_df = modeler.assign_topics_to_documents(df)

    # Save
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    out_df.to_csv(args.output, index=False, encoding="utf-8")
    print(f"✓ Saved topic assignments → {args.output}")

    if args.visualize:
        print("Saving topic visualizations...")
        modeler.visualize_topics()
        print("✓ Visualizations saved in data/analysis/topics/")


if __name__ == "__main__":
    main()


