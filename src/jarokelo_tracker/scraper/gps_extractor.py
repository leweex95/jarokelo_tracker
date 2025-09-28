"""
GPS Coordinate Extraction Module

This module provides functionality to extract GPS coordinates from Járókelő web pages
using multiple detection methods including meta tags, JavaScript, and pattern matching.
"""

import re
from typing import Tuple, Optional
from selenium.webdriver.common.by import By


def is_valid_coordinate(coord_str: str) -> bool:
    """Check if a string represents a valid coordinate"""
    try:
        coord = float(coord_str)
        # Basic sanity check for latitude/longitude ranges
        return -180 <= coord <= 180
    except (ValueError, TypeError):
        return False


def is_budapest_coordinate(lat_str: str, lng_str: str) -> bool:
    """Check if coordinates are in Budapest area"""
    try:
        lat, lng = float(lat_str), float(lng_str)
        # Budapest approximate bounds
        # Latitude: 47.35 to 47.65
        # Longitude: 18.9 to 19.4
        return (47.35 <= lat <= 47.65) and (18.9 <= lng <= 19.4)
    except (ValueError, TypeError):
        return False


def extract_gps_coordinates(page_source: str, driver=None) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract GPS coordinates from page source using multiple methods
    Returns (latitude, longitude) as strings, or (None, None) if not found
    """
    
    # Method 1: Check for meta tags with OpenGraph and Place properties
    meta_patterns = [
        r'<meta\s+property=["\']og:latitude["\']\s+content=["\']([+-]?\d+\.?\d*)["\']',
        r'<meta\s+property=["\']og:longitude["\']\s+content=["\']([+-]?\d+\.?\d*)["\']',
        r'<meta\s+property=["\']place:location:latitude["\']\s+content=["\']([+-]?\d+\.?\d*)["\']',
        r'<meta\s+property=["\']place:location:longitude["\']\s+content=["\']([+-]?\d+\.?\d*)["\']',
    ]
    
    lat_val, lng_val = None, None
    
    for pattern in meta_patterns:
        matches = re.finditer(pattern, page_source, re.IGNORECASE)
        for match in matches:
            coord = match.group(1)
            if is_valid_coordinate(coord):
                if 'lat' in pattern.lower():
                    lat_val = coord
                elif 'lon' in pattern.lower():
                    lng_val = coord
    
    if lat_val and lng_val and is_budapest_coordinate(lat_val, lng_val):
        return lat_val, lng_val
    
    # Method 2: Check for JavaScript map initialization data
    js_patterns = [
        r'window\.mapInitData\s*=\s*{[^}]*"center"\s*:\s*{\s*"lat"\s*:\s*([+-]?\d+\.?\d*)\s*,\s*"lng"\s*:\s*([+-]?\d+\.?\d*)\s*}',
        r'"center"\s*:\s*{\s*"lat"\s*:\s*([+-]?\d+\.?\d*)\s*,\s*"lng"\s*:\s*([+-]?\d+\.?\d*)\s*}',
        r'center\s*[:=]\s*{\s*lat\s*:\s*([+-]?\d+\.?\d*)\s*,\s*lng\s*:\s*([+-]?\d+\.?\d*)\s*}',
    ]
    
    for pattern in js_patterns:
        matches = re.finditer(pattern, page_source, re.IGNORECASE)
        for match in matches:
            if len(match.groups()) == 2:
                lat, lng = match.groups()
                if is_valid_coordinate(lat) and is_valid_coordinate(lng):
                    if is_budapest_coordinate(lat, lng):
                        return lat, lng
    
    # Method 3: Common coordinate patterns (fallback)
    coord_patterns = [
        r'lat(?:itude)?["\']?\s*[:=]\s*([+-]?\d+\.?\d*)',
        r'lng?(?:ongitude)?["\']?\s*[:=]\s*([+-]?\d+\.?\d*)',
        r'latitude["\']?\s*[:=]\s*([+-]?\d+\.?\d*)',
        r'longitude["\']?\s*[:=]\s*([+-]?\d+\.?\d*)',
        r'coords?\s*[:=]\s*\[([+-]?\d+\.?\d*),\s*([+-]?\d+\.?\d*)\]',
        r'center\s*[:=]\s*\[([+-]?\d+\.?\d*),\s*([+-]?\d+\.?\d*)\]',
        r'position\s*[:=]\s*\{[^}]*lat[^}]*:\s*([+-]?\d+\.?\d*)[^}]*lng?[^}]*:\s*([+-]?\d+\.?\d*)',
        r'([+-]?\d{1,2}\.\d+),\s*([+-]?\d{1,3}\.\d+)',  # Generic lat,lng pattern
    ]
    
    coordinates_found = []
    
    # Search for coordinate patterns in page source
    for pattern in coord_patterns:
        matches = re.finditer(pattern, page_source, re.IGNORECASE)
        for match in matches:
            if len(match.groups()) == 1:
                coord = match.group(1)
                if is_valid_coordinate(coord):
                    coordinates_found.append(coord)
            elif len(match.groups()) == 2:
                lat, lng = match.groups()
                if is_valid_coordinate(lat) and is_valid_coordinate(lng):
                    if is_budapest_coordinate(lat, lng):
                        return lat, lng  # Return first valid Budapest coordinate pair
    
    # If using Selenium, also check data attributes
    if driver:
        try:
            # Check for coordinates in data attributes
            elements_with_coords = []
            elements_with_coords.extend(driver.find_elements(By.CSS_SELECTOR, "[data-lat]"))
            elements_with_coords.extend(driver.find_elements(By.CSS_SELECTOR, "[data-lng]"))
            elements_with_coords.extend(driver.find_elements(By.CSS_SELECTOR, "[data-latitude]"))
            elements_with_coords.extend(driver.find_elements(By.CSS_SELECTOR, "[data-longitude]"))
            
            lat_val, lng_val = None, None
            for element in elements_with_coords:
                for attr_name in element.get_property('attributes'):
                    attr_value = element.get_attribute(attr_name)
                    if attr_name and attr_value:
                        if 'lat' in attr_name.lower() and not 'lng' in attr_name.lower():
                            if is_valid_coordinate(attr_value):
                                lat_val = attr_value
                        elif 'lng' in attr_name.lower() or 'lon' in attr_name.lower():
                            if is_valid_coordinate(attr_value):
                                lng_val = attr_value
            
            if lat_val and lng_val and is_budapest_coordinate(lat_val, lng_val):
                return lat_val, lng_val
        except Exception:
            pass  # Ignore errors in data attribute extraction
    
    return None, None