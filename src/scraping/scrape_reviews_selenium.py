# src/scraping/scrape_reviews_selenium.py

import os
import time
import hashlib
import pandas as pd

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# -------------------------
# Simple text cleaner (no usernames involved anywhere)
# -------------------------
def clean_review_text(text: str) -> str:
    if not text:
        return ""
    t = text.replace("\r", " ").replace("\n", " ").replace("\t", " ")
    t = " ".join(t.split())
    return t.strip()


# -------------------------
# Driver
# -------------------------
def get_driver(headless=True, user_agent=None):
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1400,1000")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    # look like a real browser
    opts.add_argument("--lang=en-US,en;q=0.9")
    opts.add_argument("--accept-language=en-US,en;q=0.9")
    if not user_agent:
        user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        )
    opts.add_argument(f"--user-agent={user_agent}")
    driver = webdriver.Chrome(options=opts)
    return driver


# -------------------------
# Scraper
# -------------------------
class Scraper:
    def __init__(self, headless=True, delay_seconds=2.0):
        self.headless = headless
        self.delay = float(delay_seconds)

    def get_driver(self):
        return get_driver(headless=self.headless)

    # ---------- waits & render nudges ----------
    def _wait_for_reviews(self, driver, timeout=10):
        """Wait until any review-like block appears or we time out."""
        XPATH = ("//div[contains(@class,'review')]"
                 "[.//div[contains(@class,'review-text') or contains(@class,'text')]]")
        try:
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.XPATH, XPATH))
            )
        except Exception:
            pass  # caller handles empty case

    def _force_render(self, driver):
        """Kick lazy renders."""
        try:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.5);")
            time.sleep(0.2)
            driver.execute_script("window.scrollTo(0, 0);")
        except Exception:
            pass

    # ---------- filters/sorting (avoid 'Most Helpful' ceiling) ----------
    def _prepare_page_filters(self, driver):
        """Switch to All Reviews (not Preliminary) and sort by Newest/Recent if present."""
        # 1) Try select dropdowns
        try:
            selects = driver.find_elements(By.CSS_SELECTOR, "select, .sort-select")
            for sel in selects:
                try:
                    opts = sel.find_elements(By.TAG_NAME, "option")
                    chosen = False
                    for o in opts:
                        text = (o.text or "").lower()
                        val = (o.get_attribute("value") or "").lower()
                        if "recent" in val or "new" in text or "date" in text:
                            driver.execute_script("arguments[0].selected = true;", o)
                            driver.execute_script("arguments[0].dispatchEvent(new Event('change'));", sel)
                            chosen = True
                            time.sleep(0.3)
                            break
                    if chosen:
                        break
                except Exception:
                    continue
        except Exception:
            pass

        # 2) Try filter pills/tabs for "All"
        try:
            candidates = driver.find_elements(
                By.XPATH,
                "//a[contains(.,'All Reviews') or contains(.,'All reviews') or contains(.,'All')]"
            )
            for c in candidates:
                if c.is_displayed():
                    try:
                        driver.execute_script("arguments[0].click();", c)
                        time.sleep(0.2)
                        break
                    except Exception:
                        pass
        except Exception:
            pass

        # 3) Spoilers toggle (if content is hidden)
        try:
            btns = driver.find_elements(By.XPATH, "//a[contains(.,'Show Spoilers') or contains(.,'Spoilers')]")
            for b in btns:
                if b.is_displayed():
                    try:
                        driver.execute_script("arguments[0].click();", b)
                        time.sleep(0.1)
                    except Exception:
                        pass
        except Exception:
            pass

    # ---------- read-more expanders ----------
    def click_all_read_more(self, driver):
        """
        Expand all 'Read more' anchors (<a class="js-readmore">).
        Run multiple passes in case more buttons appear after expansion.
        """
        total_clicked = 0
        for _ in range(3):
            clicked_round = 0
            buttons = driver.find_elements(By.CSS_SELECTOR, "a.js-readmore")
            for btn in buttons:
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                    time.sleep(0.05)
                    try:
                        btn.click()
                    except Exception:
                        driver.execute_script("arguments[0].click();", btn)
                    clicked_round += 1
                except Exception:
                    continue
            total_clicked += clicked_round
            if clicked_round == 0:
                break
            time.sleep(0.15)
        return total_clicked

    def _expand_review_in_block(self, driver, block):
        """Expand any residual toggles inside a single review block."""
        toggle_selectors = [
            "a.js-readmore",                 # MAL current
            "span.js-toggle-review-button",  # fallbacks
            "button.js-toggle-review-button",
            "span.read-more",
            "button.read-more",
            "a.read-more",
        ]
        for selector in toggle_selectors:
            try:
                elems = block.find_elements(By.CSS_SELECTOR, selector)
                for e in elems:
                    try:
                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", e)
                        time.sleep(0.05)
                        driver.execute_script("arguments[0].click();", e)
                        time.sleep(0.08)
                    except Exception:
                        continue
            except Exception:
                continue
        # force-unhide hidden spans
        try:
            driver.execute_script(
                """
                arguments[0]
                  .querySelectorAll('.hidden, .hide, .js-hidden, [style*="display:none"]')
                  .forEach(el => { el.style.display='inline'; el.classList.remove('hidden','hide','js-hidden'); });
                """,
                block
            )
        except Exception:
            pass

    # ---------- block discovery ----------
    def _find_review_blocks(self, driver):
        XPATHS = [
            # common containers
            "//div[contains(@class,'review')][.//div[contains(@class,'review-text') or contains(@class,'text')]]",
            "//article[contains(@class,'review')][.//div[contains(@class,'review-text') or contains(@class,'text')]]",
            # explicit old class
            "//*[@class and contains(concat(' ',normalize-space(@class),' '),' review-element ')]",
            # very defensive
            "//*[.//a[contains(@class,'js-readmore')] and (.//div[contains(@class,'text')] or .//div[contains(@class,'review-text')])]"
        ]
        for xp in XPATHS:
            elems = driver.find_elements(By.XPATH, xp)
            if elems:
                return elems
        return []

    # ---------- parse one block ----------
    def parse_review_block(self, block):
        try:
            driver = block._parent

            # text
            review_text = ""
            for sel in ["div.text", "div.review-text", ".text.readability", ".review-content"]:
                try:
                    el = block.find_element(By.CSS_SELECTOR, sel)
                    review_text = (el.text or "").strip()
                    if review_text:
                        break
                except Exception:
                    continue

            # expand if likely truncated
            if (not review_text) or ("..." in review_text and len(review_text) < 400) or len(review_text) < 120:
                self._expand_review_in_block(driver, block)
                time.sleep(0.1)
                for sel in ["div.text", "div.review-text", ".text.readability", ".review-content"]:
                    try:
                        el = block.find_element(By.CSS_SELECTOR, sel)
                        t2 = (el.text or "").strip()
                        if len(t2) > len(review_text):
                            review_text = t2
                            break
                    except Exception:
                        continue

            if (not review_text) or len(review_text) < 50:
                return None
            review_text = clean_review_text(review_text)

            # score 1..10
            score = None
            for sel in ["div.score", "span.score", ".rating", ".num"]:
                try:
                    txt = block.find_element(By.CSS_SELECTOR, sel).get_attribute("innerText") or ""
                    txt = txt.strip()
                except Exception:
                    continue
                for tok in txt.split():
                    if tok.isdigit():
                        val = int(tok)
                        if 1 <= val <= 10:
                            score = val
                            break
                if score is not None:
                    break

            # recommendation tag
            recommendation = ""
            try:
                tags = block.find_elements(By.CSS_SELECTOR, ".tag, .review-tag, .review-element .tag")
                for tag in tags:
                    t = (tag.text or "").strip()
                    if not t:
                        continue
                    if "Not Recommended" in t:
                        recommendation = "Not Recommended"; break
                    if "Mixed Feelings" in t:
                        recommendation = "Mixed Feelings"; break
                    if "Recommended" in t:
                        recommendation = "Recommended"; break
            except Exception:
                pass

            # date
            date_text = ""
            for sel in [".update_at", ".update_on", ".review-date", "div.reviewer + div"]:
                try:
                    dt = block.find_element(By.CSS_SELECTOR, sel).text.strip()
                    if dt:
                        date_text = dt
                        break
                except Exception:
                    continue

            return {
                "review_text": review_text,
                "user_score": score,
                "recommendation": recommendation,
                "review_date": date_text,
            }
        except Exception as e:
            print(f"  ⚠️ parse error: {e}")
            return None

    # ---------- entity helpers ----------
    def _entity_for(self, series_name: str) -> str:
        mapping = {
            "Naruto": "Naruto",
            "Naruto Shippuden": "Naruto",
            "One Piece": "One Piece",
            "Bleach": "Bleach",
            "Bleach TYBW Part 1": "Bleach",
            "Bleach TYBW Part 2": "Bleach",
        }
        return mapping.get(series_name, series_name)

    def _mal_id_for(self, series_name: str) -> int:
        mapping = {
            "Naruto": 20,
            "Naruto Shippuden": 1735,
            "One Piece": 21,
            "Bleach": 269,
            "Bleach TYBW Part 1": 41467,
            "Bleach TYBW Part 2": 41468,
        }
        return mapping.get(series_name, 0)

    def _review_id(self, series_name: str, review_text: str) -> str:
        text_hash = hashlib.sha1(f"{series_name}{review_text[:120]}".encode()).hexdigest()[:10]
        return f"{series_name.lower().replace(' ', '_')}_{text_hash}"

    # ---------- pagination helper ----------
    def _goto_next_page(self, driver, reviews_url, page):
        """Try 'More Reviews' first, else navigate via ?p=page+1."""
        # Button/link path
        try:
            links = driver.find_elements(By.XPATH, "//a[contains(., 'More Reviews')]")
            for a in links:
                if a.is_displayed():
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", a)
                    time.sleep(0.1)
                    try:
                        a.click()
                    except Exception:
                        driver.execute_script("arguments[0].click();", a)
                    self._wait_for_reviews(driver, timeout=8)
                    self._force_render(driver)
                    time.sleep(self.delay)
                    return True, page + 1
        except Exception:
            pass
        # Fallback param
        next_url = f"{reviews_url}?p={page+1}"
        driver.get(next_url)
        self._wait_for_reviews(driver, timeout=8)
        self._force_render(driver)
        time.sleep(self.delay)
        return True, page + 1

    # ---------- main per-series scrape ----------
    def scrape_reviews_for_series(self, series_name: str, reviews_url: str, target_reviews: int):
        print(f"\n🎯 Scraping reviews for {series_name}")
        print(f"   Target: {target_reviews} | URL: {reviews_url}")

        driver = self.get_driver()
        reviews, page = [], 1
        consecutive_empty = 0
        MAX_EMPTY_PAGES = 12     # generous tolerance
        MAX_PAGES = 120          # safety cap

        try:
            # Page 1
            driver.get(reviews_url)
            self._wait_for_reviews(driver, timeout=12)
            self._prepare_page_filters(driver)  # critical to avoid 'Most Helpful' ceiling
            self._force_render(driver)
            time.sleep(self.delay)

            while len(reviews) < target_reviews and page <= MAX_PAGES:
                print(f"   📄 Page {page}: {len(reviews)}/{target_reviews} collected")

                # expand readmores
                self.click_all_read_more(driver)
                self._force_render(driver)
                time.sleep(0.5)

                # find blocks
                blocks = self._find_review_blocks(driver)
                if not blocks:
                    print("   ⚠️ No review blocks found on this page, trying next page...")
                    consecutive_empty += 1
                    if consecutive_empty >= MAX_EMPTY_PAGES:
                        print(f"   ⚠️ {consecutive_empty} empty pages in a row — stopping.")
                        break
                    ok, page = self._goto_next_page(driver, reviews_url, page)
                    if not ok:
                        break
                    continue
                else:
                    consecutive_empty = 0

                # parse
                for block in blocks:
                    if len(reviews) >= target_reviews:
                        break
                    row = self.parse_review_block(block)
                    if not row:
                        continue
                    row.update({
                        "entity": self._entity_for(series_name),
                        "series_component": series_name,
                        "series_id": self._mal_id_for(series_name),
                        "review_id": self._review_id(series_name, row["review_text"]),
                        "page_number": page,
                    })
                    reviews.append(row)

                if len(reviews) >= target_reviews:
                    break

                # next page
                ok, page = self._goto_next_page(driver, reviews_url, page)
                if not ok:
                    break

        except Exception as e:
            print(f"   ❌ Error scraping {series_name}: {e}")
        finally:
            driver.quit()

        print(f"   ✅ Completed {series_name}: {len(reviews)} reviews")
        return reviews


