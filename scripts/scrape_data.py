import os
import re
import json
from datetime import datetime
import argparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "https://jarokelo.hu/bejelentesek"

def get_monthly_file(data_dir: str, report_date: str) -> str:
    """Return file path based on report's month (YYYY-MM)."""
    # report_date expected as string, e.g. "2025-08-25"
    month_str = datetime.strptime(report_date, "%Y-%m-%d").strftime("%Y-%m")
    return os.path.join(data_dir, f"{month_str}.jsonl")

def load_existing_urls(data_dir, report_date: str) -> set:
    """Load already saved report URLs for the report's month."""
    file_path = get_monthly_file(data_dir, report_date)
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

def save_report(data_dir: str, report: dict, existing_urls: set) -> None:
    """
    Save a report to the monthly JSONL file, organizing entries by date.

    Ordering logic:
    - If the report URL already exists in the current file, it is skipped.
    - If all existing entries in the file have the same date, new reports are always appended to the bottom.
    - Otherwise:
        - If the report's date is newer than or equal to the first line, it is prepended to the top.
        - If the report's date is older than or equal to the last line, it is appended to the bottom.
    - This ensures chronological ordering while handling single-date files or files at the start of scraping consistently.
    """
    if report["url"] in existing_urls:
        return
    existing_urls.add(report["url"])

    file_path = get_monthly_file(data_dir, report["date"])
    new_line = json.dumps(report, ensure_ascii=False) + "\n"

    lines = []
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f, start=1):
                line = line.rstrip("\r\n")
                if not line:
                    continue
                try:
                    json.loads(line)  # validate
                    lines.append(line + "\n")
                except json.JSONDecodeError as e:
                    print(f"[ERROR] Malformed line {i} in {file_path}: {line}")
                    raise

    # Insert new report chronologically
    inserted = False
    report_date = report["date"]
    new_lines = []
    for line in lines:
        line_date = json.loads(line)["date"]
        if not inserted and report_date >= line_date:
            new_lines.append(new_line)
            inserted = True
        new_lines.append(line)
    if not inserted:
        new_lines.append(new_line)  # append if newest

    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

def normalize_date(date_str) -> str:
    """Convert Hungarian date like '2025. szeptember 15.' to 'YYYY-MM-DD'."""
    HU_MONTHS = {
        "január": "01",
        "február": "02",
        "március": "03",
        "április": "04",
        "május": "05",
        "június": "06",
        "július": "07",
        "augusztus": "08",
        "szeptember": "09",
        "október": "10",
        "november": "11",
        "december": "12",
    }
    if isinstance(date_str, list):
        parts = date_str
    else:
        parts = date_str.strip(". ").split()
    year = parts[0].replace(".", "")
    month = HU_MONTHS[parts[1].lower()]
    day = parts[2].replace(".", "")
    return f"{year}-{month}-{day.zfill(2)}"

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

    # Resolution date (if status is "MEGOLDOTT")
    resolution_date = None
    if status and status.upper() == "MEGOLDOTT":
        comment_bodies = driver.find_elements(By.CSS_SELECTOR, "div.comment__body")
        for body in comment_bodies:
            msg_elems = body.find_elements(By.CSS_SELECTOR, "p.comment__message")
            for msg in msg_elems:
                raw_html = msg.get_attribute("innerHTML")
                if re.search(r"lezárta a bejelentést.*Megoldott.*eredménnyel", raw_html, re.DOTALL | re.IGNORECASE):
                    time_elems = body.find_elements(By.CSS_SELECTOR, "time")
                    # Use the first non-empty time element
                    for t in time_elems:
                        time_text = t.text.strip()
                        if not time_text:
                            # Try to extract from innerHTML if .text is empty
                            time_html = t.get_attribute("innerHTML").strip()
                            if time_html:
                                time_text = time_html
                            else:
                                # Fallback: extract from outerHTML using regex
                                outer_html = t.get_attribute("outerHTML")
                                match = re.search(r">([^<]+)<", outer_html)
                                if match:
                                    time_text = match.group(1).strip()
                        if time_text:
                            try:
                                resolution_date = normalize_date(time_text.split()[0:3])  # Only use date part
                                print(f"[DEBUG] Parsed resolution_date: {resolution_date}")
                            except Exception as e:
                                print(f"[DEBUG] Error normalizing date: {e}")
                            break
                    if not resolution_date:
                        print("[DEBUG] No valid <time> text found for resolution_date")
                        raise ValueError("Could not find valid resolution date")
                    break
            if resolution_date:
                break

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
        "images": images,
        "resolution_date": resolution_date,
    }

