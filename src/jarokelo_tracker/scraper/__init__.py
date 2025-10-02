"""
Járókelő Scraper Module

This module provides scraping functionality for the Járókelő municipal issue tracking system.
Supports BeautifulSoup backend with GPS coordinate extraction.
"""

from .core import JarokeloScraper
from .gps_extractor import extract_gps_coordinates, is_valid_coordinate, is_budapest_coordinate
from .data_manager import DataManager

__all__ = [
    'JarokeloScraper',
    'extract_gps_coordinates',
    'is_valid_coordinate', 
    'is_budapest_coordinate',
    'DataManager'
]