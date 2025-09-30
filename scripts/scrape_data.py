#!/usr/bin/env python3
"""
Járókelő Scraper Scr    # Initialize and run scraper
    try:
        print("🔄 Running in synchronous processing mode")
        
        with JarokeloScraper(
            data_dir=args.data_dir,
            backend=backend,
            headless=headless,
            buffer_size=args.buffer_size
        ) as scraper:
            # Handle different operation modes
            if args.fetch_changed_urls:
                # Recent URL Fetcher Mode - Only find URLs with status changes
                print("🔍 Running in URL Change Detection Mode")
                print(f"Detecting changed URLs from last {args.cutoff_months} months...")
                changed_urls_count = scraper.detect_changed_urls_fast(
                    cutoff_months=args.cutoff_months,
                    output_file="recent_changed_urls.txt"
                )
                print(f"✅ Found {changed_urls_count} URLs with status changes")
                
            elif args.load_old_pending:
                # Old Pending Issues Loader Mode
                print("📋 Running in Old Pending Issues Loader Mode")
                print(f"Extracting pending issues older than {args.cutoff_months} months...")
                pending_urls_count = scraper.extract_old_pending_urls(
                    cutoff_months=args.cutoff_months,
                    output_file="old_pending_urls.txt"
                )
                print(f"✅ Found {pending_urls_count} old pending URLs")
                
            elif args.scrape_urls_file:
                # Resolution Date Scraper Mode - Process specific URLs from file
                print("🎯 Running in Resolution Date Scraper Mode")
                print(f"Scraping URLs from file: {args.scrape_urls_file}")
                
                # The scrape_urls_file mode is optimized for resolution date extraction
                # This is used for Jobs 4 & 5 in the pipeline
                success_count = scraper.scrape_urls_from_file(
                    urls_file=args.scrape_urls_file,
                    resolution_focus=True  # Enable resolution date optimization
                )
                print(f"✅ Successfully updated resolution dates for {success_count} URLs")
                
            else:
                # Standard Comprehensive Scraping Mode
                print("🚀 Running in Comprehensive Scraping Mode")
                scraper.scrape(
                    start_page=args.start_page,
                    until_date=args.until_date,
                    stop_on_existing=not args.continue_scraping and not args.update_existing_status,
                    continue_scraping=args.continue_scraping,
                    update_existing_status=args.update_existing_status
                )t provides a command-line interface to scrape municipal issue data
from the Járókelő website using the core scraper module.
"""

import argparse
from jarokelo_tracker.scraper import JarokeloScraper


def main():
    """Main entry point for the scraper script"""
    parser = argparse.ArgumentParser(description="Járókelő scraper")
    parser.add_argument("--backend", type=str, choices=['selenium', 'beautifulsoup', 'bs'], 
                       default='beautifulsoup', help="Scraper backend to use (selenium/beautifulsoup/bs)")
    parser.add_argument("--headless", type=str, choices=['true', 'false'], default='true', 
                       help="Run browser in headless mode (true/false)")
    parser.add_argument("--start-page", type=int, default=1, 
                       help="Page number to start scraping from")
    parser.add_argument("--until-date", type=str, default=None, 
                       help="Scrape until this date (YYYY-MM-DD), inclusive")
    parser.add_argument("--continue-scraping", action="store_true", 
                       help="Resume automatically based on existing data")
    parser.add_argument("--update-existing-status", action="store_true", 
                       help="Update status of existing records (for re-checking solved/waiting status)")
    parser.add_argument("--data-dir", type=str, default="data/raw", 
                       help="Directory to store data files")
    parser.add_argument("--buffer-size", type=int, default=100, 
                       help="Number of records to buffer in memory before writing to disk (used for comprehensive scraping, ignored for status updates)")

    parser.add_argument("--cutoff-months", type=int, default=3,
                       help="Months cutoff for separating recent vs old status updates (default: 3)")
    parser.add_argument("--fetch-changed-urls", action="store_true",
                       help="Fast detection of recently changed URLs only (output to file)")
    parser.add_argument("--scrape-urls-file", type=str, default=None,
                       help="Scrape specific URLs from file (one URL per line)")
    parser.add_argument("--load-old-pending", action="store_true",
                       help="Load old pending URLs and save to file")

    args = parser.parse_args()
    
    # Convert headless string to boolean
    headless = args.headless.lower() == 'true'
    
    # Handle 'bs' alias for 'beautifulsoup'
    backend = 'beautifulsoup' if args.backend == 'bs' else args.backend
    
    # Initialize and run scraper
    try:
        print("� Running in synchronous processing mode")
        
        with JarokeloScraper(
            data_dir=args.data_dir,
            backend=backend,
            headless=headless,
            buffer_size=args.buffer_size
        ) as scraper:
            scraper.scrape(
                start_page=args.start_page,
                until_date=args.until_date,
                stop_on_existing=not args.continue_scraping and not args.update_existing_status,
                continue_scraping=args.continue_scraping,
                update_existing_status=args.update_existing_status
            )
    except KeyboardInterrupt:
        print("\nScraping interrupted by user")
    except Exception as e:
        print(f"Scraping failed: {e}")
        raise


if __name__ == "__main__":
    main()