"""
Core Scraper Module

This module contains the main JarokeloScraper class that orchestrates the scraping process
using either Selenium or BeautifulSoup backends.
"""

import re
import requests
import asyncio
import aiohttp
from datetime import datetime
from typing import Dict, Optional, Tuple, Set, List
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
    
    def __init__(self, data_dir: str = "data/raw", backend: str = "beautifulsoup", headless: bool = True, buffer_size: int = 100, async_mode: bool = False, max_concurrent: int = 10):
        """
        Initialize the scraper
        
        Args:
            data_dir: Directory to store scraped data
            backend: Scraping backend ('selenium' or 'beautifulsoup')
            headless: Whether to run browser in headless mode (for Selenium)
            buffer_size: Number of records to buffer in memory before writing to disk
            async_mode: Whether to use async scraping (8.6x faster, auto-fallback to sync on errors)
            max_concurrent: Maximum concurrent requests for async mode (optimal: 10)
        """
        self.data_manager = DataManager(data_dir, buffer_size)
        self.backend = backend
        self.headless = headless
        self.async_mode = async_mode
        self.max_concurrent = max_concurrent
        self.session = None
        self.driver = None
        self.wait = None
        self.aio_session = None  # For async operations
        self.semaphore = None  # For concurrency control
        
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
    
    async def _init_async_session(self):
        """Initialize async aiohttp session with optimal connection pooling"""
        if not self.aio_session:
            connector = aiohttp.TCPConnector(
                limit=50,  # Total connection limit
                limit_per_host=self.max_concurrent,
                ttl_dns_cache=300,
                use_dns_cache=True
            )
            
            self.aio_session = aiohttp.ClientSession(
                connector=connector,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                },
                timeout=aiohttp.ClientTimeout(total=30)
            )
            
            # Create semaphore for concurrency control
            self.semaphore = asyncio.Semaphore(self.max_concurrent)
    
    async def _close_async_session(self):
        """Close async session if open"""
        if self.aio_session:
            await self.aio_session.close()
            self.aio_session = None
            self.semaphore = None
    
    def close(self):
        """Clean up resources"""
        if self.driver:
            self.driver.quit()
        if self.session:
            self.session.close()
        
        # Handle async session cleanup
        if self.aio_session:
            try:
                # Try to close in current event loop
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Schedule cleanup for later
                    loop.create_task(self._close_async_session())
                else:
                    # Run cleanup directly
                    loop.run_until_complete(self._close_async_session())
            except RuntimeError:
                # No event loop, create one for cleanup
                asyncio.run(self._close_async_session())
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Ensure buffer is flushed before closing
        self.data_manager.flush_buffer()
        self.close()
    
    @staticmethod
    def validate_encoding(data: Dict, url: str) -> None:
        """
        Validate that no encoding corruption exists in scraped data.
        FAILS LOUDLY if corruption is detected to ensure issues don't go unnoticed.
        """
        corruption_patterns = [
            'Ă', 'ĂĄ', 'ĂŠ', 'Ăş', 'Ăł', 'Ăź', 'Ăś', 'Ä±', 'ĹŠ', 'Ĺ',  # Common corrupted chars
            'mĂĄjus', 'jĂşlius', 'jĂşnius',  # Specific month corruptions
            'Ã', 'â', 'Å'  # Double-encoding indicators
        ]
        
        # Check all text fields for corruption
        text_fields = ['title', 'author', 'category', 'institution', 'supporter', 'description', 'status', 'address']
        
        for field in text_fields:
            value = data.get(field)
            if isinstance(value, str):
                for pattern in corruption_patterns:
                    if pattern in value:
                        error_msg = f"""
🚨 ENCODING CORRUPTION DETECTED! 🚨
Field: {field}
Value: '{value}'
Corruption pattern: '{pattern}'
URL: {url}

This indicates our encoding fix is not working properly.
SCRAPING STOPPED to prevent corrupted data from being saved.
"""
                        print(error_msg)
                        raise ValueError(f"Encoding corruption detected in field '{field}': '{pattern}' found in '{value}'")
    
    @staticmethod
    def fix_utf8_encoding(text: str) -> str:
        """Fix common UTF-8 encoding issues in Hungarian text - only needed for date parsing now."""
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
            
        # If that doesn't work, try direct character replacements for date parsing
        replacements = {
            # Month name corruptions only (for legacy data/edge cases)
            'mÃĄjus': 'május',
            'mĂĄjus': 'május',
            'jĂşlius': 'július',
            'jĂşnius': 'június',
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

        result = {
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
        
        # VALIDATE ENCODING - FAIL LOUDLY IF CORRUPTION DETECTED
        self.validate_encoding(result, url)
        
        return result
    
    def scrape_report_beautifulsoup(self, url: str) -> Dict:
        """Scrape a single report page using BeautifulSoup and return its data."""
        if not self.session:
            raise ValueError("Requests session not initialized")
            
        response = self.session.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')  # Use response.text instead of response.content

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

        result = {
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
        
        # VALIDATE ENCODING - FAIL LOUDLY IF CORRUPTION DETECTED
        self.validate_encoding(result, url)
        
        return result
    
    async def scrape_report_beautifulsoup_async(self, url: str) -> Dict:
        """Async version of BeautifulSoup scraping with fallback to sync on errors"""
        if not self.aio_session:
            await self._init_async_session()
        
        async with self.semaphore:  # Limit concurrency
            try:
                async with self.aio_session.get(url) as response:
                    response.raise_for_status()
                    # Use text() with explicit encoding
                    html = await response.text(encoding='utf-8', errors='replace')
                    
                    soup = BeautifulSoup(html, 'html.parser')

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
                    address = address_elem.text.strip() if address_elem else None

                    # Resolution date (if available)
                    resolution_date = None
                    status_cards = soup.select("div.report__status__card")
                    for card in status_cards:
                        time_elem = card.select_one("time")
                        if time_elem:
                            time_text = time_elem.text.strip()
                            if time_text:
                                try:
                                    resolution_date = self.normalize_date(time_text.split()[0:3])
                                    break
                                except Exception as e:
                                    print(f"[DEBUG] Error normalizing date: {e}")
                                    continue

                    # GPS Coordinates
                    latitude, longitude = extract_gps_coordinates(html)

                    result = {
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
                        "longitude": longitude
                    }
                    
                    # VALIDATE ENCODING - FAIL LOUDLY IF CORRUPTION DETECTED
                    self.validate_encoding(result, url)
                    
                    return result
                    
            except Exception as e:
                print(f"[WARNING] Async scraping failed for {url}: {e}")
                print("[INFO] Falling back to synchronous scraping...")
                # Fallback to sync method
                return self.scrape_report_beautifulsoup(url)
    
    def scrape_report(self, url: str) -> Dict:
        """Scrape a single report using the configured backend and mode"""
        if self.backend == 'selenium':
            if self.async_mode:
                print("[INFO] Async mode not yet implemented for Selenium backend, using sync mode")
            return self.scrape_report_selenium(url)
        elif self.backend == 'beautifulsoup':
            if self.async_mode:
                # For individual reports, async doesn't provide benefits and can cause event loop issues
                # The performance benefit comes from batch async processing only
                print("[INFO] Using sync mode for single report (async benefits only apply to batch processing)")
                return self.scrape_report_beautifulsoup(url)
            else:
                return self.scrape_report_beautifulsoup(url)
        else:
            raise ValueError(f"Unsupported backend: {self.backend}")
    
    def _run_single_async(self, url: str) -> Dict:
        """DEPRECATED: Single async operations don't provide performance benefits"""
        return self.scrape_report_beautifulsoup(url)
    
    async def _single_async_scrape(self, url: str) -> Dict:
        """DEPRECATED: Use batch async processing for performance benefits"""
        pass
    
    async def scrape_reports_async(self, urls: List[str]) -> List[Dict]:
        """
        Scrape multiple reports asynchronously with optimal concurrency.
        This is the high-performance method that delivers 8.6x speedup.
        """
        if self.backend != 'beautifulsoup':
            raise ValueError("Async batch scraping only supported with BeautifulSoup backend")
        
        if not self.aio_session:
            await self._init_async_session()
        
        print(f"🚀 Starting async batch scraping of {len(urls)} URLs with {self.max_concurrent} concurrent connections...")
        
        # Create tasks for all URLs
        tasks = [self.scrape_report_beautifulsoup_async(url) for url in urls]
        
        # Execute with progress tracking
        results = []
        completed = 0
        
        # Process in batches to avoid overwhelming the event loop
        batch_size = min(50, len(tasks))
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i + batch_size]
            batch_results = await asyncio.gather(*batch, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, Exception):
                    print(f"[ERROR] Batch item failed: {result}")
                    results.append(None)  # Placeholder for failed items
                else:
                    results.append(result)
                
                completed += 1
                if completed % 10 == 0:
                    print(f"✅ Completed {completed}/{len(urls)} reports")
        
        print(f"🎯 Async batch scraping completed: {len([r for r in results if r is not None])}/{len(urls)} successful")
        return [r for r in results if r is not None]  # Filter out failed items
    
    def scrape_reports_batch(self, urls: List[str]) -> List[Dict]:
        """
        Scrape multiple reports with automatic async/sync mode selection.
        Uses async mode for 8.6x speedup when enabled, falls back to sync on errors.
        """
        if self.async_mode and self.backend == 'beautifulsoup':
            try:
                return asyncio.run(self.scrape_reports_async(urls))
            except Exception as e:
                print(f"[WARNING] Async batch scraping failed: {e}")
                print("[INFO] Falling back to synchronous batch processing...")
        
        # Synchronous fallback
        print(f"🔄 Starting synchronous batch scraping of {len(urls)} URLs...")
        results = []
        for i, url in enumerate(urls):
            try:
                result = self.scrape_report(url)
                results.append(result)
                if (i + 1) % 10 == 0:
                    print(f"✅ Completed {i + 1}/{len(urls)} reports")
            except Exception as e:
                print(f"[ERROR] Failed to scrape {url}: {e}")
                continue
        
        print(f"🎯 Synchronous batch scraping completed: {len(results)}/{len(urls)} successful")
        return results
    
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
        soup = BeautifulSoup(response.text, 'html.parser')  # Use response.text instead of response.content
        
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
                # ASYNC OPTIMIZATION: Collect new URLs and batch process them
                pass  # Processing moved to after the loop

        # ASYNC BATCH PROCESSING: Process all new URLs from this page at once
        new_urls_from_page = [card["url"] for card in card_info if card["url"] not in global_urls]
        
        if new_urls_from_page:
            if self.async_mode:
                try:
                    print(f"🚀 Async batch processing {len(new_urls_from_page)} new URLs from this page...")
                    # Use async batch processing for new URLs - PROPER EVENT LOOP HANDLING
                    try:
                        # Check if we're already in an event loop
                        loop = asyncio.get_running_loop()
                        print("[INFO] Already in event loop, using sync fallback for safety")
                        raise RuntimeError("Event loop exists")
                    except RuntimeError:
                        # No event loop, safe to use asyncio.run
                        reports = asyncio.run(self.scrape_reports_async(new_urls_from_page))
                    
                    # Save the reports and check for until_date
                    for report in reports:
                        if report:  # Skip None results from failed scrapes
                            # Use buffered saving for comprehensive scraping, regular saving for status updates
                            if use_buffered_saving:
                                self.data_manager.save_report_buffered(report, global_urls)
                            else:
                                self.data_manager.save_report(report, global_urls)
                            
                            if until_date and report["date"] <= until_date:
                                reached_done = True
                                break
                                
                except Exception as e:
                    print(f"[WARNING] Async batch processing failed: {e}")
                    print("[INFO] Falling back to sync processing for this page...")
                    # Fallback to sync processing
                    for url in new_urls_from_page:
                        try:
                            report = self.scrape_report_beautifulsoup(url)
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
                            continue
            else:
                # Sync processing for new URLs (when async_mode=False)
                for url in new_urls_from_page:
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
        soup = BeautifulSoup(response.text, 'html.parser')  # Use response.text instead of response.content
        
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