#!/usr/bin/env python3
"""
Test script to validate the optimizations for disk space usage.
This script tests the resource monitoring and buffer management improvements.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add the src directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent / "src"))

from jarokelo_tracker.scraper.data_manager import DataManager


def test_resource_monitoring():
    """Test that resource monitoring works correctly"""
    print("Testing resource monitoring...")
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Test with small buffer size
        dm = DataManager(data_dir=temp_dir, buffer_size=5)
        
        # Check that monitoring is enabled
        assert dm._monitor_resources == True
        print("✓ Resource monitoring initialized correctly")
        
        # Test resource check (should not crash)
        try:
            dm._check_resource_usage(force=True)
            print("✓ Resource monitoring runs without errors")
        except Exception as e:
            print(f"✗ Resource monitoring failed: {e}")
            return False
            
    return True


def test_buffer_size_reduction():
    """Test that the buffer size has been reduced correctly"""
    print("Testing buffer size reduction...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Test default buffer size
        dm = DataManager(data_dir=temp_dir)
        
        if dm.buffer_size == 50:
            print("✓ Default buffer size correctly reduced to 50")
        else:
            print(f"✗ Buffer size is {dm.buffer_size}, expected 50")
            return False
            
        # Test custom buffer size
        dm_custom = DataManager(data_dir=temp_dir, buffer_size=25)
        if dm_custom.buffer_size == 25:
            print("✓ Custom buffer size works correctly")
        else:
            print(f"✗ Custom buffer size is {dm_custom.buffer_size}, expected 25")
            return False
            
    return True


def test_cleanup_functionality():
    """Test that cleanup functionality works"""
    print("Testing cleanup functionality...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        dm = DataManager(data_dir=temp_dir)
        
        # Create some test temporary files
        temp_file1 = os.path.join(temp_dir, ".tmp_test_file1")
        temp_file2 = os.path.join(temp_dir, "test_file.tmp")
        
        with open(temp_file1, 'w') as f:
            f.write("test content")
        with open(temp_file2, 'w') as f:
            f.write("test content")
            
        # Verify files exist
        assert os.path.exists(temp_file1)
        assert os.path.exists(temp_file2)
        
        # Run cleanup
        dm.cleanup_temp_files()
        
        # Check that temp files are removed
        if not os.path.exists(temp_file1) and not os.path.exists(temp_file2):
            print("✓ Temporary files cleaned up correctly")
        else:
            print("✗ Some temporary files were not cleaned up")
            return False
            
    return True


def main():
    """Run all tests"""
    print("Running optimization validation tests...\n")
    
    tests = [
        test_buffer_size_reduction,
        test_resource_monitoring,
        test_cleanup_functionality,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            print()
        except Exception as e:
            print(f"✗ Test {test.__name__} failed with exception: {e}\n")
    
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All optimization tests passed!")
        return 0
    else:
        print("❌ Some tests failed. Check the output above.")
        return 1


if __name__ == "__main__":
    exit(main())