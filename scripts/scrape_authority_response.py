#!/usr/bin/env python3
"""
Authority Response Scraper Script

This script scrapes the first authority response date from Járókelő issue pages.
It looks for comment boxes containing "Az illetékes válasza" and extracts the date
from the bottommost (chronologically first) such comment.
"""

import json
import os
import requests
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup

from jarokelo_tracker.scraper.core import JarokeloScraper


class AuthorityResponseScraper:
    """Scraper for extracting first authority response dates from issue pages"""

    def __init__(self):
        """Initialize the scraper"""
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
        self.close()

    def load_all_issues(self, data_dir: str = "data/raw") -> List[Dict]:
        """
        Load all issues from the raw data files.

        Args:
            data_dir: Directory containing the JSONL files

        Returns:
            List of all issue dictionaries
        """
        all_issues = []

        # Get all JSONL files in the data directory
        if not os.path.exists(data_dir):
            raise ValueError(f"Data directory {data_dir} does not exist")

        jsonl_files = [f for f in os.listdir(data_dir) if f.endswith('.jsonl')]
        jsonl_files.sort()  # Sort for consistent ordering

        for filename in jsonl_files:
            filepath = os.path.join(data_dir, filename)
            print(f"Loading data from {filename}...")

            with open(filepath, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        issue = json.loads(line.strip())
                        all_issues.append((filepath, issue))
                    except json.JSONDecodeError as e:
                        print(f"Warning: Failed to parse line {line_num} in {filename}: {e}")
                        continue

        print(f"Found {len(all_issues)} total issues")
        return all_issues

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
                        normalized_date = JarokeloScraper.normalize_date(date_parts)
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
                                        normalized_date = JarokeloScraper.normalize_date(date_parts)
                                        return normalized_date
                                    except Exception as e:
                                        print(f"Warning: Failed to parse enhanced authority response date '{date_text}': {e}")
                                        continue

        return None

    def scrape_authority_response(self, url: str) -> Optional[str]:
        """
        Scrape a single URL for the first authority response date.

        Args:
            url: URL to scrape

        Returns:
            First authority response date string, or None if not found
        """
        if not self.session:
            raise ValueError("Requests session not initialized")

        try:
            response = self.session.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            return self.extract_first_authority_response_date(soup)

        except Exception as e:
            print(f"Error scraping {url}: {e}")
            return None

    def process_all_issues(self, data_dir: str = "data/raw"):
        """
        Process all issues in data/raw and add first_authority_response_date field.
        Supports resuming from where it left off if interrupted.

        Args:
            data_dir: Input/output data directory
        """
        # Load all issues with their file paths
        issues_with_paths = self.load_all_issues(data_dir)

        # Group issues by file path
        issues_by_file = {}
        for filepath, issue in issues_with_paths:
            if filepath not in issues_by_file:
                issues_by_file[filepath] = []
            issues_by_file[filepath].append(issue)

        total_processed = 0
        total_with_response = 0
        total_skipped = 0

        # Process each file
        for filepath, issues in issues_by_file.items():
            print(f"\n{'='*60}")
            print(f"Processing {len(issues)} issues in {os.path.basename(filepath)}")

            # Find the starting index (resume point)
            start_index = self.find_resume_point(issues)
            if start_index > 0:
                print(f"📍 RESUMING: Skipping {start_index} already processed issues")
                total_skipped += start_index
            elif start_index == len(issues):
                print("✅ SKIPPING: All issues in this file already processed")
                continue

            # Keep all original issues - we'll update them in place
            updated_issues = issues.copy()
            issues_to_process = issues[start_index:]

            print(f"🚀 Processing {len(issues_to_process)} remaining issues...")

            # Process in batches to enable incremental saving
            batch_size = 50  # Save every 50 issues to prevent data loss
            processed_in_file = start_index

            for batch_start in range(0, len(issues_to_process), batch_size):
                batch_end = min(batch_start + batch_size, len(issues_to_process))
                batch_issues = issues_to_process[batch_start:batch_end]

                print(f"📦 Processing batch {batch_start//batch_size + 1}/{(len(issues_to_process) + batch_size - 1)//batch_size} "
                      f"({batch_end - batch_start} issues)...")

                for i, issue in enumerate(batch_issues, 1):
                    url = issue['url']
                    global_index = processed_in_file + i
                    print(f"Processing {global_index}/{len(issues)}: {url}")

                    # Scrape the authority response date
                    authority_date = self.scrape_authority_response(url)

                    # Update the issue in the updated_issues list (maintain original order)
                    issue_index = start_index + batch_start + (i - 1)
                    updated_issues[issue_index] = {
                        'url': issue['url'],
                        'title': issue['title'],
                        'author': issue['author'],
                        'author_profile': issue['author_profile'],
                        'date': issue['date'],
                        'category': issue['category'],
                        'first_authority_response_date': authority_date,
                        'institution': issue['institution'],
                        'supporter': issue['supporter'],
                        'description': issue['description'],
                        'status': issue['status'],
                        'address': issue['address'],
                        'resolution_date': issue['resolution_date'],
                        'latitude': issue['latitude'],
                        'longitude': issue['longitude'],
                    }

                    total_processed += 1

                    if authority_date:
                        total_with_response += 1
                        print(f"  ✓ Found authority response date: {authority_date}")
                    else:
                        print(f"  ⚠️  WARNING: No authority response found for {url}")
                        print("     This issue may have been resolved without authority intervention.")

                processed_in_file += len(batch_issues)

                # Save progress after each batch - save ALL issues in the file
                print(f"💾 Saving progress after batch ({len(updated_issues)} total issues in file so far)...")
                with open(filepath, 'w', encoding='utf-8') as f:
                    for issue in updated_issues:
                        f.write(json.dumps(issue, ensure_ascii=False) + '\n')

                print(f"✅ Batch saved. Progress: {processed_in_file}/{len(issues)} issues processed in this file")

        print(f"\n{'='*60}")
        print("COMPLETED PROCESSING ALL ISSUES")
        print(f"Total issues processed: {total_processed}")
        print(f"Total issues skipped (already processed): {total_skipped}")
        print(f"Issues with authority response: {total_with_response}")
        print(f"Issues without authority response: {total_processed - total_with_response}")
        if total_processed > 0:
            success_rate = (total_with_response / total_processed * 100)
            print(f"Success rate: {success_rate:.1f}%")
        print(f"{'='*60}")

    def find_resume_point(self, issues: List[Dict]) -> int:
        """
        Find the index where processing should resume.
        Returns the index of the first issue that hasn't been processed yet.

        Args:
            issues: List of issue dictionaries

        Returns:
            Index to start processing from (0 if none processed, len(issues) if all processed)
        """
        for i, issue in enumerate(issues):
            # Check if this issue has been processed (has first_authority_response_date field)
            if 'first_authority_response_date' not in issue:
                return i

        # All issues have been processed
        return len(issues)


def main():
    """Main entry point"""
    print("🔄 Starting Authority Response Scraper - Processing ALL Issues")
    print("⚠️  WARNING: This will modify data/raw files by adding first_authority_response_date field")
    print("⚠️  Make sure you have a backup of data/raw before proceeding!")
    print("💡 This process will take a long time (potentially hours) for all ~21K issues")
    print("🔄 RESUME CAPABLE: Will automatically resume from last processed issue if interrupted")

    # Ask for confirmation
    response = input("\nDo you want to continue? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("Operation cancelled.")
        return

    with AuthorityResponseScraper() as scraper:
        scraper.process_all_issues()

    print("✅ Authority response scraping completed")


if __name__ == "__main__":
    main()