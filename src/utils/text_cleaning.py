import re

def clean_review_text(text: str) -> str:
    if text is None:
        return ""
    # Remove 'read more' artifacts and excessive whitespace
    t = re.sub(r'\s+', ' ', text).strip()
    # Remove boilerplate phrases if any appear commonly
    t = re.sub(r'(?i)no spoilers?\.?', '', t)
    return t

def normalize_whitespace(s: str) -> str:
    if s is None:
        return ""
    return ' '.join(s.split())

def safe_int(s, default=0):
    try:
        return int(str(s).replace(',', '').strip())
    except Exception:
        return default
