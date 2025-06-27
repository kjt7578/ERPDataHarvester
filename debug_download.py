#!/usr/bin/env python3
"""
Debug script to analyze PDF download issues
"""
import logging
from pathlib import Path
from login_session import ERPSession
from config import config

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def debug_download():
    """Debug the download process"""
    print("=== PDF Download Debug ===")
    
    # Initialize session
    session = ERPSession(
        base_url=config.BASE_URL,
        username=config.USERNAME,
        password=config.PASSWORD,
        use_selenium=True,
        headless=False  # Show browser for debugging
    )
    
    try:
        # Login
        print("Logging in...")
        if not session.login():
            print("❌ Login failed")
            return
        
        print("✅ Login successful")
        
        # Test download URL
        test_url = "http://erp.hrcap.com/file/procDownload/98a99a32-599f-e1c4-5dd3-df306c5d66f1"
        test_file = Path("debug_download.pdf")
        
        print(f"Testing download from: {test_url}")
        
        # Try download
        success = session.download_file(test_url, str(test_file))
        
        if test_file.exists():
            file_size = test_file.stat().st_size
            print(f"File downloaded: {file_size} bytes")
            
            # Check file content
            with open(test_file, 'rb') as f:
                first_bytes = f.read(100)
                
            print(f"First 100 bytes: {first_bytes}")
            
            # Check if it's HTML
            if b'<html' in first_bytes.lower() or b'<!doctype' in first_bytes.lower():
                print("❌ Downloaded file is HTML (likely login page)")
                
                # Show HTML content
                with open(test_file, 'r', encoding='utf-8', errors='ignore') as f:
                    html_content = f.read(1000)
                print("HTML content preview:")
                print(html_content[:500])
                
            elif first_bytes.startswith(b'%PDF'):
                print("✅ Downloaded file appears to be a valid PDF")
            else:
                print("❓ Downloaded file is unknown format")
                
            # Cleanup
            test_file.unlink()
        else:
            print("❌ No file was downloaded")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        session.close()

if __name__ == "__main__":
    debug_download() 