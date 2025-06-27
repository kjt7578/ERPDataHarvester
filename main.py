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
    sanitize_filename, 
    generate_resume_filename,
    generate_case_filename,
    extract_date_parts,
    create_directory_structure,
    convert_candidate_id,
    convert_case_id,
    parse_id_range,
    parse_case_id_range,
    predict_real_candidate_id,
    predict_url_candidate_id,
    predict_real_case_id,
    predict_url_case_id
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
                          id_range: Optional[str] = None,
                          id_type: str = 'url') -> bool:
        """
        Harvest candidates from ERP system
        
        Args:
            start_page: Starting page number for full harvest
            specific_id: Process only this specific candidate ID
            id_range: Process range of IDs (format: "65585-65580" or "65580,65581,65582")
            id_type: Type of IDs ('url', 'real', or 'auto')
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.initialize():
                return False
                
            self.stats['start_time'] = datetime.now()
            start_time = self.stats['start_time'].strftime('%Y-%m-%d %H:%M:%S')
            
            if specific_id:
                # Convert ID if needed
                id_info = convert_candidate_id(specific_id, id_type)
                url_id = str(id_info['url_id'])
                real_id = str(id_info['real_id'])
                
                logging.info(f"Processing specific candidate: {specific_id} (ID type: {id_type})")
                logging.info(f"  URL ID: {url_id}, Real ID: {real_id}")
                
                self.metadata_saver.set_command_info('candidate', 'single_id', f"{specific_id} ({id_type})", start_time)
                success = self._process_specific_candidate(url_id) is not None
            elif id_range:
                logging.info(f"Processing candidate ID range: {id_range} (ID type: {id_type})")
                self.metadata_saver.set_command_info('candidate', 'id_range', f"{id_range} ({id_type})", start_time)
                success = self._process_id_range(id_range, id_type)
            else:
                logging.info("Starting full candidate harvest process...")
                self.metadata_saver.set_command_info('candidate', 'page_crawl', f'from page {start_page}', start_time)
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
        candidate_name = candidate_basic.get('name', 'Unknown')
        
        if not candidate_id or not detail_url:
            self.metadata_saver.record_error(
                candidate_id or "Unknown", 
                candidate_name, 
                detail_url or "N/A",
                "MISSING_DATA", 
                "Missing candidate ID or detail URL from basic info"
            )
            logging.warning("Missing candidate ID or detail URL")
            return None
            
        try:
            # Add delay to prevent server overload
            time.sleep(config.request_delay)
            
            # Get detail page
            logging.info(f"Processing candidate {candidate_id}")
            
            try:
                response = self.session.get(detail_url)
                html = response.text if hasattr(response, 'text') else str(response)
            except Exception as e:
                self.metadata_saver.record_error(
                    candidate_id, candidate_name, detail_url,
                    "CONNECTION_ERROR", 
                    f"Failed to fetch detail page: {str(e)}"
                )
                raise
            
            # Get raw HTML without JavaScript for accurate date extraction
            try:
                raw_response = self.session.get_raw_html(detail_url)
                raw_html = raw_response.text if hasattr(raw_response, 'text') else str(raw_response)
            except Exception as e:
                self.metadata_saver.record_warning(
                    candidate_id, candidate_name, detail_url,
                    "RAW_HTML_FAILED", 
                    f"Failed to get raw HTML, using rendered HTML only: {str(e)}"
                )
                raw_html = None
            
            # Parse complete candidate info with both HTML versions
            try:
                candidate_info = self.scraper.parse_candidate_detail(html, candidate_id, raw_html, detail_url)
                
                # Update candidate name if we got it from parsing
                if candidate_info.name and candidate_info.name != 'Unknown':
                    candidate_name = candidate_info.name
                    
            except Exception as e:
                self.metadata_saver.record_error(
                    candidate_id, candidate_name, detail_url,
                    "PARSE_ERROR", 
                    f"Failed to parse candidate detail page: {str(e)}"
                )
                raise
            
            # Check for missing critical data and record warnings
            if not candidate_info.name or candidate_info.name == 'Unknown':
                self.metadata_saver.record_warning(
                    candidate_id, candidate_name, detail_url,
                    "MISSING_NAME", 
                    "Candidate name could not be extracted"
                )
                
            if not candidate_info.created_date:
                self.metadata_saver.record_warning(
                    candidate_id, candidate_name, detail_url,
                    "MISSING_CREATED_DATE", 
                    "Created date could not be extracted"
                )
                
            if not candidate_info.resume_url:
                self.metadata_saver.record_warning(
                    candidate_id, candidate_name, detail_url,
                    "NO_RESUME_URL", 
                    "No resume download URL found"
                )
            
            # Download resume if URL available
            pdf_path = None
            if candidate_info.resume_url:
                try:
                    pdf_path = self._download_candidate_resume(candidate_info)
                    if not pdf_path:
                        self.metadata_saver.record_error(
                            candidate_id, candidate_name, detail_url,
                            "DOWNLOAD_FAILED", 
                            "Resume download failed - check downloader logs for details"
                        )
                except Exception as e:
                    self.metadata_saver.record_error(
                        candidate_id, candidate_name, detail_url,
                        "DOWNLOAD_ERROR", 
                        f"Resume download error: {str(e)}"
                    )
            else:
                logging.warning(f"No resume URL found for candidate {candidate_id}")
                
            # Save metadata
            try:
                self.metadata_saver.save_candidate_metadata(
                    candidate_info.to_dict(), 
                    pdf_path
                )
            except Exception as e:
                self.metadata_saver.record_error(
                    candidate_id, candidate_name, detail_url,
                    "METADATA_SAVE_ERROR", 
                    f"Failed to save candidate metadata: {str(e)}"
                )
                # Don't raise here - we still want to return the candidate info
                logging.error(f"Failed to save metadata for {candidate_id}: {e}")
            
            return candidate_info.to_dict()
            
        except Exception as e:
            logging.error(f"Error processing candidate {candidate_id}: {e}")
            # If we haven't already recorded this error, record it as a general processing error
            if not any(error['candidate_id'] == candidate_id and 'processing candidate' in error['error_message'].lower() 
                      for error in self.metadata_saver.processing_errors):
                self.metadata_saver.record_error(
                    candidate_id, candidate_name, detail_url,
                    "PROCESSING_ERROR", 
                    f"General processing error: {str(e)}"
                )
            return None
            
    def _download_candidate_resume(self, candidate_info: CandidateInfo) -> Optional[Path]:
        """Download resume for a candidate"""
        # Generate filename using new bracket format
        filename = generate_resume_filename(
            name=candidate_info.name,
            candidate_id=candidate_info.candidate_id,
            extension='pdf'
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

    def _process_id_range(self, id_range: str, id_type: str = 'url') -> bool:
        """
        Process a range of candidate IDs with support for both URL and Real IDs
        
        Args:
            id_range: Range specification like "65585-65580" or "1044759-1044754"
            id_type: Type of IDs ('url', 'real', or 'auto')
            
        Returns:
            True if at least one candidate was processed successfully
        """
        try:
            # Parse the range and convert to URL IDs (for ERP access)
            candidate_url_ids = parse_id_range(id_range, id_type)
            
            if not candidate_url_ids:
                logging.error("No candidate IDs generated from range")
                return False
                
            # Log conversion information
            if id_type == 'real':
                logging.info(f"Converted real ID range to URL IDs: {candidate_url_ids[0]} to {candidate_url_ids[-1]}")
            elif id_type == 'auto':
                # Show both for auto-detected
                sample_id = candidate_url_ids[0]
                real_id = predict_real_candidate_id(sample_id)
                logging.info(f"Auto-detected as {id_type} IDs. URL: {sample_id}, Real: {real_id}")
                
            logging.info(f"Processing {len(candidate_url_ids)} candidates: {candidate_url_ids[0]} to {candidate_url_ids[-1]}")
            
            all_candidates = []
            successful_count = 0
            
            for i, candidate_url_id in enumerate(candidate_url_ids, 1):
                logging.info(f"Processing candidate {i}/{len(candidate_url_ids)}: URL ID {candidate_url_id}")
                
                candidate_info = self._process_specific_candidate(str(candidate_url_id), save_individual=False)
                if candidate_info:
                    all_candidates.append(candidate_info)
                    successful_count += 1
                    
                    # Show both IDs in success message
                    real_id = candidate_info.get('candidate_id', 'Unknown')
                    name = candidate_info.get('name', 'Unknown')
                    logging.info(f"✅ Successfully processed: URL {candidate_url_id} → Real {real_id} ({name})")
                else:
                    predicted_real_id = predict_real_candidate_id(candidate_url_id)
                    logging.warning(f"❌ Failed to process: URL {candidate_url_id} (predicted Real {predicted_real_id})")
                    
                # Add delay between requests to be respectful to server
                if i < len(candidate_url_ids):  # Don't delay after last item
                    time.sleep(config.request_delay)
                    
            # Save consolidated results
            if all_candidates:
                logging.info(f"Saving consolidated results for {len(all_candidates)} candidates")
                self.metadata_saver.save_consolidated_results(all_candidates)
                
            # Generate report
            download_stats = self.downloader.get_statistics()
            self.metadata_saver.generate_download_report(download_stats)
            
            logging.info(f"ID range processing complete: {successful_count}/{len(candidate_url_ids)} successful")
            return successful_count > 0
            
        except ValueError as e:
            logging.error(f"Invalid ID range: {e}")
            return False
        except Exception as e:
            logging.error(f"Error processing ID range: {e}")
            return False

    def harvest_cases(self, start_page: int = 1, 
                     specific_id: Optional[str] = None,
                     id_range: Optional[str] = None,
                     id_type: str = 'url') -> bool:
        """
        Harvest cases from ERP system
        
        Args:
            start_page: Starting page number for full harvest
            specific_id: Process only this specific case ID
            id_range: Process range of IDs (format: "3897-3895" or "3895,3896,3897")
            id_type: Type of IDs ('url', 'real', or 'auto') - currently cases use same ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.initialize():
                return False
                
            self.stats['start_time'] = datetime.now()
            start_time = self.stats['start_time'].strftime('%Y-%m-%d %H:%M:%S')
            
            if specific_id:
                # For cases, currently URL and Real IDs are handled the same
                id_info = convert_case_id(specific_id, id_type)
                url_id = id_info['url_id']
                
                logging.info(f"Processing specific case: {specific_id} (ID type: {id_type})")
                logging.info(f"  Using ID: {url_id}")
                
                self.metadata_saver.set_command_info('case', 'single_id', f"{specific_id} ({id_type})", start_time)
                success = self._process_specific_case(url_id) is not None
            elif id_range:
                logging.info(f"Processing case ID range: {id_range} (ID type: {id_type})")
                self.metadata_saver.set_command_info('case', 'id_range', f"{id_range} ({id_type})", start_time)
                success = self._process_case_id_range(id_range, id_type)
                # _process_case_id_range already generates its own report, so we skip the duplicate report generation
                return success
            else:
                logging.info("Starting full case harvest process...")
                self.metadata_saver.set_command_info('case', 'page_crawl', f'from page {start_page}', start_time)
                success = self._process_all_cases(start_page)
                
            self.stats['end_time'] = datetime.now()
            self._print_summary()
            
            # Generate report (case에는 다운로드가 없으므로 빈 stats 사용)
            download_stats = {
                'total': self.stats.get('candidates_found', 0),  # Reusing for cases
                'successful': self.stats.get('candidates_found', 0),
                'failed': 0,
                'skipped': 0,
                'success_rate': 100.0 if self.stats.get('candidates_found', 0) > 0 else 0.0,
                'total_size_mb': 0.0,
                'successful_candidates': [],
                'failed_candidates': [],
                'skipped_candidates': []
            }
            self.metadata_saver.generate_download_report(download_stats)
            
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
            
        # Generate report for case processing
        download_stats = {
            'total': len(all_cases),
            'successful': len(all_cases),
            'failed': 0,
            'skipped': 0,
            'success_rate': 100.0 if len(all_cases) > 0 else 0.0,
            'total_size_mb': 0.0,
            'successful_candidates': [],
            'failed_candidates': [],
            'skipped_candidates': []
        }
        self.metadata_saver.generate_download_report(download_stats)
            
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

    def _process_case_id_range(self, id_range: str, id_type: str = 'url') -> bool:
        """
        Process a range of case IDs with support for both URL and Real IDs
        
        Args:
            id_range: Range specification like "3897-3890" or "13897-13890"
            id_type: Type of IDs ('url', 'real', or 'auto') 
            
        Returns:
            True if at least one case was processed successfully
        """
        try:
            # Parse the range and convert to URL IDs (for ERP access)
            case_url_ids = parse_case_id_range(id_range, id_type)
            
            if not case_url_ids:
                logging.error("No case IDs generated from range")
                return False
                
            # Log conversion information
            if id_type == 'real':
                logging.info(f"Converted real Case ID range to URL IDs: {case_url_ids[0]} to {case_url_ids[-1]}")
            elif id_type == 'auto':
                # Show both for auto-detected
                sample_id = case_url_ids[0]
                real_id = predict_real_case_id(sample_id)
                logging.info(f"Auto-detected as {id_type} IDs. URL: {sample_id}, Real: {real_id}")
                
            logging.info(f"Processing {len(case_url_ids)} cases: {case_url_ids[0]} to {case_url_ids[-1]} (ID type: {id_type})")
            
            all_cases = []
            successful_count = 0
            
            for i, case_url_id in enumerate(case_url_ids, 1):
                logging.info(f"Processing case {i}/{len(case_url_ids)}: URL ID {case_url_id}")
                
                case_info = self._process_specific_case(str(case_url_id), save_individual=False)
                if case_info:
                    all_cases.append(case_info)
                    successful_count += 1
                    
                    company = case_info.get('company_name', 'Unknown Company')
                    title = case_info.get('job_title', 'Unknown Position')
                    actual_id = case_info.get('jobcase_id', case_url_id)
                    predicted_real_id = predict_real_case_id(case_url_id)
                    logging.info(f"✅ Successfully processed: URL {case_url_id} → Real {actual_id} (예상: {predicted_real_id}) ({company} - {title})")
                else:
                    predicted_real_id = predict_real_case_id(case_url_id)
                    logging.warning(f"❌ Failed to process: URL {case_url_id} (predicted Real {predicted_real_id})")
                    
                # Add delay between requests to be respectful to server
                if i < len(case_url_ids):  # Don't delay after last item
                    time.sleep(config.request_delay)
                    
            # Save consolidated results
            if all_cases:
                logging.info(f"Saving consolidated results for {len(all_cases)} cases")
                self.metadata_saver.save_consolidated_results(all_cases, data_type='case')
                
            # Generate report
            download_stats = {
                'total': len(case_url_ids),
                'successful': successful_count,
                'failed': len(case_url_ids) - successful_count,
                'skipped': 0,
                'success_rate': (successful_count / len(case_url_ids)) * 100 if case_url_ids else 0.0,
                'total_size_mb': 0.0,
                'successful_candidates': all_cases,  # Reusing for cases
                'failed_candidates': [],
                'skipped_candidates': []
            }
            self.metadata_saver.generate_download_report(download_stats)
            
            logging.info(f"Case ID range processing complete: {successful_count}/{len(case_url_ids)} successful")
            return successful_count > 0
            
        except Exception as e:
            logging.error(f"Error processing case ID range: {e}")
            return False


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
        help='Process specific candidate/case by URL ID (traditional method)'
    )
    parser.add_argument(
        '--range',
        type=str,
        help='Process range of URL IDs (format: "65585-65580" or "3897-3890")'
    )
    parser.add_argument(
        '--real-id',
        type=str,
        help='Process specific candidate/case by Real ID (new method)'
    )
    parser.add_argument(
        '--real-range',
        type=str,
        help='Process range of Real IDs (format: "1044759-1044754" or "13897-13890")'
    )
    parser.add_argument(
        '--id-type',
        choices=['url', 'real', 'auto'],
        default='url',
        help='[DEPRECATED] Use --real-id or --real-range instead for Real IDs'
    )
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level'
    )
    parser.add_argument(
        '--analyze-case-pattern',
        action='store_true',
        help='Analyze Case ID patterns by collecting URL ID -> Real ID mappings'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    # Validate arguments
    id_options = [args.id, args.range, args.real_id, args.real_range]
    specified_options = [opt for opt in id_options if opt]
    
    if len(specified_options) > 1:
        print("Error: Only one of --id, --range, --real-id, --real-range can be specified")
        return False
    
    # Determine processing parameters
    specific_id = None
    id_range = None
    id_type = 'url'  # Default
    
    if args.real_id:
        specific_id = args.real_id
        id_type = 'real'
        print(f"🎯 Real ID Mode: Processing {args.type} with Real ID {args.real_id}")
    elif args.real_range:
        id_range = args.real_range
        id_type = 'real'
        print(f"📊 Real Range Mode: Processing {args.type} with Real ID range {args.real_range}")
    elif args.id:
        specific_id = args.id
        id_type = 'url'
        print(f"🔗 URL ID Mode: Processing {args.type} with URL ID {args.id}")
    elif args.range:
        id_range = args.range
        id_type = 'url'
        print(f"📈 URL Range Mode: Processing {args.type} with URL ID range {args.range}")
    else:
        # No specific ID/range specified, use existing id_type for backward compatibility
        id_type = args.id_type
        if id_type != 'url':
            print("Warning: --id-type is deprecated. Use --real-id or --real-range for Real IDs")
    
    # Handle special modes
    if args.analyze_case_pattern:
        if args.type != 'case':
            print("Error: --analyze-case-pattern can only be used with --type case")
            return False
        if not id_range and not specific_id:
            print("Error: --analyze-case-pattern requires --range, --real-range, --id, or --real-id")
            return False
        print("🔍 Case ID Pattern Analysis Mode")
        print("  Collecting URL ID → Real Case ID mappings...")
        print("  Look for 'CASE ID MAPPING:' lines in the output")
        print("-" * 50)
    
    # Create harvester and run appropriate method
    harvester = ERPResumeHarvester(use_selenium=True)
    
    if args.type == 'case':
        success = harvester.harvest_cases(
            start_page=args.page,
            specific_id=specific_id,
            id_range=id_range,
            id_type=id_type
        )
    else:  # candidate (default)
        success = harvester.harvest_candidates(
            start_page=args.page,
            specific_id=specific_id,
            id_range=id_range,
            id_type=id_type
        )
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main() 