"""
PDF download module with retry logic and progress tracking
"""
import os
import re
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Callable
from urllib.parse import urlparse, unquote
import requests
from tqdm import tqdm

from config import config
from file_utils import validate_pdf_file, ensure_file_permissions

logger = logging.getLogger(__name__)


class PDFDownloader:
    """Handles PDF file downloads with retry and progress tracking"""
    
    def __init__(self, session: Any, max_retries: int = 3, 
                 retry_delay: int = 5, timeout: int = 60):
        """
        Initialize downloader
        
        Args:
            session: ERPSession instance or requests.Session
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
            timeout: Download timeout in seconds
        """
        self.session = session
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        self.download_stats = {
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'total_size_mb': 0.0
        }
        
    def download_resume(self, url: str, save_path: Path, 
                       candidate_info: Dict[str, Any],
                       progress_callback: Optional[Callable] = None) -> bool:
        """
        Download resume PDF from URL
        
        Args:
            url: Download URL
            save_path: Path to save file
            candidate_info: Candidate information for logging
            progress_callback: Optional callback for progress updates
            
        Returns:
            True if successful, False otherwise
        """
        candidate_id = candidate_info.get('candidate_id', 'unknown')
        candidate_name = candidate_info.get('name', 'unknown')
        
        # Check if file already exists
        if save_path.exists():
            if validate_pdf_file(save_path):
                logger.info(f"Resume already exists for {candidate_name} ({candidate_id})")
                self.download_stats['skipped'] += 1
                return True
            else:
                logger.warning(f"Invalid PDF exists for {candidate_name}, re-downloading")
                save_path.unlink()
                
        # Ensure directory exists
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Attempt download with retries
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Downloading resume for {candidate_name} ({candidate_id}) - Attempt {attempt + 1}")
                
                if self._download_file(url, save_path, progress_callback):
                    # Validate downloaded file
                    if validate_pdf_file(save_path):
                        ensure_file_permissions(save_path)
                        self.download_stats['successful'] += 1
                        
                        # Update total size
                        size_mb = save_path.stat().st_size / (1024 * 1024)
                        self.download_stats['total_size_mb'] += size_mb
                        
                        logger.info(f"Successfully downloaded resume for {candidate_name} ({size_mb:.2f} MB)")
                        return True
                    else:
                        logger.error(f"Downloaded file is not a valid PDF for {candidate_name}")
                        save_path.unlink()
                        
            except requests.exceptions.Timeout:
                logger.error(f"Timeout downloading resume for {candidate_name}")
            except requests.exceptions.ConnectionError:
                logger.error(f"Connection error downloading resume for {candidate_name}")
            except Exception as e:
                logger.error(f"Error downloading resume for {candidate_name}: {e}")
                
            # Wait before retry
            if attempt < self.max_retries - 1:
                logger.info(f"Retrying in {self.retry_delay} seconds...")
                time.sleep(self.retry_delay)
                
        # All attempts failed
        self.download_stats['failed'] += 1
        logger.error(f"Failed to download resume for {candidate_name} after {self.max_retries} attempts")
        return False
        
    def _download_file(self, url: str, save_path: Path, 
                      progress_callback: Optional[Callable] = None) -> bool:
        """
        Internal method to download file with progress
        
        Args:
            url: Download URL
            save_path: Path to save file
            progress_callback: Optional progress callback
            
        Returns:
            True if successful
        """
        # Handle session type (ERPSession or requests.Session)
        if hasattr(self.session, 'download_file'):
            # Using ERPSession
            return self.session.download_file(url, str(save_path))
        else:
            # Using requests.Session
            response = self.session.get(url, stream=True, timeout=self.timeout)
            response.raise_for_status()
            
            # Get total file size
            total_size = int(response.headers.get('content-length', 0))
            
            # Download with progress bar
            with open(save_path, 'wb') as f:
                if total_size > 0:
                    # Use tqdm for progress bar
                    with tqdm(total=total_size, unit='iB', unit_scale=True) as pbar:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                pbar.update(len(chunk))
                                
                                if progress_callback:
                                    progress = pbar.n / total_size
                                    progress_callback(progress)
                else:
                    # No content length, download without progress
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            
            return True
            
    def download_batch(self, download_tasks: list,
                      progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Download multiple resumes in batch
        
        Args:
            download_tasks: List of (url, save_path, candidate_info) tuples
            progress_callback: Optional callback for overall progress
            
        Returns:
            Dictionary with download statistics
        """
        total_tasks = len(download_tasks)
        logger.info(f"Starting batch download of {total_tasks} resumes")
        
        for i, (url, save_path, candidate_info) in enumerate(download_tasks):
            # Update overall progress
            if progress_callback:
                progress_callback(i / total_tasks, f"Downloading {i+1}/{total_tasks}")
                
            # Download individual file
            self.download_resume(url, save_path, candidate_info)
            
        # Final progress update
        if progress_callback:
            progress_callback(1.0, "Download complete")
            
        return self.get_statistics()
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get download statistics"""
        total = (self.download_stats['successful'] + 
                self.download_stats['failed'] + 
                self.download_stats['skipped'])
                
        stats = self.download_stats.copy()
        stats['total'] = total
        stats['success_rate'] = (
            self.download_stats['successful'] / total * 100 
            if total > 0 else 0
        )
        
        return stats
        
    def reset_statistics(self):
        """Reset download statistics"""
        self.download_stats = {
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'total_size_mb': 0.0
        }
        
    def estimate_download_time(self, file_count: int, 
                              avg_file_size_mb: float = 2.0) -> float:
        """
        Estimate total download time
        
        Args:
            file_count: Number of files to download
            avg_file_size_mb: Average file size in MB
            
        Returns:
            Estimated time in seconds
        """
        # Assume average download speed of 1 MB/s
        avg_download_speed_mbps = 1.0
        
        # Add overhead for requests and retries
        overhead_per_file = 2.0  # seconds
        
        total_size_mb = file_count * avg_file_size_mb
        download_time = total_size_mb / avg_download_speed_mbps
        total_overhead = file_count * overhead_per_file
        
        return download_time + total_overhead
        
    @staticmethod
    def get_filename_from_url(url: str) -> Optional[str]:
        """
        Extract filename from URL
        
        Args:
            url: Download URL
            
        Returns:
            Filename or None
        """
        try:
            parsed = urlparse(url)
            path = unquote(parsed.path)
            filename = os.path.basename(path)
            
            if filename and '.' in filename:
                return filename
        except:
            pass
            
        return None
        
    @staticmethod
    def get_resume_urls_from_page(html: str, base_url: str) -> list:
        """
        Extract all resume URLs from a page
        
        Args:
            html: Page HTML content
            base_url: Base URL for resolving relative links
            
        Returns:
            List of resume URLs
        """
        from bs4 import BeautifulSoup
        from urllib.parse import urljoin
        
        soup = BeautifulSoup(html, 'html.parser')
        resume_urls = []
        
        # Find all links that might be resumes
        patterns = [
            {'href': re.compile(r'\.pdf($|\?)', re.I)},
            {'href': re.compile(r'resume|cv', re.I)},
            {'class': re.compile(r'download|resume', re.I)}
        ]
        
        for pattern in patterns:
            links = soup.find_all('a', pattern)
            for link in links:
                if link.get('href'):
                    full_url = urljoin(base_url, link['href'])
                    if full_url not in resume_urls:
                        resume_urls.append(full_url)
                        
        return resume_urls 