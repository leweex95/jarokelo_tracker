"""
Data Management Module

This module handles saving and loading scraped data with proper file organization
and chronological ordering by month.
"""

import os
import json
from datetime import datetime
from typing import Dict, Set, Tuple, Optional


class DataManager:
    """Manages data storage and retrieval for scraped reports"""
    
    def __init__(self, data_dir: str = "data/raw"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
    
    def get_monthly_file(self, report_date: str) -> str:
        """Return file path based on report's month (YYYY-MM)."""
        # report_date expected as string, e.g. "2025-08-25"
        month_str = datetime.strptime(report_date, "%Y-%m-%d").strftime("%Y-%m")
        return os.path.join(self.data_dir, f"{month_str}.jsonl")
    
    def load_existing_urls(self, report_date: str) -> Set[str]:
        """Load already saved report URLs for the report's month."""
        file_path = self.get_monthly_file(report_date)
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
    
    def load_all_existing_urls(self) -> Set[str]:
        """Load all existing URLs from all monthly files."""
        global_urls = set()
        for f in os.listdir(self.data_dir):
            if f.endswith(".jsonl"):
                with open(os.path.join(self.data_dir, f), encoding="utf-8") as fh:
                    for line in fh:
                        try:
                            global_urls.add(json.loads(line)["url"])
                        except json.JSONDecodeError:
                            continue
        return global_urls
    
    def save_report(self, report: Dict, existing_urls: Set[str]) -> None:
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

        file_path = self.get_monthly_file(report["date"])
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
    
    def get_scraping_resume_point(self) -> Tuple[Optional[str], int]:
        """Determine resume point: oldest scraped report date and total saved reports."""
        all_files = sorted(
            [os.path.join(self.data_dir, f) for f in os.listdir(self.data_dir) if f.endswith(".jsonl")]
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
    
    def find_record_by_url(self, url: str) -> Tuple[Optional[str], Optional[Dict], Optional[int]]:
        """Find a record by URL and return file path, record data, and line number"""
        for filename in os.listdir(self.data_dir):
            if not filename.endswith(".jsonl"):
                continue
                
            file_path = os.path.join(self.data_dir, filename)
            with open(file_path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        record = json.loads(line.strip())
                        if record.get("url") == url:
                            return file_path, record, line_num
                    except json.JSONDecodeError:
                        continue
        
        return None, None, None
    
    def update_status_if_changed(self, url: str, new_status: str) -> bool:
        """
        Update the status of an existing record if it has changed.
        
        Args:
            url: The URL of the record to update
            new_status: The new status from the listing page
            
        Returns:
            True if the status was updated, False otherwise
        """
        file_path, record, line_num = self.find_record_by_url(url)
        
        if not record:
            print(f"[WARNING] Record not found for URL: {url}")
            return False
        
        current_status = record.get("status")
        
        # Only update if status actually changed
        if current_status == new_status:
            return False
        
        print(f"Status changed for {url}: '{current_status}' → '{new_status}'")
        
        # Update the record
        record["status"] = new_status
        
        # If status changed to "MEGOLDOTT", we might want to update resolution_date
        # But since we're only getting info from listing page, we can't extract the full resolution date
        # This would require a full scrape of the individual page
        # For now, we'll just update the status
        
        # Read all lines from the file
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        # Update the specific line
        lines[line_num - 1] = json.dumps(record, ensure_ascii=False) + "\n"
        
        # Write back the updated content
        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        
        return True
    
    def needs_full_rescrape(self, old_status: str, new_status: str) -> bool:
        """
        Determine if a status change requires full re-scraping of the individual page.
        
        This is needed when:
        - Status changes to "MEGOLDOTT" (to get resolution_date)
        - Status changes from "MEGOLDOTT" to something else (to clear resolution_date)
        """
        old_resolved = old_status and old_status.upper() == "MEGOLDOTT"
        new_resolved = new_status and new_status.upper() == "MEGOLDOTT"
        
        # Need full rescrape if resolution status changed
        return old_resolved != new_resolved
    
    def replace_record(self, url: str, new_record: Dict) -> bool:
        """
        Replace an existing record with new data (for full re-scrapes).
        
        Args:
            url: The URL of the record to replace
            new_record: The new record data
            
        Returns:
            True if the record was replaced, False if not found
        """
        file_path, _, line_num = self.find_record_by_url(url)
        
        if not file_path:
            print(f"[WARNING] Record not found for replacement: {url}")
            return False
        
        # Read all lines from the file
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        # Replace the specific line
        lines[line_num - 1] = json.dumps(new_record, ensure_ascii=False) + "\n"
        
        # Write back the updated content
        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        
        print(f"Replaced record for {url} with updated data")
        return True