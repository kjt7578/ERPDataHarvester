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
from file_utils import validate_pdf_file, ensure_file_permissions, generate_resume_filename

logger = logging.getLogger(__name__)


class PDFDownloader:
    """Handles PDF file downloads with retry and progress tracking"""
    
    def __init__(self, session: Any, max_retries: int = 3, 
                 retry_delay: int = 5, timeout: int = 60):
        """
        Initialize PDF Downloader
        
        Args:
            session: HTTP session or ERPSession for downloading
            max_retries: Maximum retry attempts
            retry_delay: Delay between retries in seconds
            timeout: Download timeout in seconds
        """
        self.session = session
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        
        # Statistics tracking
        self.download_stats = {
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'total_size_mb': 0.0,
            'successful_candidates': [],  # List of successful candidate info
            'failed_candidates': [],      # List of failed candidate info
            'skipped_candidates': []      # List of skipped candidate info
        }
        
    def download_resume(self, url: str, save_path: Path, 
                      candidate_info: Dict[str, Any]) -> bool:
        """
        Download resume file with retry logic
        
        Args:
            url: Resume URL
            save_path: Path to save file
            candidate_info: Candidate information dict
            
        Returns:
            True if successful
        """
        import zipfile
        import tempfile
        import time
        from pathlib import Path as PathLib
        
        # Skip if file already exists
        if save_path.exists():
            file_size_mb = save_path.stat().st_size / (1024 * 1024)
            logger.info(f"Resume already exists for {candidate_info.get('name', 'Unknown')} ({file_size_mb:.2f} MB)")
            self._record_skip(candidate_info)
            return True
            
        # Retry logic
        for attempt in range(1, self.max_retries + 1):
            self._set_current_attempt(attempt)
            logger.info(f"Downloading resume for {candidate_info.get('name', 'Unknown')} ({candidate_info.get('candidate_id', 'Unknown')}) - Attempt {attempt}")
            
            success = self._download_resume_attempt(url, save_path, candidate_info)
            if success:
                self._record_success_with_candidate(candidate_info, save_path)
                return True
                
            if attempt < self.max_retries:
                logger.info(f"Retrying in {self.retry_delay} seconds...")
                time.sleep(self.retry_delay)
                
        logger.error(f"Failed to download resume for {candidate_info.get('name', 'Unknown')} after {self.max_retries} attempts")
        self._record_failure_with_candidate(candidate_info)
        return False
        
    def _download_resume_attempt(self, url: str, save_path: Path, 
                               candidate_info: Dict[str, Any]) -> bool:
        """
        Single download attempt
        
        Args:
            url: Resume URL
            save_path: Path to save file
            candidate_info: Candidate information dict
            
        Returns:
            True if successful
        """
        import zipfile
        import tempfile
        import shutil
        
        try:
            # Download to a temporary location first
            temp_dir = Path(tempfile.mkdtemp())
            temp_file = temp_dir / "temp_download"
            
            # Download the file
            if not self._download_file(url, temp_file):
                return False
                
            # Check if downloaded file is a ZIP archive
            if self._is_zip_file(temp_file):
                logger.info(f"Downloaded file is a ZIP archive, extracting...")
                
                # Extract ZIP file to find resume files
                # First, check what's in the ZIP
                with zipfile.ZipFile(temp_file, 'r') as zip_ref:
                    file_list = zip_ref.namelist()
                    
                    # Look for PDF files first
                    pdf_files = [f for f in file_list if f.lower().endswith('.pdf')]
                    
                    # Look for .doc files (old Word format)
                    doc_files = [f for f in file_list if f.lower().endswith('.doc')]
                    
                    if pdf_files:
                        # Extract the first PDF file found
                        resume_filename = pdf_files[0]
                        logger.info(f"Found PDF in ZIP: {resume_filename}")
                        
                        # Extract to temporary location
                        zip_ref.extract(resume_filename, temp_dir)
                        extracted_file = temp_dir / resume_filename
                        
                        # Move to final location (keep .pdf extension)
                        final_save_path = save_path.with_suffix('.pdf')
                        shutil.move(str(extracted_file), str(final_save_path))
                        
                        # Cleanup
                        shutil.rmtree(temp_dir)
                        
                        # Validate the extracted PDF
                        if validate_pdf_file(final_save_path):
                            file_size_mb = final_save_path.stat().st_size / (1024 * 1024)
                            logger.info(f"✅ Successfully downloaded and extracted PDF ({file_size_mb:.2f} MB)")
                            self._record_success(file_size_mb)
                            return True
                        else:
                            logger.error("Extracted file is not a valid PDF")
                            final_save_path.unlink(missing_ok=True)
                            return False
                    
                    # If no PDF, check for .doc files (old Word format)
                    elif doc_files:
                        is_old_word_doc = True
                        old_doc_filename = doc_files[0]
                    # If no PDF or .doc, check for .docx documents
                    elif 'word/document.xml' in file_list:
                        is_word_doc = True
                    else:
                        is_word_doc = False
                        is_old_word_doc = False
                
                # Handle old Word documents (.doc files)
                if 'is_old_word_doc' in locals() and is_old_word_doc:
                    logger.info(f"Found old Word document (.doc) in ZIP: {old_doc_filename}")
                    
                    # Extract the .doc file
                    with zipfile.ZipFile(temp_file, 'r') as zip_ref:
                        zip_ref.extract(old_doc_filename, temp_dir)
                        extracted_file = temp_dir / old_doc_filename
                        
                        # Move to final location (keep .doc extension)
                        final_save_path = save_path.with_suffix('.doc')
                        shutil.move(str(extracted_file), str(final_save_path))
                    
                    # Cleanup
                    shutil.rmtree(temp_dir)
                    
                    # Check if it's a valid file
                    if final_save_path.exists() and final_save_path.stat().st_size > 0:
                        file_size_mb = final_save_path.stat().st_size / (1024 * 1024)
                        logger.info(f"✅ Successfully downloaded old Word document (.doc) ({file_size_mb:.2f} MB)")
                        self._record_success(file_size_mb)
                        return True
                    else:
                        logger.error("Failed to save old Word document")
                        final_save_path.unlink(missing_ok=True)
                        return False
                        
                # Handle new Word documents (.docx files)
                elif 'is_word_doc' in locals() and is_word_doc:
                    logger.info("Found Word document in ZIP, extracting as .docx file")
                    
                    # Save the entire ZIP as a .docx file (Word documents are ZIP archives)
                    final_save_path = save_path.with_suffix('.docx')
                    shutil.move(str(temp_file), str(final_save_path))
                    
                    # Cleanup
                    shutil.rmtree(temp_dir)
                    
                    # Check if it's a valid file
                    if final_save_path.exists() and final_save_path.stat().st_size > 0:
                        file_size_mb = final_save_path.stat().st_size / (1024 * 1024)
                        logger.info(f"✅ Successfully downloaded Word document ({file_size_mb:.2f} MB)")
                        self._record_success(file_size_mb)
                        return True
                    else:
                        logger.error("Failed to save Word document")
                        final_save_path.unlink(missing_ok=True)
                        return False
                else:
                    logger.error("No PDF or Word documents found in ZIP archive")
                    logger.debug(f"ZIP contents: {file_list}")
                    return False
            else:
                # Not a ZIP file, treat as regular file
                shutil.move(str(temp_file), str(save_path))
                
                # Cleanup temp directory
                shutil.rmtree(temp_dir)
                
                # Validate file
                if validate_pdf_file(save_path):
                    file_size_mb = save_path.stat().st_size / (1024 * 1024)
                    logger.info(f"✅ Successfully downloaded PDF ({file_size_mb:.2f} MB)")
                    self._record_success(file_size_mb)
                    return True
                else:
                    logger.error(f"Downloaded file is not a valid PDF for {candidate_info.get('name', 'Unknown')}")
                    save_path.unlink(missing_ok=True)
                    return False
                
        except Exception as e:
            logger.error(f"Error downloading resume: {e}")
            save_path.unlink(missing_ok=True)
            
            # Cleanup temp directory if it exists
            try:
                if 'temp_dir' in locals():
                    shutil.rmtree(temp_dir, ignore_errors=True)
            except:
                pass
                
            return False
            
    def _is_zip_file(self, file_path: Path) -> bool:
        """Check if file is a ZIP archive"""
        try:
            with open(file_path, 'rb') as f:
                # ZIP files start with 'PK'
                header = f.read(2)
                return header == b'PK'
        except Exception:
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
            logger.debug(f"Using ERPSession to download: {url}")
            return self.session.download_file(url, str(save_path))
        else:
            # Using requests.Session
            logger.debug(f"Using requests.Session to download: {url}")
            response = self.session.get(url, stream=True, timeout=self.timeout)
            response.raise_for_status()
            
            # Log response details for debugging
            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Content-Type: {response.headers.get('Content-Type', 'Unknown')}")
            logger.debug(f"Content-Length: {response.headers.get('Content-Length', 'Unknown')}")
            
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
            'total_size_mb': 0.0,
            'successful_candidates': [],
            'failed_candidates': [],
            'skipped_candidates': []
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

    def _get_current_attempt(self) -> int:
        """Get current download attempt number"""
        return getattr(self, '_current_attempt', 1)
        
    def _set_current_attempt(self, attempt: int):
        """Set current download attempt number"""
        self._current_attempt = attempt
        
    def _record_skip(self, candidate_info: Dict[str, Any]):
        """Record a skipped download"""
        self.download_stats['skipped'] += 1
        self.download_stats['skipped_candidates'].append(candidate_info)
        
    def _record_failure(self):
        """Record a failed download"""
        self.download_stats['failed'] += 1
        
    def _record_success(self, file_size_mb: float):
        """Record a successful download"""
        self.download_stats['successful'] += 1
        self.download_stats['total_size_mb'] += file_size_mb 

    def _record_success_with_candidate(self, candidate_info: Dict[str, Any], save_path: Path):
        """Record a successful download with candidate information"""
        self._record_success(save_path.stat().st_size / (1024 * 1024))
        self.download_stats['successful_candidates'].append(candidate_info)
        
    def _record_failure_with_candidate(self, candidate_info: Dict[str, Any]):
        """Record a failed download with candidate information"""
        self._record_failure()
        self.download_stats['failed_candidates'].append(candidate_info) 