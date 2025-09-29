"""
Core Scraper Module

This module contains the main JarokeloScraper class that orchestrates the scraping process
using either Selenium or BeautifulSoup backends.
"""

import re
import requests
from datetime import datetime
from typing import Dict, Optional, Tuple, Set
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .gps_extractor import extract_gps_coordinates
from .data_manager import DataManager


class JarokeloScraper:
    """Main scraper class for Járókelő municipal issue tracking system"""
    
    BASE_URL = "https://jarokelo.hu/bejelentesek"
    
    def __init__(self, data_dir: str = "data/raw", backend: str = "beautifulsoup", headless: bool = True, buffer_size: int = 100):
        """
        Initialize the scraper
        
        Args:
            data_dir: Directory to store scraped data
            backend: Scraping backend ('selenium' or 'beautifulsoup')
            headless: Whether to run browser in headless mode (for Selenium)
            buffer_size: Number of records to buffer in memory before writing to disk
        """
        self.data_manager = DataManager(data_dir, buffer_size)
        self.backend = backend
        self.headless = headless
        self.session = None
        self.driver = None
        self.wait = None
        
        if backend == 'selenium':
            self._init_selenium()
        elif backend == 'beautifulsoup':
            self._init_requests()
        else:
            raise ValueError(f"Unsupported backend: {backend}")
    
    def _init_selenium(self):
        """Initialize Selenium WebDriver"""
        options = Options()
        if self.headless:
            options.add_argument("--headless")
        options.add_experimental_option("excludeSwitches", ["enable-logging", "enable-automation"])
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-background-networking")
        options.add_argument("--disable-sync")
        options.add_argument("--disable-component-update")
        options.add_argument("--log-level=3")
        # Ensure proper UTF-8 encoding
        options.add_argument("--lang=hu-HU")
        options.add_argument("--accept-lang=hu-HU,hu,en-US,en")
        
        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 10)
    
    def _init_requests(self):
        """Initialize requests session"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def close(self):
        """Clean up resources"""
        if self.driver:
            self.driver.quit()
        if self.session:
            self.session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Ensure buffer is flushed before closing
        self.data_manager.flush_buffer()
        self.close()
    
    @staticmethod
    def fix_utf8_encoding(text: str) -> str:
        """Fix common UTF-8 encoding issues in Hungarian text."""
        if not text:
            return text
            
        # Try to fix double-encoded UTF-8 issues
        try:
            # First try: if text is already double-encoded, decode it properly
            # This handles cases like "mÃĄjus" -> "május"
            if 'Ã' in text or 'Å' in text or 'â' in text:
                # Try to encode as latin-1 and decode as utf-8
                fixed = text.encode('latin-1').decode('utf-8')
                return fixed
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
            
        # If that doesn't work, try direct character replacements
        replacements = {
            'mÃĄjus': 'május',
            'mãąjus': 'május', 
            'jãšlius': 'július',
            'jรบnius': 'június',
            'mããšius': 'március',
            'febriãšr': 'február',
            'mรกrcius': 'március',
            'ãกprilis': 'április',
            'oktรณber': 'október',
            'novembรฉr': 'november',
            'decembรฉr': 'december',
            # Additional common corruptions
            'jÃบnius': 'június',
            'jÃºlius': 'július',
            'mÃกrcius': 'március',
            'ÃกpriÄบlis': 'április',
            'oktÃ³ber': 'október',
            'novembÃ©r': 'november',
            'decembÃ©r': 'december'
        }
        
        for corrupted, correct in replacements.items():
            text = text.replace(corrupted, correct)
            
        return text

    @staticmethod
    def normalize_date(date_str, url: str = None) -> str:
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
        try:
            if isinstance(date_str, list):
                parts = date_str
            else:
                # Fix encoding issues first
                fixed_date_str = JarokeloScraper.fix_utf8_encoding(date_str)
                parts = fixed_date_str.strip(". ").split()
            
            if len(parts) < 3:
                raise ValueError(f"Invalid date format: '{date_str}' - expected 3 parts, got {len(parts)}")
            
            year = parts[0].replace(".", "")
            month_name = JarokeloScraper.fix_utf8_encoding(parts[1]).lower()
            
            if month_name not in HU_MONTHS:
                # Print detailed error information
                print(f"[ERROR] Unknown Hungarian month: '{month_name}' (original: '{parts[1]}')")
                print(f"[ERROR] Full date string: '{date_str}'")
                print(f"[ERROR] Date parts: {parts}")
                if url:
                    print(f"[ERROR] URL: {url}")
                print(f"[ERROR] Available months: {list(HU_MONTHS.keys())}")
                
                raise KeyError(f"Unknown Hungarian month: '{month_name}' (from '{date_str}')")
            
            month = HU_MONTHS[month_name]
            day = parts[2].replace(".", "")
            return f"{year}-{month}-{day.zfill(2)}"
            
        except Exception as e:
            print(f"[ERROR] Failed to normalize date: '{date_str}'")
            if url:
                print(f"[ERROR] URL where error occurred: {url}")
            raise
    
    def scrape_report_selenium(self, url: str) -> Dict:
        """Scrape a single report page using Selenium and return its data."""
        if not self.driver or not self.wait:
            raise ValueError("Selenium not initialized")
            
        self.driver.execute_script("window.open(arguments[0]);", url)
        self.driver.switch_to.window(self.driver.window_handles[1])

        title = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "h1.report__title"))).text

        # Author
        author_elem = self.driver.find_elements(By.CSS_SELECTOR, "div.report__reporter div.report__author a")
        if author_elem:
            author = author_elem[0].text
            author_profile = author_elem[0].get_attribute("href")
        else:
            anon_elem = self.driver.find_elements(By.CSS_SELECTOR, "div.report__reporter div.report__author")
            author = anon_elem[0].text.strip() if anon_elem else None
            author_profile = None

        # Date, category, institution, supporter, description
        date_elem = self.driver.find_elements(By.CSS_SELECTOR, "time.report__date")
        date = self.normalize_date(date_elem[0].text, url) if date_elem else None

        category_elem = self.driver.find_elements(By.CSS_SELECTOR, "div.report__category a")
        category = category_elem[0].text if category_elem else None

        institution_elem = self.driver.find_elements(By.CSS_SELECTOR, "div.report__institution a")
        institution = institution_elem[0].text if institution_elem else None

        supporter_elem = self.driver.find_elements(By.CSS_SELECTOR, "span.report__partner__about")
        supporter = supporter_elem[0].text if supporter_elem else None

        description_elem = self.driver.find_elements(By.CSS_SELECTOR, "p.report__description")
        description = description_elem[0].text if description_elem else None

        # Status
        status_elem = self.driver.find_elements(By.CSS_SELECTOR, "span.badge")
        status = status_elem[0].text.strip() if status_elem else None

        # Address
        address_elem = self.driver.find_elements(By.CSS_SELECTOR, "address.report__location__address")
        if address_elem:
            city = address_elem[0].text.split("\n")[0].strip() if address_elem[0].text else None
            district_elem = address_elem[0].find_elements(By.CSS_SELECTOR, "span.report__location__address__district")
            district = district_elem[0].text.strip() if district_elem else None
            address = ", ".join(filter(None, [city, district]))
        else:
            address = None

        # Resolution date (if status is "MEGOLDOTT")
        resolution_date = None
        if status and status.upper() == "MEGOLDOTT":
            comment_bodies = self.driver.find_elements(By.CSS_SELECTOR, "div.comment__body")
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
                                    resolution_date = self.normalize_date(time_text.split()[0:3])  # Only use date part
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

        # GPS Coordinates
        page_source = self.driver.page_source
        latitude, longitude = extract_gps_coordinates(page_source, self.driver)

        self.driver.close()
        self.driver.switch_to.window(self.driver.window_handles[0])

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
            "resolution_date": resolution_date,
            "latitude": latitude,
            "longitude": longitude,
        }
    
    def scrape_report_beautifulsoup(self, url: str) -> Dict:
        """Scrape a single report page using BeautifulSoup and return its data."""
        if not self.session:
            raise ValueError("Requests session not initialized")
            
        response = self.session.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Title
        title_elem = soup.select_one("h1.report__title")
        title = title_elem.text.strip() if title_elem else None

        # Author
        author_elem = soup.select_one("div.report__reporter div.report__author a")
        if author_elem:
            author = author_elem.text.strip()
            author_profile = author_elem.get("href")
        else:
            anon_elem = soup.select_one("div.report__reporter div.report__author")
            author = anon_elem.text.strip() if anon_elem else None
            author_profile = None

        # Date
        date_elem = soup.select_one("time.report__date")
        date = self.normalize_date(date_elem.text.strip(), url) if date_elem else None

        # Category
        category_elem = soup.select_one("div.report__category a")
        category = category_elem.text.strip() if category_elem else None

        # Institution
        institution_elem = soup.select_one("div.report__institution a")
        institution = institution_elem.text.strip() if institution_elem else None

        # Supporter
        supporter_elem = soup.select_one("span.report__partner__about")
        supporter = supporter_elem.text.strip() if supporter_elem else None

        # Description
        description_elem = soup.select_one("p.report__description")
        description = description_elem.text.strip() if description_elem else None

        # Status
        status_elem = soup.select_one("span.badge")
        status = status_elem.text.strip() if status_elem else None

        # Address
        address_elem = soup.select_one("address.report__location__address")
        if address_elem:
            city = address_elem.text.split("\n")[0].strip() if address_elem.text else None
            district_elem = address_elem.select_one("span.report__location__address__district")
            district = district_elem.text.strip() if district_elem else None
            address = ", ".join(filter(None, [city, district]))
        else:
            address = None

        # Resolution date (if status is "MEGOLDOTT")
        resolution_date = None
        if status and status.upper() == "MEGOLDOTT":
            comment_bodies = soup.select("div.comment__body")
            for body in comment_bodies:
                msg_elems = body.select("p.comment__message")
                for msg in msg_elems:
                    raw_html = str(msg)
                    if re.search(r"lezárta a bejelentést.*Megoldott.*eredménnyel", raw_html, re.DOTALL | re.IGNORECASE):
                        time_elems = body.select("time")
                        for t in time_elems:
                            time_text = t.text.strip()
                            if not time_text and t.string:
                                time_text = t.string.strip()
                            if time_text:
                                try:
                                    resolution_date = self.normalize_date(time_text.split()[0:3])
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

        # GPS Coordinates
        latitude, longitude = extract_gps_coordinates(response.text)

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
            "resolution_date": resolution_date,
            "latitude": latitude,
            "longitude": longitude,
        }
    
    def scrape_report(self, url: str) -> Dict:
        """Scrape a single report using the configured backend"""
        if self.backend == 'selenium':
            return self.scrape_report_selenium(url)
        elif self.backend == 'beautifulsoup':
            return self.scrape_report_beautifulsoup(url)
        else:
            raise ValueError(f"Unsupported backend: {self.backend}")
    
    def extract_listing_info_selenium(self, page_url: str) -> list:
        """Extract URL and status from listing page cards using Selenium"""
        if not self.driver:
            raise ValueError("Selenium not initialized")
            
        self.driver.get(page_url)
        
        cards = self.driver.find_elements(By.CSS_SELECTOR, "article.card")
        card_info = []
        
        for card in cards:
            # Extract URL
            link_elem = card.find_elements(By.CSS_SELECTOR, "a.card__media__bg")
            if not link_elem:
                continue
            url = link_elem[0].get_attribute("href")
            
            # Extract status from badge
            status = None
            status_elems = card.find_elements(By.CSS_SELECTOR, "span.badge")
            for elem in status_elems:
                # Skip comment badges
                if "badge--comment" not in elem.get_attribute("class"):
                    status = elem.text.strip()
                    break
            
            card_info.append({"url": url, "status": status})
        
        return card_info

    def scrape_listing_page_selenium(self, page_url: str, global_urls: Set[str], 
                                   until_date: Optional[str] = None, 
                                   stop_on_existing: bool = True,
                                   use_buffered_saving: bool = False) -> Tuple[Optional[str], bool]:
        """Return next page URL and a flag if we reached an already scraped report or until_date."""
        if not self.driver:
            raise ValueError("Selenium not initialized")
            
        # Extract all card info (URL + status) from listing page
        card_info = self.extract_listing_info_selenium(page_url)
        reached_done = False

        for card in card_info:
            url = card["url"]
            current_status = card["status"]
            
            if url in global_urls:
                # Existing record - check if status needs updating
                _, existing_record, _ = self.data_manager.find_record_by_url(url)
                old_status = existing_record.get("status") if existing_record else None
                
                # Check if we need full re-scrape (e.g., for resolution_date when status → MEGOLDOTT)
                if self.data_manager.needs_full_rescrape(old_status, current_status):
                    print(f"Status change requires full re-scrape: {url} ({old_status} → {current_status})")
                    print(f"[DEBUG] This is expected when status changes to/from 'MEGOLDOTT' to capture resolution_date")
                    # Perform full scrape and update the record
                    try:
                        updated_report = self.scrape_report_selenium(url)
                        # Replace the existing record with the updated one
                        self.data_manager.replace_record(url, updated_report)
                        print(f"Successfully updated record for {url}")
                    except Exception as e:
                        print(f"ERROR: Failed to scrape report during status update: {url}")
                        print(f"Error details: {str(e)}")
                        print(f"[INFO] Continuing with next report...")
                        continue  # Skip this report and continue with the next one
                elif self.data_manager.update_status_if_changed(url, current_status):
                    print(f"Updated status for {url}: {current_status}")
                
                if stop_on_existing:
                    reached_done = True
                    break
            else:
                # New record - perform full scraping
                try:
                    report = self.scrape_report_selenium(url)
                    # Use buffered saving for comprehensive scraping, regular saving for status updates
                    if use_buffered_saving:
                        self.data_manager.save_report_buffered(report, global_urls)
                    else:
                        self.data_manager.save_report(report, global_urls)
                    if until_date and report["date"] <= until_date:
                        reached_done = True
                        break
                except Exception as e:
                    print(f"ERROR: Failed to scrape new report: {url}")
                    print(f"Error details: {str(e)}")
                    continue  # Skip this report and continue with the next one

        if reached_done:
            return None, True

        next_page_elems = self.driver.find_elements(By.CSS_SELECTOR, "a.pagination__link")
        for elem in next_page_elems:
            if "Következő" in elem.text:
                href = elem.get_attribute("href")
                # Convert relative URLs to absolute
                if href and href.startswith("/"):
                    href = "https://jarokelo.hu" + href
                return href, False
        return None, False
    
    def extract_listing_info_beautifulsoup(self, page_url: str) -> list:
        """Extract URL and status from listing page cards using BeautifulSoup"""
        if not self.session:
            raise ValueError("Requests session not initialized")
            
        response = self.session.get(page_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        cards = soup.select("article.card")
        card_info = []
        
        for card in cards:
            # Extract URL
            link_elem = card.select_one("a.card__media__bg")
            if not link_elem:
                continue
            url = link_elem.get("href")
            
            # Extract status from badge
            status = None
            status_elems = card.select("span.badge")
            for elem in status_elems:
                # Skip comment badges
                if "badge--comment" not in elem.get("class", []):
                    status = elem.text.strip()
                    break
            
            card_info.append({"url": url, "status": status})
        
        return card_info

    def scrape_listing_page_beautifulsoup(self, page_url: str, global_urls: Set[str], 
                                        until_date: Optional[str] = None, 
                                        stop_on_existing: bool = True,
                                        use_buffered_saving: bool = False) -> Tuple[Optional[str], bool]:
        """Return next page URL and a flag if we reached an already scraped report or until_date."""
        if not self.session:
            raise ValueError("Requests session not initialized")
            
        # Extract all card info (URL + status) from listing page
        card_info = self.extract_listing_info_beautifulsoup(page_url)
        reached_done = False

        for card in card_info:
            url = card["url"]
            current_status = card["status"]
            
            if url in global_urls:
                # Existing record - check if status needs updating
                _, existing_record, _ = self.data_manager.find_record_by_url(url)
                old_status = existing_record.get("status") if existing_record else None
                
                # Check if we need full re-scrape (e.g., for resolution_date when status → MEGOLDOTT)
                if self.data_manager.needs_full_rescrape(old_status, current_status):
                    print(f"Status change requires full re-scrape: {url} ({old_status} → {current_status})")
                    print(f"[DEBUG] This is expected when status changes to/from 'MEGOLDOTT' to capture resolution_date")
                    # Perform full scrape and update the record
                    try:
                        updated_report = self.scrape_report_beautifulsoup(url)
                        # Replace the existing record with the updated one
                        self.data_manager.replace_record(url, updated_report)
                        print(f"Successfully updated record for {url}")
                    except Exception as e:
                        print(f"ERROR: Failed to scrape report during status update: {url}")
                        print(f"Error details: {str(e)}")
                        print(f"[INFO] Continuing with next report...")
                        continue  # Skip this report and continue with the next one
                elif self.data_manager.update_status_if_changed(url, current_status):
                    print(f"Updated status for {url}: {current_status}")
                
                if stop_on_existing:
                    reached_done = True
                    break
            else:
                # New record - perform full scraping
                try:
                    report = self.scrape_report_beautifulsoup(url)
                    # Use buffered saving for comprehensive scraping, regular saving for status updates
                    if use_buffered_saving:
                        self.data_manager.save_report_buffered(report, global_urls)
                    else:
                        self.data_manager.save_report(report, global_urls)
                    if until_date and report["date"] <= until_date:
                        reached_done = True
                        break
                except Exception as e:
                    print(f"ERROR: Failed to scrape new report: {url}")
                    print(f"Error details: {str(e)}")
                    continue  # Skip this report and continue with the next one

        if reached_done:
            return None, True

        # Get pagination info - need to fetch the page again
        response = self.session.get(page_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        next_page_elems = soup.select("a.pagination__link")
        for elem in next_page_elems:
            if "Következő" in elem.text:
                href = elem.get("href")
                # Convert relative URLs to absolute
                if href and href.startswith("/"):
                    href = "https://jarokelo.hu" + href
                return href, False
        return None, False
    
    def scrape_listing_page(self, page_url: str, global_urls: Set[str], 
                           until_date: Optional[str] = None, 
                           stop_on_existing: bool = True,
                           use_buffered_saving: bool = False) -> Tuple[Optional[str], bool]:
        """Scrape a listing page using the configured backend"""
        if self.backend == 'selenium':
            return self.scrape_listing_page_selenium(page_url, global_urls, until_date, stop_on_existing, use_buffered_saving)
        elif self.backend == 'beautifulsoup':
            return self.scrape_listing_page_beautifulsoup(page_url, global_urls, until_date, stop_on_existing, use_buffered_saving)
        else:
            raise ValueError(f"Unsupported backend: {self.backend}")
    
    def scrape(self, start_page: int = 1, until_date: Optional[str] = None, 
               stop_on_existing: bool = True, continue_scraping: bool = False,
               update_existing_status: bool = False):
        """
        Main scraping method
        
        Args:
            start_page: Page number to start scraping from
            until_date: Scrape until this date (YYYY-MM-DD), inclusive
            stop_on_existing: Whether to stop when encountering existing reports
            continue_scraping: Whether to resume from where we left off
            update_existing_status: Whether to update status of existing records
        """
        
        # Load existing URLs
        global_urls = self.data_manager.load_all_existing_urls()
        
        # Determine if we should use buffered saving (for comprehensive scraping)
        use_buffered_saving = not update_existing_status
        if use_buffered_saving:
            print(f"Using buffered saving (buffer size: {self.data_manager.buffer_size}) for performance")
        
        # Determine starting page and behavior
        if continue_scraping:
            oldest_date, total = self.data_manager.get_scraping_resume_point()
            page = max(total // 8 - 1, 1)
            stop_on_existing = False
            print(f"Resuming scraping from date: {oldest_date} and from page number: {page}")
        elif update_existing_status:
            page = start_page
            stop_on_existing = False  # Don't stop on existing when updating status
            print(f"Status update mode: Will check and update existing record statuses")
        else:
            page = start_page
        
        # Determine starting URL
        if page <= 1:
            page_url = self.BASE_URL
        else:
            page_url = f"{self.BASE_URL}?page={page}"
        
        # Main scraping loop
        try:
            while page_url:
                print(f"[Page {page}] Loading: {page_url}")
                page_url, done = self.scrape_listing_page(
                    page_url, global_urls, until_date, stop_on_existing, use_buffered_saving
                )
                if done:
                    print(f"Found already-scraped report or reached until-date ({until_date=}) Exiting.")
                    break
                page += 1
        finally:
            # Always flush buffer at the end of scraping
            if use_buffered_saving:
                print("Scraping complete. Flushing remaining buffer...")
                self.data_manager.flush_buffer()