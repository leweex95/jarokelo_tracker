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
    
    def __init__(self, data_dir: str = "data/raw", backend: str = "beautifulsoup", headless: bool = True):
        """
        Initialize the scraper
        
        Args:
            data_dir: Directory to store scraped data
            backend: Scraping backend ('selenium' or 'beautifulsoup')
            headless: Whether to run browser in headless mode (for Selenium)
        """
        self.data_manager = DataManager(data_dir)
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
        self.close()
    
    @staticmethod
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
        date = self.normalize_date(date_elem[0].text) if date_elem else None

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
        date = self.normalize_date(date_elem.text.strip()) if date_elem else None

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
    
    def scrape_listing_page_selenium(self, page_url: str, global_urls: Set[str], 
                                   until_date: Optional[str] = None, 
                                   stop_on_existing: bool = True) -> Tuple[Optional[str], bool]:
        """Return next page URL and a flag if we reached an already scraped report or until_date."""
        if not self.driver:
            raise ValueError("Selenium not initialized")
            
        self.driver.get(page_url)
        reached_done = False
        links = [a.get_attribute("href") for a in self.driver.find_elements(By.CSS_SELECTOR, "article.card a.card__media__bg")]

        for link in links:
            if link in global_urls and stop_on_existing:
                reached_done = True
                break

            if link not in global_urls:
                report = self.scrape_report_selenium(link)
                self.data_manager.save_report(report, global_urls)  # update global set
                if until_date and report["date"] <= until_date:
                    reached_done = True
                    break

        if reached_done:
            return None, True

        next_page_elems = self.driver.find_elements(By.CSS_SELECTOR, "a.pagination__link")
        for elem in next_page_elems:
            if "Következő" in elem.text:
                return elem.get_attribute("href"), False
        return None, False
    
    def scrape_listing_page_beautifulsoup(self, page_url: str, global_urls: Set[str], 
                                        until_date: Optional[str] = None, 
                                        stop_on_existing: bool = True) -> Tuple[Optional[str], bool]:
        """Return next page URL and a flag if we reached an already scraped report or until_date."""
        if not self.session:
            raise ValueError("Requests session not initialized")
            
        response = self.session.get(page_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        reached_done = False
        links = [a.get("href") for a in soup.select("article.card a.card__media__bg")]

        for link in links:
            if link in global_urls and stop_on_existing:
                reached_done = True
                break

            if link not in global_urls:
                report = self.scrape_report_beautifulsoup(link)
                self.data_manager.save_report(report, global_urls)  # update global set
                if until_date and report["date"] <= until_date:
                    reached_done = True
                    break

        if reached_done:
            return None, True

        next_page_elems = soup.select("a.pagination__link")
        for elem in next_page_elems:
            if "Következő" in elem.text:
                return elem.get("href"), False
        return None, False
    
    def scrape_listing_page(self, page_url: str, global_urls: Set[str], 
                           until_date: Optional[str] = None, 
                           stop_on_existing: bool = True) -> Tuple[Optional[str], bool]:
        """Scrape a listing page using the configured backend"""
        if self.backend == 'selenium':
            return self.scrape_listing_page_selenium(page_url, global_urls, until_date, stop_on_existing)
        elif self.backend == 'beautifulsoup':
            return self.scrape_listing_page_beautifulsoup(page_url, global_urls, until_date, stop_on_existing)
        else:
            raise ValueError(f"Unsupported backend: {self.backend}")
    
    def scrape(self, start_page: int = 1, until_date: Optional[str] = None, 
               stop_on_existing: bool = True, continue_scraping: bool = False):
        """
        Main scraping method
        
        Args:
            start_page: Page number to start scraping from
            until_date: Scrape until this date (YYYY-MM-DD), inclusive
            stop_on_existing: Whether to stop when encountering existing reports
            continue_scraping: Whether to resume from where we left off
        """
        
        # Load existing URLs
        global_urls = self.data_manager.load_all_existing_urls()
        
        # Determine starting page
        if continue_scraping:
            oldest_date, total = self.data_manager.get_scraping_resume_point()
            page = max(total // 8 - 1, 1)
            stop_on_existing = False
            print(f"Resuming scraping from date: {oldest_date} and from page number: {page}")
        else:
            page = start_page
        
        # Determine starting URL
        if page <= 1:
            page_url = self.BASE_URL
        else:
            page_url = f"{self.BASE_URL}?page={page}"
        
        # Main scraping loop
        while page_url:
            print(f"[Page {page}] Loading: {page_url}")
            page_url, done = self.scrape_listing_page(
                page_url, global_urls, until_date, stop_on_existing
            )
            if done:
                print(f"Found already-scraped report or reached until-date ({until_date=}) Exiting.")
                break
            page += 1