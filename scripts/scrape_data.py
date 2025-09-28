#!/usr/bin/env python3
"""
Járókelő Scraper Script

This script provides a command-line interface to scrape municipal issue data
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
    parser.add_argument("--data-dir", type=str, default="data/raw", 
                       help="Directory to store data files")

    args = parser.parse_args()
    
    # Convert headless string to boolean
    headless = args.headless.lower() == 'true'
    
    # Handle 'bs' alias for 'beautifulsoup'
    backend = 'beautifulsoup' if args.backend == 'bs' else args.backend
    
    # Initialize and run scraper
    try:
        with JarokeloScraper(
            data_dir=args.data_dir,
            backend=backend,
            headless=headless
        ) as scraper:
            scraper.scrape(
                start_page=args.start_page,
                until_date=args.until_date,
                stop_on_existing=not args.continue_scraping,
                continue_scraping=args.continue_scraping
            )
    except KeyboardInterrupt:
        print("\nScraping interrupted by user")
    except Exception as e:
        print(f"Scraping failed: {e}")
        raise


if __name__ == "__main__":
    main()