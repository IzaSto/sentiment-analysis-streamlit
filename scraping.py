import os
import json
import time
import requests
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

BASE = "https://web-scraping.dev"
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


# ================= PRODUCTS (requests, pagination 1..6) =================
def scrape_products():
    print("🛍️ Scraping products...")
    products = []

    for page in range(1, 7):
        url = f"{BASE}/products?page={page}"
        res = requests.get(url, headers=HEADERS, timeout=30)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        cards = soup.select("div.row.product")
        print(f"Page {page}: {len(cards)} products")

        if not cards:
            break

        for card in cards:
            name_el = card.select_one(".col-8.description h3 a")
            desc_el = card.select_one(".col-8.description .short-description")
            price_el = card.select_one(".col-2.price-wrap") or card.select_one(".price")

            products.append({
                "name": name_el.get_text(strip=True) if name_el else "",
                "description": desc_el.get_text(" ", strip=True) if desc_el else "",
                "price": price_el.get_text(strip=True) if price_el else ""
            })

    with open(os.path.join(DATA_DIR, "products_data.json"), "w", encoding="utf-8") as f:
        json.dump(products, f, indent=2, ensure_ascii=False)

    print(f"✅ Products saved: {len(products)}")


# ================= TESTIMONIALS (requests, infinite scroll via HTMX API) =================
def scrape_testimonials():
    print("💬 Scraping testimonials...")

    # 1) Load the testimonials page to get the token from <script id="appData">
    page = requests.get(f"{BASE}/testimonials", headers=HEADERS, timeout=30)
    page.raise_for_status()
    soup = BeautifulSoup(page.text, "html.parser")

    app_data = soup.select_one("#appData")
    if not app_data or not app_data.text.strip():
        raise RuntimeError("Could not find #appData token on /testimonials")

    token = json.loads(app_data.text.strip()).get("x-secret-token")
    if not token:
        raise RuntimeError("x-secret-token missing in #appData JSON")

    api_headers = {
        **HEADERS,
        "Referer": f"{BASE}/testimonials",
        "x-secret-token": token
    }

    testimonials = []
    page_num = 1

    while True:
        api_url = f"{BASE}/api/testimonials?page={page_num}"
        res = requests.get(api_url, headers=api_headers, timeout=30)

        # stop when no more pages
        if res.status_code != 200 or not res.text.strip():
            break

        frag = BeautifulSoup(res.text, "html.parser")
        items = frag.select("div.testimonial")
        if not items:
            break

        for item in items:
            text_el = item.select_one("p.text")
            author_el = item.select_one("identicon-svg")
            rating = len(item.select("span.rating svg"))

            testimonials.append({
                "author": author_el["username"] if author_el and author_el.has_attr("username") else "User",
                "rating": rating,
                "text": text_el.get_text(strip=True) if text_el else ""
            })

        print(f"Page {page_num}: {len(items)} testimonials")
        page_num += 1
        time.sleep(0.05)

    with open(os.path.join(DATA_DIR, "testimonials_data.json"), "w", encoding="utf-8") as f:
        json.dump(testimonials, f, indent=2, ensure_ascii=False)

    print(f"✅ Testimonials saved: {len(testimonials)}")


# ================= REVIEWS (selenium - keep exactly as you had it working) =================
def setup_driver():
    options = Options()
    options.add_argument("--start-maximized")
    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )


def scrape_reviews():
    print("📝 Scraping reviews (selenium)...")
    driver = setup_driver()
    driver.get(f"{BASE}/reviews")

    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div.review"))
    )

    reviews = []

    while True:
        cards = driver.find_elements(By.CSS_SELECTOR, "div.review")

        for card in cards[len(reviews):]:
            try:
                date_text = card.find_element(
                    By.CSS_SELECTOR, '[data-testid="review-date"]'
                ).text.strip()

                rating = len(
                    card.find_elements(
                        By.CSS_SELECTOR, '[data-testid="review-stars"] svg'
                    )
                )

                text = card.find_element(
                    By.CSS_SELECTOR, '[data-testid="review-text"]'
                ).text.strip()

                reviews.append({
                    "date": date_text,
                    "rating": rating,
                    "text": text
                })
            except:
                pass

        try:
            load_more = driver.find_element(By.ID, "page-load-more")
            driver.execute_script("arguments[0].click();", load_more)
            time.sleep(1)
        except:
            break

    driver.quit()

    with open(os.path.join(DATA_DIR, "reviews_data.json"), "w", encoding="utf-8") as f:
        json.dump(reviews, f, indent=2, ensure_ascii=False)

    print(f"✅ Reviews saved: {len(reviews)}")


# ================= RUN =================
if __name__ == "__main__":
    scrape_products()
    scrape_testimonials()
    scrape_reviews()
    print("🎉 ALL DATA SCRAPED SUCCESSFULLY")
