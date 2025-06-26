"""
Main entry point for ERP Resume Harvester
"""
import sys
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import colorlog
import time

from config import config
from login_session import ERPSession
from scraper import ERPScraper, CandidateInfo
from downloader import PDFDownloader
from metadata_saver import MetadataSaver
from file_utils import (
    generate_filename_from_template, 
    extract_date_parts,
    create_directory_structure
)


def setup_logging(log_level: str = 'INFO'):
    """Setup colored logging"""
    handler = colorlog.StreamHandler()
    handler.setFormatter(
        colorlog.ColoredFormatter(
            '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        )
    )
    
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))
    logger.addHandler(handler)
    
    # Also log to file
    log_file = config.logs_dir / f'harvest_{datetime.now().strftime("%Y%m%d")}.log'
    config.logs_dir.mkdir(parents=True, exist_ok=True)
    
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(
        logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
    logger.addHandler(file_handler)


class ERPResumeHarvester:
    """Main orchestrator for resume harvesting process"""
    
    def __init__(self, use_selenium: bool = False):
        """
        Initialize harvester
        
        Args:
            use_selenium: Use Selenium instead of requests
        """
        self.use_selenium = use_selenium
        self.session: Optional[ERPSession] = None
        self.scraper: Optional[ERPScraper] = None
        self.downloader: Optional[PDFDownloader] = None
        self.metadata_saver: Optional[MetadataSaver] = None
        
        # Statistics
        self.stats = {
            'candidates_found': 0,
            'pages_processed': 0,
            'start_time': None,
            'end_time': None
        }
        
    def initialize(self) -> bool:
        """Initialize all components"""
        try:
            # Validate configuration
            if not config.validate():
                logging.error("Configuration validation failed")
                return False
                
            # Create directories
            config.create_directories()
            
            # Initialize session
            self.session = ERPSession(
                base_url=config.erp_base_url,
                username=config.erp_username,
                password=config.erp_password,
                use_selenium=True,
                headless=False
            )
            
            # Login
            logging.info("Logging into ERP system...")
            if not self.session.login():
                logging.error("Failed to login to ERP system")
                return False
                
            logging.info("Successfully logged in")
            
            # Initialize other components
            self.scraper = ERPScraper(config.erp_base_url)
            self.downloader = PDFDownloader(
                session=self.session,
                max_retries=config.max_retries,
                retry_delay=config.retry_delay,
                timeout=config.download_timeout
            )
            self.metadata_saver = MetadataSaver(
                metadata_dir=config.metadata_dir,
                results_dir=config.results_dir
            )
            
            return True
            
        except Exception as e:
            logging.error(f"Initialization error: {e}")
            return False
            
    def harvest_candidates(self, start_page: int = 1, 
                          specific_id: Optional[str] = None) -> bool:
        """
        Main harvesting process
        
        Args:
            start_page: Page number to start from
            specific_id: Specific candidate ID to process (optional)
            
        Returns:
            True if successful
        """
        if not self.initialize():
            return False
            
        self.stats['start_time'] = datetime.now()
        
        try:
            if specific_id:
                # Process specific candidate
                logging.info(f"Processing specific candidate: {specific_id}")
                return self._process_specific_candidate(specific_id)
            else:
                # Process all candidates
                logging.info("Starting full harvest process...")
                return self._process_all_candidates(start_page)
                
        except Exception as e:
            logging.error(f"Harvest error: {e}")
            return False
        finally:
            self.stats['end_time'] = datetime.now()
            self._print_summary()
            self.cleanup()
            
    def _process_all_candidates(self, start_page: int) -> bool:
        """Process all candidates from list pages"""
        all_candidates = []
        page = start_page
        
        while True:
            # Construct list page URL for HRcap ERP system
            list_url = f"{config.erp_base_url}/searchcandidate/dispSearchList/{page}"
            logging.info(f"Processing page {page}: {list_url}")
            
            # Get page content
            try:
                response = self.session.get(list_url)
                html = response.text if hasattr(response, 'text') else str(response)
            except Exception as e:
                logging.error(f"Error fetching page {page}: {e}")
                break
                
            # Parse candidate list
            candidates = self.scraper.parse_candidate_list(html)
            if not candidates:
                logging.info("No more candidates found")
                break
                
            logging.info(f"Found {len(candidates)} candidates on page {page}")
            self.stats['candidates_found'] += len(candidates)
            self.stats['pages_processed'] += 1
            
            # Process each candidate
            for candidate_basic in candidates:
                candidate_info = self._process_candidate(candidate_basic)
                if candidate_info:
                    all_candidates.append(candidate_info)
                    
            # Check pagination
            pagination = self.scraper.extract_pagination_info(html)
            if not pagination['has_next'] or (config.max_pages > 0 and page >= config.max_pages):
                break
                
            # Add delay between pages
            time.sleep(config.page_delay)
            page += 1
            
        # Save consolidated results
        if all_candidates:
            logging.info(f"Saving consolidated results for {len(all_candidates)} candidates")
            self.metadata_saver.save_consolidated_results(all_candidates)
            
        # Generate report
        download_stats = self.downloader.get_statistics()
        self.metadata_saver.generate_download_report(download_stats)
        
        return True
        
    def _process_specific_candidate(self, candidate_id: str) -> bool:
        """Process a specific candidate by ID"""
        # Construct detail URL for HRcap ERP system
        detail_url = f"{config.erp_base_url}/candidate/dispView/{candidate_id}?kw="
        
        candidate_basic = {
            'candidate_id': candidate_id,
            'detail_url': detail_url
        }
        
        candidate_info = self._process_candidate(candidate_basic)
        if candidate_info:
            # Save individual result
            self.metadata_saver.save_consolidated_results([candidate_info])
            return True
            
        return False
        
    def _process_candidate(self, candidate_basic: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process individual candidate
        
        Args:
            candidate_basic: Basic candidate info from list page
            
        Returns:
            Complete candidate information or None
        """
        candidate_id = candidate_basic.get('candidate_id')
        detail_url = candidate_basic.get('detail_url')
        
        if not candidate_id or not detail_url:
            logging.warning("Missing candidate ID or detail URL")
            return None
            
        try:
            # Add delay to prevent server overload
            time.sleep(config.request_delay)
            
            # Get detail page
            logging.info(f"Processing candidate {candidate_id}")
            response = self.session.get(detail_url)
            html = response.text if hasattr(response, 'text') else str(response)
            
            # Parse complete candidate info
            candidate_info = self.scraper.parse_candidate_detail(html, candidate_id)
            
            # Download resume if URL available
            pdf_path = None
            if candidate_info.resume_url:
                pdf_path = self._download_candidate_resume(candidate_info)
            else:
                logging.warning(f"No resume URL found for candidate {candidate_id}")
                
            # Save metadata
            self.metadata_saver.save_candidate_metadata(
                candidate_info.to_dict(), 
                pdf_path
            )
            
            return candidate_info.to_dict()
            
        except Exception as e:
            logging.error(f"Error processing candidate {candidate_id}: {e}")
            return None
            
    def _download_candidate_resume(self, candidate_info: CandidateInfo) -> Optional[Path]:
        """Download resume for a candidate"""
        # Generate filename
        filename = generate_filename_from_template(
            template=config.file_name_pattern,
            name=candidate_info.name,
            candidate_id=candidate_info.candidate_id
        )
        
        # Determine directory based on created date
        year, month = extract_date_parts(candidate_info.created_date)
        resume_dir = create_directory_structure(config.resumes_dir, year, month)
        
        # Full path for PDF
        pdf_path = resume_dir / filename
        
        # Download
        success = self.downloader.download_resume(
            url=candidate_info.resume_url,
            save_path=pdf_path,
            candidate_info=candidate_info.to_dict()
        )
        
        return pdf_path if success else None
        
    def _print_summary(self):
        """Print harvest summary"""
        if not self.stats['start_time'] or not self.stats['end_time']:
            return
            
        duration = self.stats['end_time'] - self.stats['start_time']
        download_stats = self.downloader.get_statistics() if self.downloader else {}
        
        print("\n" + "=" * 60)
        print("HARVEST SUMMARY")
        print("=" * 60)
        print(f"Duration: {duration}")
        print(f"Pages processed: {self.stats['pages_processed']}")
        print(f"Candidates found: {self.stats['candidates_found']}")
        print(f"Successful downloads: {download_stats.get('successful', 0)}")
        print(f"Failed downloads: {download_stats.get('failed', 0)}")
        print(f"Skipped (existing): {download_stats.get('skipped', 0)}")
        print(f"Total size: {download_stats.get('total_size_mb', 0):.2f} MB")
        print(f"Success rate: {download_stats.get('success_rate', 0):.1f}%")
        print("=" * 60)
        
    def cleanup(self):
        """Cleanup resources"""
        if self.session:
            self.session.close()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='ERP Resume Harvester')
    parser.add_argument(
        '--selenium', 
        action='store_true',
        help='Use Selenium instead of requests'
    )
    parser.add_argument(
        '--page',
        type=int,
        default=1,
        help='Starting page number (default: 1)'
    )
    parser.add_argument(
        '--id',
        type=str,
        help='Process specific candidate ID'
    )
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    # Run harvester
    harvester = ERPResumeHarvester(use_selenium=args.selenium)
    success = harvester.harvest_candidates(
        start_page=args.page,
        specific_id=args.id
    )
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main() 