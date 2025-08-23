import os
import re
import time
import yaml
import pandas as pd
import requests
from bs4 import BeautifulSoup

def parse_score_histogram(soup):
    """Return both raw counts and percentage histogram for scores 10..1."""
    counts = {str(k): 0 for k in range(10, 0, -1)}
    for tr in soup.select("table.score-stats tr"):
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td","th"])]
        if len(cells) >= 2 and cells[0].strip().isdigit():
            score = cells[0].strip()
            m = re.search(r"[\d,]+", cells[1])
            if score in counts and m:
                counts[score] = int(m.group(0).replace(",", ""))
    total_votes = sum(counts.values())
    pct = {s: (counts[s] / total_votes * 100.0) if total_votes > 0 else 0.0 for s in counts}
    return counts, pct, total_votes

def parse_status_distribution(soup):
    # Watching / Completed / On-Hold / Dropped / Plan to Watch
    dist = {"watching": 0, "completed": 0, "on_hold": 0, "dropped": 0, "plan_to_watch": 0}
    text = soup.get_text(" ", strip=True)
    # Heuristics with regex
    pairs = {
        "watching": r"Watching\s*([\d,]+)",
        "completed": r"Completed\s*([\d,]+)",
        "on_hold": r"On-Hold\s*([\d,]+)",
        "dropped": r"Dropped\s*([\d,]+)",
        "plan_to_watch": r"Plan to Watch\s*([\d,]+)",
    }
    for key, pat in pairs.items():
        m = re.search(pat, text, flags=re.I)
        if m:
            dist[key] = int(m.group(1).replace(",", ""))
    dist["total_status"] = sum(dist.values())
    return dist

def parse_header_metrics(_soup):
    """Deprecated: we no longer collect rank/popularity/members/favorites."""
    return None, None, None, None

def scrape_stats_for_series(series_cfg, delay=1.0):
    url = series_cfg['stats_url']
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    time.sleep(delay)
    soup = BeautifulSoup(r.text, "lxml")
    counts, pct, total_votes = parse_score_histogram(soup)
    dist = parse_status_distribution(soup)
    _rank, _pop, _members, _favorites = parse_header_metrics(soup)
    out = {
        "entity": series_cfg['entity'],
        "series_component": series_cfg['series_component'],
        "series_id": series_cfg['mal_id'],
    }
    # Score percentages only
    for k, v in pct.items():
        out[f"score_{k}_pct"] = round(v, 2)
    # Keep internal total score votes for proper merging (will be dropped in exports)
    out["score_total_votes"] = total_votes
    # Status counts and total
    for k, v in dist.items():
        out[f"status_{k}"] = v
    return out

def main():
    with open("config.yml", "r") as f:
        cfg = yaml.safe_load(f)

    rows = []
    for series in cfg['entities']:
        print(f"Scraping stats for: {series['series_component']}")
        try:
            row = scrape_stats_for_series(series)
            rows.append(row)
        except Exception as e:
            print(f"  Failed: {e}")

    df = pd.DataFrame(rows)
    os.makedirs(cfg['runtime']['out_dir_raw'], exist_ok=True)
    out_path = os.path.join(cfg['runtime']['out_dir_raw'], "all_stats_raw.csv")
    df.to_csv(out_path, index=False, encoding="utf-8")
    print(f"Saved stats → {out_path}")

if __name__ == "__main__":
    main()