# -------------------------
# Run with your exact targets
# -------------------------
def main():
    SERIES = [
        {"series_component": "Naruto",
         "reviews_url": "https://myanimelist.net/anime/20/Naruto/reviews",
         "target_reviews": 300},
        {"series_component": "Naruto Shippuden",
         "reviews_url": "https://myanimelist.net/anime/1735/Naruto__Shippuuden/reviews",
         "target_reviews": 300},
        {"series_component": "One Piece",
         "reviews_url": "https://myanimelist.net/anime/21/One_Piece/reviews",
         "target_reviews": 600},
        {"series_component": "Bleach",
         "reviews_url": "https://myanimelist.net/anime/269/Bleach/reviews",
         "target_reviews": 400},
        {"series_component": "Bleach TYBW Part 1",
         "reviews_url": "https://myanimelist.net/anime/41467/Bleach__Sennen_Kessen_Hen__Ketsubetsu_Tan/reviews",
         "target_reviews": 100},
        {"series_component": "Bleach TYBW Part 2",
         "reviews_url": "https://myanimelist.net/anime/41468/Bleach__Sennen_Kessen_Hen__Saigo_no_15_Byoshi/reviews",
         "target_reviews": 100},
    ]

    HEADLESS = True
    DELAY = 2.0
    OUT_DIR = os.path.join("data", "raw")
    os.makedirs(OUT_DIR, exist_ok=True)

    scraper = Scraper(headless=HEADLESS, delay_seconds=DELAY)

    all_rows = []
    for s in SERIES:
        name = s["series_component"]
        url = s["reviews_url"]
        target = int(s["target_reviews"])
        print(f"Scraping reviews for: {name}")

        rows = scraper.scrape_reviews_for_series(name, url, target)
        df = pd.DataFrame(rows)
        out_path = os.path.join(OUT_DIR, f"{name.lower().replace(' ','_')}_reviews_raw.csv")
        df.to_csv(out_path, index=False, encoding="utf-8")
        print(f"Saved {len(df)} reviews → {out_path}")
        all_rows.extend(rows)

    # combined
    all_df = pd.DataFrame(all_rows)
    all_df.to_csv(os.path.join(OUT_DIR, "all_reviews_raw.csv"), index=False, encoding="utf-8")
    print(f"Total reviews saved: {len(all_df)}")


if __name__ == "__main__":
    main()
