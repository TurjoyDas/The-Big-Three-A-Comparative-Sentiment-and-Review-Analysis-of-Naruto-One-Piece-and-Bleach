import os
import hashlib
import pandas as pd
from src.utils.text_cleaning import clean_review_text

def sha1(s: str) -> str:
    return hashlib.sha1(s.encode('utf-8', errors='ignore')).hexdigest()

def main():
    raw = pd.read_csv("data/raw/all_reviews_raw.csv")
    # Basic cleaning
    raw['review_text'] = raw['review_text'].astype(str).apply(clean_review_text)
    raw['review_len'] = raw['review_text'].str.len().fillna(0).astype(int)
    # Drop short reviews
    raw = raw[raw['review_len'] >= 50].copy()
    # Deduplicate on text hash within entity
    raw['text_hash'] = raw.apply(lambda r: sha1(r['entity'] + r['review_text']), axis=1)
    raw = raw.drop_duplicates(subset=['text_hash']).drop(columns=['text_hash'])
    # Save
    os.makedirs("data/clean", exist_ok=True)
    raw.to_csv("data/clean/all_reviews_clean.csv", index=False, encoding="utf-8")
    print(f"Clean reviews saved: {len(raw)} → data/clean/all_reviews_clean.csv")

if __name__ == "__main__":
    main()
