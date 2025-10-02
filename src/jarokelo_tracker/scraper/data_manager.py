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
import psutil
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
        
        # Performance optimization: URL index cache
        self.index_file = os.path.join(data_dir, ".url_index.cache")
        self.meta_file = os.path.join(data_dir, ".file_meta.cache")
        
        # Memory and disk monitoring (more aggressive for CI)
        self._monitor_resources = True
        self._last_memory_check = 0
        self._check_interval = 10  # Check every 10 records instead of 30 seconds
        
        os.makedirs(data_dir, exist_ok=True)
    
    def get_monthly_file(self, report_date: str) -> str:
        """Return file path based on report's month (YYYY-MM)."""
        # report_date expected as string, e.g. "2025-08-25"
        month_str = datetime.strptime(report_date, "%Y-%m-%d").strftime("%Y-%m")
        return os.path.join(self.data_dir, f"{month_str}.jsonl")
    
    def _check_resource_usage(self, force: bool = False) -> None:
        """Monitor memory and disk usage, force flush if necessary"""
        if not self._monitor_resources:
            return
            
        import time
        current_time = time.time()
        
        # Check resources every 30 seconds or when forced
        if not force and current_time - self._last_memory_check < 30:
            return
            
        self._last_memory_check = current_time
        
        try:
            # Get memory usage
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            # Get disk usage
            disk_usage = psutil.disk_usage(self.data_dir)
            disk_free_gb = disk_usage.free / 1024 / 1024 / 1024
            
            # Log resource usage
            if force or memory_mb > 500:  # Log if memory > 500MB or forced
                print(f"[RESOURCE] Memory: {memory_mb:.1f}MB, Disk free: {disk_free_gb:.1f}GB, Buffer: {self.buffer_count} records")
            
            # Force flush if memory usage is high or disk space is low (very aggressive for CI)
            if memory_mb > 400 or disk_free_gb < 5.0:  # 400MB memory or <5GB disk (much more aggressive)
                print(f"[WARNING] High resource usage detected - forcing buffer flush")
                print(f"[WARNING] Memory: {memory_mb:.1f}MB, Disk free: {disk_free_gb:.1f}GB")
                self.flush_buffer()
                gc.collect()  # Force garbage collection
                
                # Emergency cleanup if still critical
                if disk_free_gb < 3.0:
                    print(f"[EMERGENCY] Critical disk space - running emergency cleanup")
                    self._emergency_cleanup()
                
        except Exception as e:
            print(f"[WARNING] Resource monitoring failed: {e}")
            self._monitor_resources = False  # Disable monitoring if it fails
    
    def _emergency_cleanup(self) -> None:
        """Emergency cleanup when disk space is critically low"""
        try:
            print("[EMERGENCY] Running emergency disk cleanup...")
            
            # 1. Clear all caches immediately
            cache_files = [self.index_file, self.meta_file]
            for cache_file in cache_files:
                if os.path.exists(cache_file):
                    os.remove(cache_file)
                    print(f"[EMERGENCY] Removed cache: {cache_file}")
            
            # 2. Clean up pip caches if accessible
            import shutil
            pip_cache_dir = os.path.expanduser("~/.cache/pip")
            if os.path.exists(pip_cache_dir):
                try:
                    shutil.rmtree(pip_cache_dir)
                    print(f"[EMERGENCY] Cleared pip cache")
                except:
                    pass
            
            # 3. Remove any .pyc files
            import glob
            pyc_files = glob.glob("**/*.pyc", recursive=True)
            for pyc_file in pyc_files[:100]:  # Limit to avoid hanging
                try:
                    os.remove(pyc_file)
                except:
                    pass
            if pyc_files:
                print(f"[EMERGENCY] Removed {min(len(pyc_files), 100)} .pyc files")
            
            # 4. Force garbage collection
            gc.collect()
            
            print("[EMERGENCY] Emergency cleanup completed")
            
        except Exception as e:
            print(f"[ERROR] Emergency cleanup failed: {e}")
    
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
        Load all existing URLs from all monthly files with intelligent caching.
        
        Performance improvements:
        - First run: Same as original (builds cache)  
        - Subsequent runs: 10-100x faster (loads from cache)
        - Incremental updates: Only processes changed files
        """
        
        # Check if we can use cached data
        cache_valid, cached_urls = self._try_load_from_cache()
        if cache_valid:
            return cached_urls
        
        # Fallback to full file scan and rebuild cache
        print("[PERF] Building URL index cache...")
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
        
        # Save to cache for next time
        self._save_to_cache(global_urls)
        
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
    
    def _get_file_metadata(self) -> Dict[str, float]:
        """Get modification times for all JSONL files"""
        metadata = {}
        for filename in os.listdir(self.data_dir):
            if filename.endswith('.jsonl'):
                file_path = os.path.join(self.data_dir, filename)
                metadata[filename] = os.path.getmtime(file_path)
        return metadata
    
    def _try_load_from_cache(self) -> Tuple[bool, Set[str]]:
        """Try to load URLs from cache if files haven't changed"""
        
        if not os.path.exists(self.index_file) or not os.path.exists(self.meta_file):
            return False, set()
        
        try:
            # Load cached metadata
            with open(self.meta_file, 'rb') as f:
                cached_metadata = pickle.load(f)
            
            # Check if files have changed
            current_metadata = self._get_file_metadata()
            
            if current_metadata == cached_metadata:
                # No changes, load from cache
                with open(self.index_file, 'rb') as f:
                    cached_urls = pickle.load(f)
                print(f"[PERF] Loaded {len(cached_urls):,} URLs from cache in <0.1s")
                return True, cached_urls
            else:
                # Files changed, cache invalid
                return False, set()
                
        except Exception as e:
            print(f"[PERF] Cache load failed: {e}")
            return False, set()
    
    def _save_to_cache(self, urls: Set[str]) -> None:
        """Save URLs and file metadata to cache"""
        try:
            # Save URLs
            with open(self.index_file, 'wb') as f:
                pickle.dump(urls, f)
            
            # Save file metadata
            current_metadata = self._get_file_metadata()
            with open(self.meta_file, 'wb') as f:
                pickle.dump(current_metadata, f)
                
            print(f"[PERF] URL index cached for future runs")
            
        except Exception as e:
            print(f"[WARNING] Could not save URL cache: {e}")
    
    def invalidate_cache(self) -> None:
        """Invalidate URL cache (call when files are modified)"""
        for cache_file in [self.index_file, self.meta_file]:
            if os.path.exists(cache_file):
                os.remove(cache_file)
        # print("[PERF] URL cache invalidated")  # Comment out to avoid spam
    
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
        
        # Invalidate cache since file was modified
        self.invalidate_cache()
    
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
        
        # Check resource usage every 10 records or when forced
        if self.buffer_count % self._check_interval == 0:
            self._check_resource_usage(force=True)
        else:
            self._check_resource_usage()
        
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
        
        # Force resource check before flushing
        self._check_resource_usage(force=True)
        
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
        
        # Invalidate cache since files were modified
        self.invalidate_cache()
        
        print(f"Successfully flushed {buffer_records} records to disk")
        
        # Final resource check after flush
        self._check_resource_usage(force=True)
    
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
            # Clean up cache files if they exist and are large
            cache_files = [self.index_file, self.meta_file]
            for cache_file in cache_files:
                if os.path.exists(cache_file):
                    size_mb = os.path.getsize(cache_file) / 1024 / 1024
                    if size_mb > 50:  # If cache is larger than 50MB, remove it
                        os.remove(cache_file)
                        print(f"[CLEANUP] Removed large cache file: {cache_file} ({size_mb:.1f}MB)")
            
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
        
        # Only update if status actually changed (case-insensitive comparison)
        if current_status and current_status.lower() == new_status.lower():
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
        else:
            # Record is on disk - need to write back to file
            self._update_disk_record(file_path, line_num, record)
        
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