def scrape_listing_page(driver, wait, page_url: str, global_urls: set, until_date: str = None, stop_on_existing: bool = True, data_dir: str = None) -> tuple[str, bool]:
    """Return next page URL and a flag if we reached an already scraped report or until_date."""
    driver.get(page_url)
    reached_done = False
    links = [a.get_attribute("href") for a in driver.find_elements(By.CSS_SELECTOR, "article.card a.card__media__bg")]

    for link in links:
        if link in global_urls and stop_on_existing:
            reached_done = True
            break

        if link not in global_urls:
            report = scrape_report(driver, wait, link)
            save_report(data_dir, report, global_urls)  # update global set
            if until_date and report["date"] <= until_date:
                reached_done = True
                break

    if reached_done:
        return None, True

    next_page_elems = driver.find_elements(By.CSS_SELECTOR, "a.pagination__link")
    for elem in next_page_elems:
        if "Következő" in elem.text:
            return elem.get_attribute("href"), False
    return None, False


def get_scraping_resume_point(data_dir: str) -> tuple[str, int]:
    """Determine resume point: oldest scraped report date and total saved reports."""
    all_files = sorted(
        [os.path.join(data_dir, f) for f in os.listdir(data_dir) if f.endswith(".jsonl")]
    )
    if not all_files:
        return None, 0

    oldest_date = None
    total = 0
    for f in all_files:
        with open(f, encoding="utf-8") as fh:
            lines = fh.readlines()
            total += len(lines)
            if lines:
                last_date = json.loads(lines[-1])["date"]
                if oldest_date is None or last_date < oldest_date:
                    oldest_date = last_date
    return oldest_date, total

def _get_chrome_options(headless: bool) -> Options:
    options = Options()
    if headless:
        options.add_argument("--headless")
    options.add_experimental_option("excludeSwitches", ["enable-logging", "enable-automation"])
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-sync")
    options.add_argument("--disable-component-update")
    options.add_argument("--log-level=3")
    return options

def main(headless: bool, start_page: int, until_date: str = None, stop_on_existing: bool = True, data_dir: str = None):

    os.makedirs(data_dir, exist_ok=True)

    options = _get_chrome_options(headless=headless)
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 10)

    # --- Prepare global set of already scraped URLs ---
    global_urls = set()
    for f in os.listdir(data_dir):
        if f.endswith(".jsonl"):
            with open(os.path.join(data_dir, f), encoding="utf-8") as fh:
                for line in fh:
                    try:
                        global_urls.add(json.loads(line)["url"])
                    except json.JSONDecodeError:
                        continue

    # --- Determine starting page ---
    if start_page <= 1:
        page_url = BASE_URL
    else:
        page_url = f"{BASE_URL}?page={start_page}"
    page_num = start_page

    # --- Scraping loop ---
    while page_url:
        print(f"[Page {page_num}] Loading: {page_url}")
        # page_url, done = scrape_listing_page(driver, wait, page_url, global_urls, until_date)
        page_url, done = scrape_listing_page(driver, wait, page_url, global_urls, until_date, stop_on_existing=stop_on_existing, data_dir=data_dir)
        if done:
            print(f"Found already-scraped report or reached until-date ({until_date=}) Exiting.")
            break
        page_num += 1

    driver.quit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Járókelő scraper")
    parser.add_argument("--headless", type=str, choices=['true', 'false'], default='true', help="Run browser in headless mode (true/false)")
    parser.add_argument("--start-page", type=int, default=1, help="Page number to start scraping from")
    parser.add_argument("--until-date", type=str, default=None, help="Scrape until this date (YYYY-MM-DD), inclusive")
    parser.add_argument("--continue-scraping", action="store_true", help="Resume automatically based on existing data")
    parser.add_argument("--data-dir", type=str, default="data/raw", help="Directory to store data files")

    args = parser.parse_args()
    
    if args.continue_scraping:
        oldest_date, total = get_scraping_resume_point(data_dir=args.data_dir)
        page = max(total // 8 - 1, 1)
        print(f"Proceeding with scraping from date: {oldest_date} and from page number: {page}")
        main(headless=args.headless, start_page=page, until_date=args.until_date, stop_on_existing=False, data_dir=args.data_dir)
    else:
        main(headless=args.headless, start_page=args.start_page, until_date=args.until_date, stop_on_existing=True, data_dir=args.data_dir)
