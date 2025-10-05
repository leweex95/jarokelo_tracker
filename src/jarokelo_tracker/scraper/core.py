"""
Core Scraper Module

This module contains the main JarokeloScraper class that orchestrates the scraping process
using BeautifulSoup backend only.
"""

import re
import os
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, Set, List
from bs4 import BeautifulSoup

from .gps_extractor import extract_gps_coordinates
from .data_manager import DataManager


class JarokeloScraper:
    """Main scraper class for Járókelő municipal issue tracking system"""
    
    BASE_URL = "https://jarokelo.hu/bejelentesek"
    
    def __init__(self, data_dir: str = "data/raw", buffer_size: int = 50):
        """
        Initialize the scraper
        
        Args:
            data_dir: Directory to store scraped data
            buffer_size: Number of records to buffer in memory before writing to disk (default reduced for CI stability)
        """
        self.data_manager = DataManager(data_dir, buffer_size)
        self.session = None
        self._init_requests()
    
    def _init_requests(self):
        """Initialize requests session"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def close(self):
        """Clean up resources"""
        if self.session:
            self.session.close()
    
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
    def normalize_date(date_str: str, url: Optional[str] = None) -> str:
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
    
    def scrape_report(self, url: str, resolution_focus: bool = False) -> Dict:
        """
        Scrape a single report page using BeautifulSoup and return its data.
        
        Args:
            url: URL to scrape
            resolution_focus: If True, optimizes for resolution date extraction
        """
        if not self.session:
            raise ValueError("Requests session not initialized")
            
        response = self.session.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')  # Use response.text instead of response.content
        
        # For resolution_focus, we can optimize by only looking for status and resolution_date
        if resolution_focus:
            # Get existing record data first to preserve other fields
            _, existing_record, _ = self.data_manager.find_record_by_url(url)
            if existing_record:
                # Status - find the first non-comment badge
                status_elems = soup.select("span.badge")
                status = None
                for elem in status_elems:
                    elem_class = elem.get("class", [])
                    if isinstance(elem_class, str):
                        elem_class = [elem_class]
                    if not any("badge--comment" in c for c in elem_class):
                        status = elem.text.strip()
                        break
                
                if status is None:
                    print(f"[ERROR] Status extraction failed for report: {url}")
                    print(f"[DEBUG] Raw HTML snippet for report:")
                    print(response.text[:1000])
                
                # Resolution date (if available) - search comments for resolution pattern
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
                                    if time_text:
                                        try:
                                            # Use only first 3 parts of date
                                            date_parts = time_text.split()[0:3]
                                            resolution_date = self.normalize_date(date_parts)
                                            break
                                        except Exception as e:
                                            print(f"[DEBUG] Error normalizing date '{time_text}': {e}")
                                            continue
                                if resolution_date:
                                    break
                        if resolution_date:
                            break
                
                # First Authority Response Date (for resolution_focus updates)
                first_authority_response_date = self.extract_first_authority_response_date(soup)
                
                # Update only necessary fields
                result = existing_record.copy()
                original_status = existing_record.get("status") if existing_record else None
                original_resolution = existing_record.get("resolution_date") if existing_record else None
                result["status"] = status
                result["resolution_date"] = resolution_date
                result["first_authority_response_date"] = first_authority_response_date
                # Only print if status or resolution_date actually changes, and use tab for formatting
                if (original_status != status) or (original_resolution != resolution_date):
                    print(f"\tResolution date focus: {url} -> original_status={original_status}, new_status={status}, original_resolution_date={original_resolution}, new_resolution_date={resolution_date}")
                return result
        
        # Full scraping (either not resolution_focus or no existing record found)
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

        # Status - find the first non-comment badge
        status_elems = soup.select("span.badge")
        status = None
        for elem in status_elems:
            elem_class = elem.get("class", [])
            if isinstance(elem_class, str):
                elem_class = [elem_class]
            if not any("badge--comment" in c for c in elem_class):
                status = elem.text.strip()
                break
                
        if status is None:
            print(f"[ERROR] Status extraction failed for report: {url}")
            print(f"[DEBUG] Raw HTML snippet for report:")
            print(response.text[:1000])

        # Address
        address_elem = soup.select_one("address.report__location__address")
        if address_elem:
            city = address_elem.text.split("\n")[0].strip() if address_elem.text else None
            district_elem = address_elem.select_one("span.report__location__address__district")
            district = district_elem.text.strip() if district_elem else None
            address = ", ".join(filter(None, [city, district]))
        else:
            address = None

        # Resolution date extraction: find resolution date from comments
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
                            if time_text:
                                try:
                                    # Use only first 3 parts of date (year, month, day)
                                    date_parts = time_text.split()[0:3]
                                    resolution_date = self.normalize_date(date_parts)
                                    break
                                except Exception as e:
                                    print(f"[DEBUG] Error normalizing resolution date '{time_text}': {e}")
                                    continue
                        if resolution_date:
                            break
                if resolution_date:
                    break

        # First Authority Response Date
        first_authority_response_date = self.extract_first_authority_response_date(soup)

        # GPS Coordinates
        latitude, longitude = extract_gps_coordinates(response.text)

        result = {
            "url": url,
            "title": title,
            "author": author,
            "author_profile": author_profile,
            "date": date,
            "category": category,
            "first_authority_response_date": first_authority_response_date,
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

        # Prevent encoding issues from being detected as status changes
        if "original_status" in result and result["status"] and result["original_status"]:
            fixed_new_status = JarokeloScraper.fix_utf8_encoding(result["status"])
            fixed_original_status = JarokeloScraper.fix_utf8_encoding(result["original_status"])
            if fixed_new_status == fixed_original_status:
                result["status"] = result["original_status"]
        
        return result
    
    def scrape_reports_batch(self, urls: List[str]) -> List[Dict]:
        """
        Scrape multiple reports synchronously.
        """
        print(f"Starting synchronous batch scraping of {len(urls)} URLs...")
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
        
        print(f"Synchronous batch scraping completed: {len(results)}/{len(urls)} successful")
        return results
    
    def extract_listing_info(self, page_url: str) -> list:
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
                elem_class = elem.get("class", [])
                # elem_class can be a list or string; normalize to list
                if isinstance(elem_class, str):
                    elem_class = [elem_class]
                if not any("badge--comment" in c for c in elem_class):
                    status = elem.text.strip()
                    break
            if status is None:
                print(f"[ERROR] Status extraction failed for listing card: {url}")
                print(f"[DEBUG] Raw HTML snippet for card:")
                print(str(card)[:1000])
            card_info.append({"url": url, "status": status})
        
        return card_info
    
    def extract_listing_info_from_soup(self, soup) -> list:
        """Extract URL and status from listing page cards using pre-parsed BeautifulSoup object"""
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
                elem_class = elem.get("class", [])
                # elem_class can be a list or string; normalize to list
                if isinstance(elem_class, str):
                    elem_class = [elem_class]
                if not any("badge--comment" in c for c in elem_class):
                    status = elem.text.strip()
                    break
            if status is None:
                print(f"[ERROR] Status extraction failed for listing card: {url}")
                print(f"[DEBUG] Raw HTML snippet for card:")
                print(str(card)[:1000])
            card_info.append({"url": url, "status": status})
        
        return card_info

    def scrape_listing_page(self, page_url: str, global_urls: Set[str], 
                            until_date: Optional[str] = None, 
                            stop_on_existing: bool = True,
                            use_buffered_saving: bool = False) -> Tuple[Optional[str], bool]:
        """Return next page URL and a flag if we reached an already scraped report or until_date."""
        if not self.session:
            raise ValueError("Requests session not initialized")
            
        # Extract all card info (URL + status) from listing page
        card_info = self.extract_listing_info(page_url)

        # Update statuses or perform full re-scrapes for existing records
        for card in card_info:
            url = card["url"]
            current_status = card["status"]
            if url in global_urls:
                _, existing_record, _ = self.data_manager.find_record_by_url(url)
                old_status = existing_record.get("status") if existing_record else None
                if old_status is not None and current_status is not None and self.data_manager.needs_full_rescrape(str(old_status), str(current_status)):
                    print(f"Status change requires full re-scrape: {url} ({old_status} → {current_status})")
                    print(f"[DEBUG] This is expected when status changes to/from 'MEGOLDOTT' to capture resolution_date")
                    try:
                        updated_report = self.scrape_report(url)
                        self.data_manager.replace_record(url, updated_report)
                        print(f"Successfully updated record for {url}")
                    except Exception as e:
                        print(f"ERROR: Failed to scrape report during status update: {url}")
                        print(f"Error details: {str(e)}")
                        print(f"[INFO] Continuing with next report...")
                        continue
                elif self.data_manager.update_status_if_changed(url, current_status):
                    print(f"Updated status for {url}: {current_status}")

        # Process all new URLs from this page
        new_urls_from_page = [card["url"] for card in card_info if card["url"] not in global_urls]

        if new_urls_from_page:
            print(f"Processing {len(new_urls_from_page)} new URLs from this page...")
            scraped_reports = []
            for url in new_urls_from_page:
                try:
                    report = self.scrape_report(url)
                    scraped_reports.append(report)
                    if use_buffered_saving:
                        self.data_manager.save_report_buffered(report, global_urls)
                    else:
                        self.data_manager.save_report(report, global_urls)
                except Exception as e:
                    print(f"ERROR: Failed to scrape new report: {url}")
                    print(f"Error details: {str(e)}")
                    continue
            # Only stop if ALL new scraped reports are older than until_date
            if until_date:
                all_older_than_until = all(r.get("date", "0000-00-00") < until_date for r in scraped_reports)
                if all_older_than_until:
                    print(f"Reached until_date ({until_date}) after processing all new URLs on this page.")
                    return None, True

        # If there are no new URLs on this page, stop scraping
        if not new_urls_from_page:
            print("No new entries found on this page. Stopping scraping.")
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
                if isinstance(href, str) and href.startswith("/"):
                    href = "https://jarokelo.hu" + href
                if isinstance(href, str) or href is None:
                    return href, False
                else:
                    return None, False
        return None, False
    
    def detect_changed_urls_fast(self, cutoff_months: int = 3, output_file: str = "recent_changed_urls.txt") -> int:
        """
        Fast status change detection - scans only recent pages for status changes.

        Args:
            cutoff_months: Only scan pages from last N months (default: 3)
            output_file: File to save changed URLs to

        Returns:
            Number of status changes detected
        """
        import concurrent.futures
        import threading
        from datetime import datetime, timedelta
        import time, os, json

        def fetch_page_threaded(page_url):
            """Fetch a single page in a thread"""
            try:
                response = self.session.get(page_url, timeout=30)
                response.raise_for_status()
                return response.text
            except Exception as e:
                print(f"   Error fetching {page_url}: {e}")
                return None

        def process_page_batch(page_urls, existing_data, cutoff_date):
            """Process a batch of pages and return changed URLs"""
            changed_urls = set()

            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                # Submit all page fetches
                future_to_url = {executor.submit(fetch_page_threaded, url): url for url in page_urls}

                # Process results as they complete
                for future in concurrent.futures.as_completed(future_to_url):
                    page_url = future_to_url[future]
                    try:
                        html_content = future.result()
                        if not html_content:
                            continue

                        # Parse page content
                        soup = BeautifulSoup(html_content, 'html.parser')

                        # Extract card info from listing page (URL + status) - NO SCRAPING!
                        card_info = self.extract_listing_info_from_soup(soup)

                        # Check each card for changes
                        for card in card_info:
                            url = card["url"]
                            current_status = card.get("status", "")

                            if url in existing_data:
                                old_data = existing_data[url]
                                old_status = old_data["status"]
                                old_resolution = old_data["resolution_date"]
                                report_date = old_data["date"]

                                # Only check reports within our cutoff date
                                if report_date >= cutoff_date.strftime("%Y-%m-%d"):
                                    # Detect if status changed or resolution was added
                                    status_changed = current_status != old_status
                                    newly_resolved = (not old_resolution and
                                                    current_status and
                                                    current_status.upper() == "MEGOLDOTT")

                                    if status_changed or newly_resolved:
                                        changed_urls.add(url)
                                        print(f"   Status change detected: {url}")

                    except Exception as e:
                        print(f"   Error processing {page_url}: {e}")

            return changed_urls

        cutoff_date = datetime.now() - timedelta(days=cutoff_months * 30)

        print(f"🔍 RECENT STATUS CHANGE DETECTION (FAST SCAN - OPTIMIZED)")
        print(f"Strategy: Parallel page scanning for status changes in the last {cutoff_months} months")
        print(f"Cutoff months: {cutoff_months}")

        print("\n[PERF] Building URL index cache...")
        start_time = time.time()
        # Load existing data to compare against for status changes
        existing_data = {}
        for filename in os.listdir(self.data_manager.data_dir):
            if filename.endswith(".jsonl"):
                file_path = os.path.join(self.data_manager.data_dir, filename)
                with open(file_path, encoding="utf-8") as f:
                    for line in f:
                        try:
                            data = json.loads(line)
                            # Only load data we care about for comparison
                            existing_data[data["url"]] = {
                                "date": data.get("date", "0000-00-00"),
                                "status": data.get("status", ""),
                                "resolution_date": data.get("resolution_date")
                            }
                        except json.JSONDecodeError:
                            continue

        print(f"[PERF] Loaded {len(existing_data):,} URLs in {time.time() - start_time:.2f}s")
        print(f"[PERF] URL index cached for future runs")

        changed_urls = set()
        page = 1
        scan_start_time = time.time()
        batch_size = 5  # Process 5 pages at a time

        try:
            while True:
                # Build batch of page URLs
                page_urls = []
                for i in range(batch_size):
                    if page + i == 1:
                        page_urls.append(self.BASE_URL)
                    else:
                        page_urls.append(f"{self.BASE_URL}?page={page + i}")

                print(f"[Pages {page}-{page + len(page_urls) - 1}] Loading batch...")

                # Process batch of pages in parallel
                batch_changed_urls = process_page_batch(page_urls, existing_data, cutoff_date)
                changed_urls.update(batch_changed_urls)

                # Check if we got any cards from the last page in the batch
                # If not, we've reached the end
                last_page_url = page_urls[-1]
                try:
                    response = self.session.get(last_page_url, timeout=30)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.text, 'html.parser')
                    card_info = self.extract_listing_info_from_soup(soup)

                    if not card_info:
                        print(f"   No more cards found, stopping")
                        break

                    # Check if any cards on this page are within our cutoff date
                    # If not, all subsequent pages will be even older, so we can stop
                    page_has_recent_reports = False
                    for card in card_info:
                        url = card["url"]
                        if url in existing_data:
                            report_date = existing_data[url]["date"]
                            if report_date >= cutoff_date.strftime("%Y-%m-%d"):
                                page_has_recent_reports = True
                                break

                    if not page_has_recent_reports:
                        print(f"   Page {page + len(page_urls) - 1} contains no reports within cutoff date ({cutoff_months} months), stopping")
                        break

                except Exception as e:
                    print(f"   Error checking pagination: {e}")
                    break

                page += batch_size

                # Safety limit to prevent runaway - but only if we're still finding recent reports
                # If we've been scanning for too long without finding cutoff, something's wrong
                if page > 2000:  # Much higher limit, but still prevent infinite loops
                    print(f"   Reached safety limit of 2000 pages without finding end of recent data, stopping")
                    break

        except Exception as e:
            print(f"   Error during status detection: {e}")

        # Save changed URLs to file
        if changed_urls:
            with open(output_file, 'w', encoding='utf-8') as f:
                for url in sorted(changed_urls):
                    f.write(f"{url}\n")

        elapsed = time.time() - start_time
        scan_elapsed = time.time() - scan_start_time
        print(f"   ✅ Detected {len(changed_urls):,} recently changed statuses in {elapsed:.1f}s (scan: {scan_elapsed:.1f}s)")
        print(f"   📁 Saved to: {output_file}")

        return len(changed_urls)
    
    def extract_old_pending_urls(self, cutoff_months: int = 3, output_file: str = "old_pending_urls.txt") -> int:
        """
        Extract old pending URLs (older than cutoff_months) from existing database.
        These are issues that were scraped a while ago but still don't have a resolution.
        
        Args:
            cutoff_months: Extract issues older than this many months (default: 3)
            output_file: File to save old pending URLs to
            
        Returns:
            Number of old pending URLs extracted
        """
        import json
        
        print(f"🕰️ Extracting Old Pending URLs (older than {cutoff_months} months)")
        start_time = time.time()
        
        # Calculate cutoff date
        cutoff_date = (datetime.now() - timedelta(days=cutoff_months * 30)).strftime("%Y-%m-%d")
        print(f"   Cutoff date: {cutoff_date}")
        
        # Load existing data to find old pending issues
        old_pending_urls = set()
        non_pending_statuses = {"MEGOLDOTT", "TÖRÖLT", "MEGOLDATLAN"}
        
        # Process each JSONL file in the data directory
        for filename in os.listdir(self.data_manager.data_dir):
            if not filename.endswith(".jsonl"):
                continue
                
            file_path = os.path.join(self.data_manager.data_dir, filename)
            print(f"   Processing {filename}...")
            
            with open(file_path, encoding="utf-8") as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        # Check if the issue is old enough and still pending
                        report_date = data.get("date", "9999-99-99")
                        status_raw = data.get("status", "")
                        status = status_raw.upper() if isinstance(status_raw, str) else ""
                        url = data.get("url", "")
                        if (report_date < cutoff_date and
                            status not in non_pending_statuses and 
                            url):
                            old_pending_urls.add(url)
                    except json.JSONDecodeError:
                        continue
        
        # Save old pending URLs to file
        if old_pending_urls:
            with open(output_file, 'w', encoding='utf-8') as f:
                for url in sorted(old_pending_urls):
                    f.write(f"{url}\n")
        
        elapsed = time.time() - start_time
        print(f"   ✅ Found {len(old_pending_urls):,} old pending URLs in {elapsed:.1f}s")
        print(f"   📁 Saved to: {output_file}")
        
        return len(old_pending_urls)

    def scrape_urls_from_file(self, urls_file: str, progress_prefix: str = "", resolution_focus: bool = True) -> int:
        """
        Scrape specific URLs from a file (for resolution date updates).
        
        Args:
            urls_file: File containing URLs to scrape (one per line)
            progress_prefix: Prefix for progress messages
            resolution_focus: If True, optimizes for resolution date extraction
                              For recent/old resolution date jobs (Job 4 & 5)
            
        Returns:
            Number of URLs successfully scraped
        """
        if not os.path.exists(urls_file):
            print(f"   ⚠️  URLs file not found: {urls_file}")
            return 0
        
        # Load URLs from file
        urls_to_scrape = []
        with open(urls_file, 'r', encoding='utf-8') as f:
            for line in f:
                url = line.strip()
                if url:
                    urls_to_scrape.append(url)
        
        # Remove duplicates to avoid double work
        original_count = len(urls_to_scrape)
        urls_to_scrape = list(set(urls_to_scrape))  # Deduplicate
        if len(urls_to_scrape) < original_count:
            print(f"{progress_prefix}   📝 Removed {original_count - len(urls_to_scrape)} duplicate URLs from {urls_file}")
        
        if not urls_to_scrape:
            print(f"{progress_prefix}   📝 No URLs to scrape in {urls_file}")
            return 0
        
        if resolution_focus:
            print(f"{progress_prefix}Fetching resolution dates for {len(urls_to_scrape):,} URLs from {urls_file}")
        else:
            print(f"{progress_prefix}Scraping {len(urls_to_scrape):,} URLs from {urls_file}")
        
        global_urls = self.data_manager.load_all_existing_urls()
        start_time = time.time()
        successful_scrapes = 0
        non_null_resolution = 0

        for i, url in enumerate(urls_to_scrape, 1):
            try:
                # Get original record from DB
                _, original_record, _ = self.data_manager.find_record_by_url(url)
                original_status = original_record.get("status") if original_record else None
                original_resolution = original_record.get("resolution_date") if original_record else None

                # Scrape the report, using resolution_focus for efficiency if requested
                report_data = self.scrape_report(url, resolution_focus=resolution_focus)

                new_status = report_data.get("status")
                new_resolution = report_data.get("resolution_date")

                # Only print if status or resolution_date actually changes, and always show both original and new values
                if (original_status != new_status) or (original_resolution != new_resolution):
                    print(f"{progress_prefix}[{i}/{len(urls_to_scrape)}] {url}")
                    print(f"\tResolution date focus: {url} -> original_status={original_status}, new_status={new_status}, original_resolution_date={original_resolution}, new_resolution_date={new_resolution}")

                # Save immediately (no buffering for status updates)
                self.data_manager.save_report(report_data, global_urls)
                successful_scrapes += 1
                if new_resolution is not None:
                    non_null_resolution += 1

            except Exception as e:
                print(f"{progress_prefix}   ❌ Error scraping {url}: {e}")
                continue

        elapsed = time.time() - start_time
        if resolution_focus:
            print(f"{progress_prefix}✅ Finished processing {len(urls_to_scrape)} URLs in {elapsed:.1f}s")
            print(f"{progress_prefix}✅ Resolution dates updated for {non_null_resolution} URLs (out of {successful_scrapes} successfully scraped)")
        else:
            print(f"{progress_prefix}✅ Successfully scraped {successful_scrapes}/{len(urls_to_scrape)} URLs in {elapsed:.1f}s")

        return successful_scrapes
    
    def extract_first_authority_response_date(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Extract the first authority response date from the page.
        Enhanced method that handles both explicit "illetékes válasza" and implicit
        authority responses following "elküldte az ügyet az illetékesnek" pattern.

        Args:
            soup: BeautifulSoup object of the page

        Returns:
            Date string in YYYY-MM-DD format, or None if not found
        """
        # Find all comment bodies
        comment_bodies = soup.select("div.comment__body")

        # First, try the original method: look for explicit "Az illetékes válasza"
        authority_response_dates = []
        for body in comment_bodies:
            message_elem = body.select_one("p.comment__message")
            if message_elem and "Az illetékes válasza" in message_elem.text:
                date_elem = body.select_one("time.comment__date")
                if date_elem:
                    date_text = date_elem.text.strip()
                    try:
                        date_parts = date_text.split()[:3]
                        normalized_date = self.normalize_date(date_parts)
                        authority_response_dates.append(normalized_date)
                    except Exception as e:
                        print(f"Warning: Failed to parse authority response date '{date_text}': {e}")
                        continue

        # Return the last (bottommost) date if found with explicit method
        if authority_response_dates:
            return authority_response_dates[-1]

        # If no explicit responses found, try enhanced method
        # Look for "elküldte az ügyet az illetékesnek" pattern
        for i, body in enumerate(comment_bodies):
            message_elem = body.select_one("p.comment__message")
            if message_elem and "elküldte az ügyet az illetékesnek:" in message_elem.text:
                # Found a forwarding message, extract the authority name
                message_text = message_elem.text.strip()
                if ":" in message_text:
                    authority_name = message_text.split(":", 1)[1].strip()

                    # Look for authority responses BEFORE this forwarding message
                    # (comments are displayed newest-first)
                    for j in range(i - 1, -1, -1):  # Search backwards
                        next_body = comment_bodies[j]
                        next_message_elem = next_body.select_one("p.comment__message")

                        if next_message_elem:
                            next_message_text = next_message_elem.text.strip()
                            # Check if this comment is from the same authority
                            if authority_name.lower() in next_message_text.lower():
                                # Found a comment from the same authority, get the date
                                date_elem = next_body.select_one("time.comment__date")
                                if date_elem:
                                    date_text = date_elem.text.strip()
                                    try:
                                        date_parts = date_text.split()[:3]
                                        normalized_date = self.normalize_date(date_parts)
                                        return normalized_date
                                    except Exception as e:
                                        print(f"Warning: Failed to parse enhanced authority response date '{date_text}': {e}")
                                        continue

        return None
