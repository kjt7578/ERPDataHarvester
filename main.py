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
from scraper import ERPScraper, CandidateInfo, JobCaseInfo
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
            self.scraper.session = self.session  # Pass session for additional page fetching
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
                          specific_id: Optional[str] = None,
                          id_range: Optional[str] = None) -> bool:
        """
        Harvest candidates from ERP system
        
        Args:
            start_page: Starting page number for full harvest
            specific_id: Process only this specific candidate ID
            id_range: Process range of IDs (format: "65585-65580" or "65580,65581,65582")
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.initialize():
                return False
                
            self.stats['start_time'] = datetime.now()
            
            if specific_id:
                logging.info(f"Processing specific candidate: {specific_id}")
                success = self._process_specific_candidate(specific_id) is not None
            elif id_range:
                logging.info(f"Processing ID range: {id_range}")
                success = self._process_id_range(id_range)
            else:
                logging.info("Starting full harvest process...")
                success = self._process_all_candidates(start_page)
                
            self.stats['end_time'] = datetime.now()
            self._print_summary()
            
            return success
            
        except KeyboardInterrupt:
            logging.info("Harvest interrupted by user")
            return False
        except Exception as e:
            logging.error(f"Error during harvest: {e}")
            return False
        finally:
            self.cleanup()
            
    def _process_all_candidates(self, start_page: int) -> bool:
        """Process all candidates from multiple pages"""
        all_candidates = []
        page = start_page
        
        # Try different possible list URLs for HRcap ERP
        list_url_patterns = [
            f"{config.erp_base_url}/searchcandidate/dispSearchList/{{page}}",
            f"{config.erp_base_url}/candidate/list/{{page}}",
            f"{config.erp_base_url}/case/dispList?page={{page}}",
            f"{config.erp_base_url}/member/list?page={{page}}",
        ]
        
        successful_pattern = None
        
        while True:
            candidates_found_this_page = False
            
            # Try each URL pattern if we haven't found a working one
            if not successful_pattern:
                for pattern in list_url_patterns:
                    list_url = pattern.format(page=page)
                    logging.info(f"Trying URL pattern: {list_url}")
                    
                    try:
                        response = self.session.get(list_url)
                        html = response.text if hasattr(response, 'text') else str(response)
                        
                        # Quick check if this looks like a candidate list page
                        if len(html) > 1000 and ('candidate' in html.lower() or 'table' in html.lower()):
                            candidates = self.scraper.parse_candidate_list(html)
                            if candidates:
                                logging.info(f"Found working URL pattern: {pattern}")
                                successful_pattern = pattern
                                candidates_found_this_page = True
                                break
                        else:
                            logging.debug(f"URL {list_url} doesn't look like candidate list (length: {len(html)})")
                            
                    except Exception as e:
                        logging.debug(f"Error with URL {list_url}: {e}")
                        continue
                        
                if not successful_pattern:
                    logging.error("No working URL pattern found for candidate list")
                    break
            else:
                # Use the successful pattern
                list_url = successful_pattern.format(page=page)
                logging.info(f"Processing page {page}: {list_url}")
                
                try:
                    response = self.session.get(list_url)
                    html = response.text if hasattr(response, 'text') else str(response)
                    
                    candidates = self.scraper.parse_candidate_list(html)
                    if candidates:
                        candidates_found_this_page = True
                    
                except Exception as e:
                    logging.error(f"Error fetching page {page}: {e}")
                    break
            
            # If no candidates found on this page, we're done
            if not candidates_found_this_page:
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
        
    def _process_specific_candidate(self, candidate_id: str, save_individual: bool = True) -> Optional[Dict[str, Any]]:
        """Process a specific candidate by ID"""
        # Construct detail URL for HRcap ERP system
        detail_url = f"{config.erp_base_url}/candidate/dispView/{candidate_id}?kw="
        
        candidate_basic = {
            'candidate_id': candidate_id,
            'detail_url': detail_url
        }
        
        candidate_info = self._process_candidate(candidate_basic)
        if candidate_info:
            # Save individual result only if requested
            if save_individual:
                self.metadata_saver.save_consolidated_results([candidate_info])
            return candidate_info
            
        return None
        
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

    def _process_id_range(self, id_range: str) -> bool:
        """
        Process a range of candidate IDs
        
        Args:
            id_range: Range specification like "65585-65580" or "65580,65581,65582"
            
        Returns:
            True if at least one candidate was processed successfully
        """
        candidate_ids = []
        
        # Parse different range formats
        if '-' in id_range:
            # Range format: "65585-65580" (from high to low)
            try:
                parts = id_range.split('-')
                if len(parts) == 2:
                    start_id = int(parts[0])
                    end_id = int(parts[1])
                    
                    # Ensure we go from high to low or low to high
                    if start_id > end_id:
                        candidate_ids = list(range(start_id, end_id - 1, -1))  # Descending
                    else:
                        candidate_ids = list(range(start_id, end_id + 1))  # Ascending
                else:
                    raise ValueError("Invalid range format")
            except ValueError:
                logging.error(f"Invalid range format: {id_range}. Use format like '65585-65580'")
                return False
                
        elif ',' in id_range:
            # Comma-separated format: "65580,65581,65582"
            try:
                candidate_ids = [int(id_str.strip()) for id_str in id_range.split(',')]
            except ValueError:
                logging.error(f"Invalid comma-separated format: {id_range}")
                return False
        else:
            logging.error(f"Invalid ID range format: {id_range}. Use '65585-65580' or '65580,65581,65582'")
            return False
            
        if not candidate_ids:
            logging.error("No candidate IDs generated from range")
            return False
            
        logging.info(f"Processing {len(candidate_ids)} candidates: {candidate_ids[0]} to {candidate_ids[-1]}")
        
        all_candidates = []
        successful_count = 0
        
        for i, candidate_id in enumerate(candidate_ids, 1):
            logging.info(f"Processing candidate {i}/{len(candidate_ids)}: {candidate_id}")
            
            candidate_info = self._process_specific_candidate(str(candidate_id), save_individual=False)
            if candidate_info:
                all_candidates.append(candidate_info)
                successful_count += 1
                logging.info(f"✅ Successfully processed {candidate_id}")
            else:
                logging.warning(f"❌ Failed to process {candidate_id}")
                
            # Add delay between requests to be respectful to server
            if i < len(candidate_ids):  # Don't delay after last item
                time.sleep(config.request_delay)
                
        # Save consolidated results
        if all_candidates:
            logging.info(f"Saving consolidated results for {len(all_candidates)} candidates")
            self.metadata_saver.save_consolidated_results(all_candidates)
            
        # Generate report
        download_stats = self.downloader.get_statistics()
        self.metadata_saver.generate_download_report(download_stats)
        
        logging.info(f"ID range processing complete: {successful_count}/{len(candidate_ids)} successful")
        return successful_count > 0

    def harvest_cases(self, start_page: int = 1, 
                     specific_id: Optional[str] = None,
                     id_range: Optional[str] = None) -> bool:
        """
        Harvest cases from ERP system
        
        Args:
            start_page: Starting page number for full harvest
            specific_id: Process only this specific case ID
            id_range: Process range of IDs (format: "3897-3895" or "3895,3896,3897")
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.initialize():
                return False
                
            self.stats['start_time'] = datetime.now()
            
            if specific_id:
                logging.info(f"Processing specific case: {specific_id}")
                success = self._process_specific_case(specific_id) is not None
            elif id_range:
                logging.info(f"Processing case ID range: {id_range}")
                success = self._process_case_id_range(id_range)
            else:
                logging.info("Starting full case harvest process...")
                success = self._process_all_cases(start_page)
                
            self.stats['end_time'] = datetime.now()
            self._print_summary()
            
            return success
            
        except KeyboardInterrupt:
            logging.info("Case harvest interrupted by user")
            return False
        except Exception as e:
            logging.error(f"Error during case harvest: {e}")
            return False
        finally:
            self.cleanup()

    def _process_all_cases(self, start_page: int) -> bool:
        """Process all cases from multiple pages"""
        all_cases = []
        page = start_page
        
        # Try case list URL
        while page <= config.max_pages:
            list_url = f"{config.erp_base_url}{config.case_list_url}".format(page=page)
            logging.info(f"Fetching case list from: {list_url}")
            
            try:
                response = self.session.get(list_url)
                html = response.text if hasattr(response, 'text') else str(response)
                
                # Parse cases from this page
                cases = self.scraper.parse_jobcase_list(html)
                if not cases:
                    logging.info(f"No cases found on page {page}")
                    break
                    
                logging.info(f"Found {len(cases)} cases on page {page}")
                self.stats['pages_processed'] += 1
                
                # Process each case
                for case in cases:
                    case_info = self._process_case(case)
                    if case_info:
                        all_cases.append(case_info)
                        self.stats['candidates_found'] += 1  # Reusing for cases
                        
                    time.sleep(config.request_delay)
                    
                page += 1
                time.sleep(config.page_delay)
                
            except Exception as e:
                logging.error(f"Error processing page {page}: {e}")
                break
                
        # Save consolidated results
        if all_cases:
            self.metadata_saver.save_consolidated_results(all_cases, data_type='case')
            
        return len(all_cases) > 0

    def _process_specific_case(self, case_id: str, save_individual: bool = True) -> Optional[Dict[str, Any]]:
        """Process a specific case by ID"""
        try:
            detail_url = f"{config.erp_base_url}{config.case_detail_url}".format(id=case_id)
            logging.info(f"Fetching case details from: {detail_url}")
            
            response = self.session.get(detail_url)
            html = response.text if hasattr(response, 'text') else str(response)
            
            # Parse case details
            case_info = self.scraper.parse_jobcase_detail(html, case_id)
            
            # Save metadata if requested
            if save_individual:
                # Save metadata (existing format in metadata folder)
                self.metadata_saver.save_case_metadata(case_info.to_dict())
                
                # Save detailed JD info (new format in case folder)
                self.metadata_saver.save_case_jd_info(case_info.to_dict())
                
            return case_info.to_dict()
            
        except Exception as e:
            logging.error(f"Error processing case {case_id}: {e}")
            return None

    def _process_case(self, case_basic: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a case with full details"""
        case_id = case_basic.get('jobcase_id')
        if not case_id:
            logging.warning("No case ID found in basic info")
            return None
            
        logging.info(f"Processing case: {case_id}")
        
        try:
            # Get full case details
            detail_url = case_basic.get('detail_url')
            if not detail_url:
                detail_url = f"{config.erp_base_url}{config.case_detail_url}".format(id=case_id)
                
            response = self.session.get(detail_url)
            html = response.text if hasattr(response, 'text') else str(response)
            
            # Parse detailed information
            case_info = self.scraper.parse_jobcase_detail(html, case_id)
            
            # Save metadata (existing format in metadata folder)
            self.metadata_saver.save_case_metadata(case_info.to_dict())
            
            # Save detailed JD info (new format in case folder)
            self.metadata_saver.save_case_jd_info(case_info.to_dict())
            
            return case_info.to_dict()
            
        except Exception as e:
            logging.error(f"Error processing case {case_id}: {e}")
            return None

    def _process_case_id_range(self, id_range: str) -> bool:
        """Process a range of case IDs"""
        case_ids = []
        
        # Parse different range formats (same logic as candidates)
        if '-' in id_range:
            try:
                parts = id_range.split('-')
                if len(parts) == 2:
                    start_id = int(parts[0])
                    end_id = int(parts[1])
                    
                    if start_id > end_id:
                        case_ids = list(range(start_id, end_id - 1, -1))
                    else:
                        case_ids = list(range(start_id, end_id + 1))
                else:
                    raise ValueError("Invalid range format")
            except ValueError:
                logging.error(f"Invalid range format: {id_range}")
                return False
                
        elif ',' in id_range:
            try:
                case_ids = [int(id_str.strip()) for id_str in id_range.split(',')]
            except ValueError:
                logging.error(f"Invalid comma-separated format: {id_range}")
                return False
        else:
            logging.error(f"Invalid ID range format: {id_range}")
            return False
            
        if not case_ids:
            logging.error("No case IDs generated from range")
            return False
            
        logging.info(f"Processing {len(case_ids)} cases: {case_ids[0]} to {case_ids[-1]}")
        
        all_cases = []
        successful_count = 0
        
        for i, case_id in enumerate(case_ids, 1):
            logging.info(f"Processing case {i}/{len(case_ids)}: {case_id}")
            
            case_info = self._process_specific_case(str(case_id), save_individual=False)
            if case_info:
                # Save individual metadata and JD info for each case in range
                self.metadata_saver.save_case_metadata(case_info)
                self.metadata_saver.save_case_jd_info(case_info)
                all_cases.append(case_info)
                successful_count += 1
                logging.info(f"✅ Successfully processed case {case_id}")
            else:
                logging.warning(f"❌ Failed to process case {case_id}")
                
            if i < len(case_ids):
                time.sleep(config.request_delay)
                
        # Save consolidated results
        if all_cases:
            logging.info(f"Saving consolidated case results for {len(all_cases)} cases")
            self.metadata_saver.save_consolidated_results(all_cases, data_type='case')
            
        logging.info(f"Case ID range processing complete: {successful_count}/{len(case_ids)} successful")
        return successful_count > 0


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='ERP Resume Harvester')
    parser.add_argument(
        '--type',
        choices=['candidate', 'case'],
        default='candidate',
        help='Type of data to harvest: candidate or case (default: candidate)'
    )
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
        help='Process specific candidate/case ID'
    )
    parser.add_argument(
        '--range',
        type=str,
        help='Process range of IDs (format: "65585-65580" or "65580,65581,65582")'
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
    
    # Run harvester based on type
    harvester = ERPResumeHarvester(use_selenium=args.selenium)
    
    if args.type == 'case':
        success = harvester.harvest_cases(
            start_page=args.page,
            specific_id=args.id,
            id_range=args.range
        )
    else:  # candidate (default)
        success = harvester.harvest_candidates(
            start_page=args.page,
            specific_id=args.id,
            id_range=args.range
        )
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main() 