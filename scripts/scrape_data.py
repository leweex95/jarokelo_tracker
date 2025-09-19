import os
import json
import locale
from datetime import datetime
import argparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "https://jarokelo.hu/bejelentesek"
DATA_DIR = "data/entries"

locale.setlocale(locale.LC_TIME, 'hu_HU.UTF-8')

def get_monthly_file(report_date: str) -> str:
    """Return file path based on report's month (YYYY-MM)."""
    # report_date expected as string, e.g. "2025-08-25"
    month_str = datetime.strptime(report_date, "%Y-%m-%d").strftime("%Y-%m")
    return os.path.join(DATA_DIR, f"{month_str}.jsonl")

def load_existing_urls(report_date: str) -> set:
    """Load already saved report URLs for the report's month."""
    file_path = get_monthly_file(report_date)
    if not os.path.exists(file_path):
        return set()
    urls = set()
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                urls.add(json.loads(line)["url"])
            except json.JSONDecodeError:
                continue
    return urls

def save_report(report: dict, existing_urls: set) -> None:
    """Save a report if it's not already saved."""
    if report["url"] in existing_urls:
        return
    existing_urls.add(report["url"])
    with open(get_monthly_file(report["date"]), "a", encoding="utf-8") as f:
        f.write(json.dumps(report, ensure_ascii=False) + "\n")

def normalize_date(date_str: str) -> str:
    """Convert Hungarian date like '2025. szeptember 15.' to 'YYYY-MM-DD'."""
    dt = datetime.strptime(date_str.strip(), "%Y. %B %d.")
    return dt.strftime("%Y-%m-%d")

def scrape_report(driver, wait, url: str) -> dict:
    """Scrape a single report page and return its data."""
    driver.execute_script("window.open(arguments[0]);", url)
    driver.switch_to.window(driver.window_handles[1])

    title = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "h1.report__title"))).text

    # Author
    author_elem = driver.find_elements(By.CSS_SELECTOR, "div.report__reporter div.report__author a")
    if author_elem:
        author = author_elem[0].text
        author_profile = author_elem[0].get_attribute("href")
    else:
        anon_elem = driver.find_elements(By.CSS_SELECTOR, "div.report__reporter div.report__author")
        author = anon_elem[0].text.strip() if anon_elem else None
        author_profile = None

    # Date, category, institution, supporter, description
    date_elem = driver.find_elements(By.CSS_SELECTOR, "time.report__date")
    date = normalize_date(date_elem[0].text) if date_elem else None

    category_elem = driver.find_elements(By.CSS_SELECTOR, "div.report__category a")
    category = category_elem[0].text if category_elem else None

    institution_elem = driver.find_elements(By.CSS_SELECTOR, "div.report__institution a")
    institution = institution_elem[0].text if institution_elem else None

    supporter_elem = driver.find_elements(By.CSS_SELECTOR, "span.report__partner__about")
    supporter = supporter_elem[0].text if supporter_elem else None

    description_elem = driver.find_elements(By.CSS_SELECTOR, "p.report__description")
    description = description_elem[0].text if description_elem else None

    # Status
    status_elem = driver.find_elements(By.CSS_SELECTOR, "span.badge")
    status = status_elem[0].text.strip() if status_elem else None

    # Address
    address_elem = driver.find_elements(By.CSS_SELECTOR, "address.report__location__address")
    if address_elem:
        city = address_elem[0].text.split("\n")[0].strip() if address_elem[0].text else None
        district_elem = address_elem[0].find_elements(By.CSS_SELECTOR, "span.report__location__address__district")
        district = district_elem[0].text.strip() if district_elem else None
        address = ", ".join(filter(None, [city, district]))
    else:
        address = None

    # Images
    image_divs = driver.find_elements(By.CSS_SELECTOR, "div.report__media__item__img[style]")
    images = [div.get_attribute("style").split("url(")[1].split(")")[0].strip('"') for div in image_divs]

    driver.close()
    driver.switch_to.window(driver.window_handles[0])

    return {
        "url": url,
        "title": title,
        "author": author,
        "author_profile": author_profile,
        "date": date,
        "category": category,
        "institution": institution,
        "supporter": supporter,
        "description": description,
        "status": status,
        "address": address,
        "images": images
    }

def scrape_listing_page(driver, wait, page_url: str) -> str:
    """Scrape all reports from a listing page. Return next page URL or None."""
    driver.get(page_url)
    links = [a.get_attribute("href") for a in driver.find_elements(By.CSS_SELECTOR, "article.card a.card__media__bg")]

    for link in links:
        report = scrape_report(driver, wait, link)
        existing_urls = load_existing_urls(report["date"])
        save_report(report, existing_urls)

    next_page_elems = driver.find_elements(By.CSS_SELECTOR, "a.pagination__link")
    for elem in next_page_elems:
        if "Következő" in elem.text:
            return elem.get_attribute("href")
    return None


def main(headless: bool, start_page: int):
    os.makedirs(DATA_DIR, exist_ok=True)

    options = Options()
    if headless:
        options.add_argument("--headless")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 10)

    if start_page <= 1:
        page_url = BASE_URL
    else:
        page_url = f"{BASE_URL}?page={start_page}"
    page_num = start_page

    while page_url:
        print(f"[Page {page_num}] Loading: {page_url}")
        page_url = scrape_listing_page(driver, wait, page_url)
        page_num += 1

    driver.quit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Jarokelo scraper")
    parser.add_argument("--headless", type=lambda x: x.lower() in ("true", "1"), default=True,
                        help="Run browser in headless mode (true/false)")
    parser.add_argument("--start-page", type=int, default=1, help="Page number to start scraping from")
    args = parser.parse_args()

    main(headless=args.headless, start_page=args.start_page)
