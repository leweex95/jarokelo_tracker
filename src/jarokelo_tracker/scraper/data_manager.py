"""
Data Management Module

This module handles saving and loading scraped data with proper file organization
and chronological ordering by month.
"""

import os
import json
import pickle
import hashlib
import gc
 
from datetime import datetime
from typing import Dict, Set, Tuple, Optional, List
from collections import defaultdict


class DataManager:
    """Manages data storage and retrieval for scraped reports"""
    
    def __init__(self, data_dir: str = "data/raw", buffer_size: int = 25):
        self.data_dir = data_dir
        self.buffer_size = buffer_size  # Number of records to buffer before writing to disk (reduced for CI)
        self.buffer = defaultdict(list)  # Buffer organized by monthly file: {file_path: [reports]}
        self.buffer_count = 0  # Total number of buffered records
        
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
        """
        Load all existing URLs from all monthly files.
        """
        import time
        start_time = time.time()
        global_urls = set()
        for f in os.listdir(self.data_dir):
            if f.endswith(".jsonl"):
                with open(os.path.join(self.data_dir, f), encoding="utf-8") as fh:
                    for line in fh:
                        try:
                            global_urls.add(json.loads(line)["url"])
                        except json.JSONDecodeError:
                            continue
        load_time = time.time() - start_time
        print(f"[PERF] Loaded {len(global_urls):,} URLs in {load_time:.2f}s")
        return global_urls
    
    def load_pending_urls_older_than(self, cutoff_months: int = 3) -> Set[str]:
        """
        Load all URLs from existing data that are still pending/waiting and older than cutoff_months.
        
        Args:
            cutoff_months: Number of months ago to use as cutoff (default: 3)
            
        Returns:
            Set of URLs that are pending and older than cutoff
        """
        import time
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.now() - timedelta(days=cutoff_months * 30)
        cutoff_str = cutoff_date.strftime("%Y-%m-%d")
        
        pending_urls = set()
        pending_statuses = {"VÁRAKOZÁS", "FOLYAMATBAN", "BEKÜLDÖTT", "WAITING", "IN_PROGRESS", "SUBMITTED"}
        
        print(f"[PERF] Loading pending URLs older than {cutoff_str} ({cutoff_months} months ago)...")
        start_time = time.time()
        
        for filename in os.listdir(self.data_dir):
            if filename.endswith(".jsonl"):
                file_path = os.path.join(self.data_dir, filename)
                with open(file_path, encoding="utf-8") as f:
                    for line in f:
                        try:
                            data = json.loads(line)
                            # Check if report is old enough and still pending
                            if (data.get("date", "9999-99-99") < cutoff_str and 
                                data.get("status", "").upper() in pending_statuses and
                                not data.get("resolution_date")):  # Not resolved
                                pending_urls.add(data["url"])
                        except json.JSONDecodeError:
                            continue
        
        load_time = time.time() - start_time
        print(f"[PERF] Found {len(pending_urls):,} old pending URLs in {load_time:.2f}s")
        
        return pending_urls
    
    def save_report(self, report: Dict, existing_urls: Set[str]) -> None:
        """
        Save a report to the monthly JSONL file, organizing entries by date.

        If the report URL already exists, update the record if status or resolution_date changed.
        Otherwise, insert as new.
        """
        file_path = self.get_monthly_file(report["date"])
        new_line = json.dumps(report, ensure_ascii=False) + "\n"

        lines = []
        updated = False
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                for i, line in enumerate(f, start=1):
                    line = line.rstrip("\r\n")
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        # If URL matches, check for status/resolution_date changes
                        if record.get("url") == report["url"]:
                            # Only update if status or resolution_date changed
                            if (record.get("status") != report.get("status") or
                                record.get("resolution_date") != report.get("resolution_date")):
                                lines.append(new_line)
                                updated = True
                            else:
                                lines.append(line + "\n")
                            continue  # Skip adding duplicate/new below
                        lines.append(line + "\n")
                    except json.JSONDecodeError as e:
                        print(f"[ERROR] Malformed line {i} in {file_path}: {line}")
                        raise

        # If not updated, insert new report chronologically
        if not updated:
            report_date = report["date"]
            inserted = False
            new_lines = []
            for line in lines:
                line_date = json.loads(line)["date"]
                if not inserted and report_date >= line_date:
                    new_lines.append(new_line)
                    inserted = True
                new_lines.append(line)
            if not inserted:
                new_lines.append(new_line)  # append if newest
            lines = new_lines

        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
            
    def save_report_buffered(self, report: Dict, existing_urls: Set[str]) -> None:
        """
        Save a report to the memory buffer and flush to disk when buffer is full.
        This method is optimized for bulk operations (comprehensive scraping).
        
        For comprehensive scraping, this provides significant performance improvements
        by reducing disk I/O from O(n) to O(n/buffer_size).
        """
        if report["url"] in existing_urls:
            return
        existing_urls.add(report["url"])
        
        # Add to buffer
        file_path = self.get_monthly_file(report["date"])
        self.buffer[file_path].append(report)
        self.buffer_count += 1
                
        # Flush buffer if it's full
        if self.buffer_count >= self.buffer_size:
            self.flush_buffer()
    
    def flush_buffer(self) -> None:
        """
        Flush all buffered reports to disk and clear the buffer.
        This method merges buffered reports with existing files while maintaining chronological order.
        """
        if self.buffer_count == 0:
            return
        
        print(f"Flushing {self.buffer_count} records from buffer to disk...")
        
        for file_path, buffered_reports in self.buffer.items():
            if not buffered_reports:
                continue
                
            # Load existing lines from file
            existing_lines = []
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    for i, line in enumerate(f, start=1):
                        line = line.rstrip("\r\n")
                        if not line:
                            continue
                        try:
                            json.loads(line)  # validate
                            existing_lines.append(line + "\n")
                        except json.JSONDecodeError as e:
                            print(f"[ERROR] Malformed line {i} in {file_path}: {line}")
                            raise
            
            # Sort buffered reports by date (newest first for prepending logic)
            buffered_reports.sort(key=lambda x: x["date"], reverse=True)
            
            # Merge buffered reports with existing lines chronologically
            all_lines = existing_lines.copy()
            
            for report in buffered_reports:
                new_line = json.dumps(report, ensure_ascii=False) + "\n"
                report_date = report["date"]
                
                # Find insertion point
                inserted = False
                new_all_lines = []
                
                for line in all_lines:
                    line_date = json.loads(line)["date"]
                    if not inserted and report_date >= line_date:
                        new_all_lines.append(new_line)
                        inserted = True
                    new_all_lines.append(line)
                
                if not inserted:
                    new_all_lines.append(new_line)  # append if newest
                
                all_lines = new_all_lines
            
            # Write merged content to file
            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(all_lines)
        
        # Clear buffer
        buffer_records = self.buffer_count
        self.buffer.clear()
        self.buffer_count = 0
        
        # Force garbage collection after buffer clear
        gc.collect()
                
        print(f"Successfully flushed {buffer_records} records to disk")
            
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensure buffer is flushed"""
        self.flush_buffer()
        self.cleanup_temp_files()
    
    def cleanup_temp_files(self) -> None:
        """Clean up temporary files to free disk space"""
        try:
            # Clean up any temporary files in data directory
            for filename in os.listdir(self.data_dir):
                if filename.startswith('.tmp') or filename.endswith('.tmp'):
                    temp_file = os.path.join(self.data_dir, filename)
                    try:
                        os.remove(temp_file)
                        print(f"[CLEANUP] Removed temporary file: {filename}")
                    except OSError:
                        pass
        except Exception as e:
            print(f"[WARNING] Cleanup failed: {e}")
    
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
        """Find a record by URL and return file path, record data, and line number.
        
        First checks the memory buffer, then searches disk files.
        """
        # First check memory buffer for recently scraped records
        for file_path, buffered_reports in self.buffer.items():
            for record in buffered_reports:
                if record.get("url") == url:
                    # Return buffer info (file_path, record, line_num=None for buffer)
                    return file_path, record, None
        
        # Then check disk files
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
        # Do not update if new_status is None or empty
        if not new_status:
            error_msg = f"[ERROR] Attempted status update for {url} with None or empty value. Old status: '{record.get('status')}'"
            print(error_msg)
            raise ValueError(error_msg)
        # Only update if status actually changed (case-insensitive comparison)
        if current_status and new_status and current_status.lower() == new_status.lower():
            # Status is the same (ignoring case) - no update needed
            if current_status != new_status:
                print(f"[DEBUG] Status case difference ignored for {url}: '{current_status}' vs '{new_status}'")
            return False
        print(f"Status changed for {url}: '{current_status}' → '{new_status}'")
        # Update the record
        record["status"] = new_status
        # Handle buffer vs disk record updates differently
        if line_num is None:
            # Record is in buffer - already updated by reference
            print(f"[DEBUG] Updated buffered record for {url}")
        elif file_path is not None:
            # Record is on disk - need to write back to file
            self._update_disk_record(file_path, line_num, record)
        else:
            print(f"[ERROR] file_path is None when updating disk record for {url}")
            return False
        return True
    
    def _update_disk_record(self, file_path: str, line_num: int, record: Dict) -> None:
        """Helper method to update a record on disk"""
        # Read all lines from the file
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        # Update the specific line
        lines[line_num - 1] = json.dumps(record, ensure_ascii=False) + "\n"
        
        # Write back to file
        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
    
    def needs_full_rescrape(self, old_status: str, new_status: str) -> bool:
        """
        Determine if a status change requires full re-scraping of the individual page.
        
        This is needed when:
        - Status changes to "MEGOLDOTT" (to get resolution_date)
        - Status changes from "MEGOLDOTT" to something else (to clear resolution_date)
        
        Note: Both "MEGOLDOTT" and "Megoldott" are considered resolved status.
        """
        if not old_status or not new_status:
            return False
            
        old_resolved = old_status.upper() == "MEGOLDOTT"
        new_resolved = new_status.upper() == "MEGOLDOTT"
        
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
        file_path, old_record, line_num = self.find_record_by_url(url)
        
        if not file_path:
            print(f"[WARNING] Record not found for replacement: {url}")
            return False
        
        if line_num is None:
            # Record is in buffer - find and replace it
            for i, record in enumerate(self.buffer[file_path]):
                if record.get("url") == url:
                    self.buffer[file_path][i] = new_record
                    print(f"[DEBUG] Replaced buffered record for {url}")
                    return True
            print(f"[WARNING] Buffered record not found for replacement: {url}")
            return False
        else:
            # Record is on disk - replace it
            self._update_disk_record(file_path, line_num, new_record)
            return True
