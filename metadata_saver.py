"""
Metadata saving module for storing candidate information in JSON and CSV formats
"""
import json
import csv
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd

from config import config

logger = logging.getLogger(__name__)


class MetadataSaver:
    """Handles saving candidate metadata in various formats"""
    
    def __init__(self, metadata_dir: Path, results_dir: Path):
        """
        Initialize metadata saver
        
        Args:
            metadata_dir: Directory for metadata files
            results_dir: Directory for consolidated results
        """
        self.metadata_dir = Path(metadata_dir)
        self.results_dir = Path(results_dir)
        self.case_dir = Path("case")  # New case directory
        
        # Create metadata subdirectories
        self.metadata_case_dir = self.metadata_dir / "case"
        self.metadata_resume_dir = self.metadata_dir / "resume"
        
        # Create directories
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.case_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_case_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_resume_dir.mkdir(parents=True, exist_ok=True)
        
        # Define file paths
        self.candidates_json_path = self.results_dir / "candidates.json"
        self.candidates_csv_path = self.results_dir / "candidates.csv"
        self.cases_json_path = self.results_dir / "cases.json"
        self.cases_csv_path = self.results_dir / "cases.csv"
        
        # Initialize error tracking
        self.processing_errors = []
        self.warnings = []
        
        # Initialize command info
        self.command_info = {
            'data_type': None,
            'execution_mode': None,
            'target_range': None,
            'start_time': None,
            'end_time': None
        }
        
    def record_error(self, candidate_id: str, name: str, detail_url: str, error_type: str, error_message: str):
        """
        Record a processing error for later reporting
        
        Args:
            candidate_id: Candidate ID
            name: Candidate name
            detail_url: Detail page URL
            error_type: Type of error (e.g., 'DOWNLOAD_FAILED', 'PARSE_ERROR', 'CONNECTION_ERROR')
            error_message: Detailed error message
        """
        error_record = {
            'candidate_id': candidate_id,
            'name': name,
            'detail_url': detail_url,
            'error_type': error_type,
            'error_message': error_message,
            'timestamp': datetime.now().isoformat()
        }
        self.processing_errors.append(error_record)
        logger.error(f"Recorded error for {name} ({candidate_id}): {error_type} - {error_message}")
        
    def record_warning(self, candidate_id: str, name: str, detail_url: str, warning_type: str, warning_message: str):
        """
        Record a processing warning for later reporting
        
        Args:
            candidate_id: Candidate ID
            name: Candidate name
            detail_url: Detail page URL
            warning_type: Type of warning (e.g., 'MISSING_DATA', 'DATE_EXTRACTION_FAILED', 'NO_RESUME_URL')
            warning_message: Detailed warning message
        """
        warning_record = {
            'candidate_id': candidate_id,
            'name': name,
            'detail_url': detail_url,
            'warning_type': warning_type,
            'warning_message': warning_message,
            'timestamp': datetime.now().isoformat()
        }
        self.warnings.append(warning_record)
        logger.warning(f"Recorded warning for {name} ({candidate_id}): {warning_type} - {warning_message}")
        
    def set_command_info(self, data_type: str, execution_mode: str, target_range: str = None, start_time: str = None):
        """
        Set command execution information for report
        
        Args:
            data_type: 'candidate' or 'case'
            execution_mode: 'single_id', 'id_range', 'page_crawl', etc.
            target_range: Target ID(s) or page range
            start_time: Execution start time
        """
        self.command_info.update({
            'data_type': data_type,
            'execution_mode': execution_mode,
            'target_range': target_range,
            'start_time': start_time,
            'end_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        logger.info(f"Command info set: {data_type} {execution_mode} {target_range}")
        
    def save_candidate_metadata(self, candidate_info: Dict[str, Any], 
                               pdf_path: Optional[Path] = None) -> bool:
        """
        Save individual candidate metadata to JSON file
        
        Args:
            candidate_info: Candidate information dictionary
            pdf_path: Path to downloaded PDF file
            
        Returns:
            True if successful
        """
        try:
            # Generate metadata filename
            candidate_id = candidate_info.get('candidate_id', 'unknown')
            name = candidate_info.get('name', 'unknown')
            
            # Use same naming pattern as PDF
            filename = config.file_name_pattern.format(
                name=self._sanitize_name(name),
                id=candidate_id
            )
            metadata_filename = f"{filename}.meta.json"
            metadata_path = self.metadata_resume_dir / metadata_filename
            
            # Prepare metadata
            metadata = {
                'candidate_id': candidate_id,
                'name': name,
                'created_date': candidate_info.get('created_date'),
                'updated_date': candidate_info.get('updated_date'),
                'email': candidate_info.get('email'),
                'phone': candidate_info.get('phone'),
                'status': candidate_info.get('status'),
                'position': candidate_info.get('position'),
                'resume_url': candidate_info.get('resume_url'),
                'detail_url': candidate_info.get('detail_url'),
                'pdf_downloaded': pdf_path is not None and pdf_path.exists(),
                'pdf_path': str(pdf_path) if pdf_path else None,
                'pdf_size_mb': self._get_file_size_mb(pdf_path) if pdf_path else None,
                'metadata_created': datetime.now().isoformat(),
                'scrape_timestamp': datetime.now().isoformat()
            }
            
            # Save to JSON file
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
                
            logger.debug(f"Saved metadata for {name} ({candidate_id})")
            return True
            
        except Exception as e:
            logger.error(f"Error saving metadata for candidate {candidate_id}: {e}")
            return False
            
    def save_case_metadata(self, case_info: Dict[str, Any]) -> bool:
        """
        Save individual case metadata to JSON file
        
        Args:
            case_info: Case information dictionary
            
        Returns:
            True if successful
        """
        try:
            # Generate metadata filename
            case_id = case_info.get('jobcase_id', 'unknown')
            job_title = case_info.get('job_title', 'unknown')
            company_name = case_info.get('company_name', 'unknown')
            
            # Use new naming pattern to match JD files: clientName_PositionTitle_caseID.case.meta.json
            sanitized_company = self._sanitize_name(company_name)
            sanitized_title = self._sanitize_name(job_title)
            filename = f"{sanitized_company}_{sanitized_title}_{case_id}"
            metadata_filename = f"{filename}.case.meta.json"
            metadata_path = self.metadata_case_dir / metadata_filename
            
            # Prepare metadata
            metadata = {
                'jobcase_id': case_id,
                'job_title': job_title,
                'company_name': company_name,
                'created_date': case_info.get('created_date'),
                'updated_date': case_info.get('updated_date'),
                'job_status': case_info.get('job_status'),
                'assigned_team': case_info.get('assigned_team'),
                'drafter': case_info.get('drafter'),
                'client_id': case_info.get('client_id'),
                'candidate_ids': case_info.get('candidate_ids', []),
                'detail_url': case_info.get('detail_url'),
                'location': case_info.get('location'),
                'salary_range': case_info.get('salary_range'),
                'employment_type': case_info.get('employment_type'),
                'total_connected_candidates': len(case_info.get('candidate_ids', [])),
                'metadata_created': datetime.now().isoformat(),
                'scrape_timestamp': datetime.now().isoformat()
            }
            
            # Save to JSON file
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
                
            logger.debug(f"Saved case metadata for {job_title} ({case_id})")
            return True
            
        except Exception as e:
            logger.error(f"Error saving case metadata for {case_id}: {e}")
            return False
            
    def save_case_jd_info(self, case_info: Dict[str, Any]) -> bool:
        """
        Save detailed case JD information to case folder with new naming pattern
        
        Args:
            case_info: Complete case information dictionary with JD details
            
        Returns:
            True if successful
        """
        try:
            # Extract info for filename
            case_id = case_info.get('jobcase_id', 'unknown')
            job_title = case_info.get('job_title', 'unknown')
            company_name = case_info.get('company_name', 'unknown')
            
            # Create filename: clientName_PositionTitle_caseID.json
            sanitized_company = self._sanitize_name(company_name)
            sanitized_title = self._sanitize_name(job_title)
            filename = f"{sanitized_company}_{sanitized_title}_{case_id}.json"
            case_path = self.case_dir / filename
            
            # Prepare complete JD data
            jd_data = {
                # Basic Information
                'case_id': case_id,
                'position_title': job_title,
                'client_name': company_name,
                'case_status': case_info.get('job_status'),
                'created_date': case_info.get('created_date'),
                'updated_date': case_info.get('updated_date'),
                'assigned_team': case_info.get('assigned_team'),
                'drafter': case_info.get('drafter'),
                'client_id': case_info.get('client_id'),
                'connected_candidates': case_info.get('candidate_ids', []),
                'total_candidates': len(case_info.get('candidate_ids', [])),
                
                # Contract Information
                'contract_info': {
                    'contract_type': case_info.get('contract_type'),
                    'fee_type': case_info.get('fee_type'),
                    'bonus_types': case_info.get('bonus_types'),
                    'fee_rate': case_info.get('fee_rate'),
                    'guarantee_days': case_info.get('guarantee_days'),
                    'candidate_ownership_period': case_info.get('candidate_ownership_period'),
                    'payment_due_days': case_info.get('payment_due_days'),
                    'contract_expiration_date': case_info.get('contract_expiration_date'),
                    'signer_name': case_info.get('signer_name'),
                    'signer_position_level': case_info.get('signer_position_level'),
                    'signed_date': case_info.get('signed_date')
                },
                
                # Position Information
                'position_info': {
                    'job_category': case_info.get('job_category'),
                    'position_level': case_info.get('position_level'),
                    'employment_type': case_info.get('employment_type'),
                    'salary_range': case_info.get('salary_range'),
                    'job_location': case_info.get('job_location'),
                    'business_trip_frequency': case_info.get('business_trip_frequency'),
                    'targeted_due_date': case_info.get('targeted_due_date'),
                    'responsibilities': case_info.get('responsibilities'),
                    'responsibilities_input_tag': case_info.get('responsibilities_input_tag'),
                    'responsibilities_file_attach': case_info.get('responsibilities_file_attach')
                },
                
                # Job Order Information
                'job_order_info': {
                    'reason_of_hiring': case_info.get('reason_of_hiring'),
                    'job_order_inquirer': case_info.get('job_order_inquirer'),
                    'job_order_background': case_info.get('job_order_background'),
                    'desire_spec': case_info.get('desire_spec'),
                    'strategy_approach': case_info.get('strategy_approach'),
                    'important_notes': case_info.get('important_notes'),
                    'additional_client_info': case_info.get('additional_client_info'),
                    'other_info': case_info.get('other_info')
                },
                
                # Requirements Information
                'requirements_info': {
                    'education_level': case_info.get('education_level'),
                    'major': case_info.get('major'),
                    'language_ability': case_info.get('language_ability'),
                    'select_languages': case_info.get('select_languages', {}),
                    'experience_range': case_info.get('experience_range'),
                    'relocation_supported': case_info.get('relocation_supported')
                },
                
                # Benefits Information
                'benefits_info': {
                    'insurance_info': case_info.get('insurance_info'),
                    'k401_info': case_info.get('k401_info'),
                    'overtime_pay': case_info.get('overtime_pay'),
                    'personal_sick_days': case_info.get('personal_sick_days'),
                    'vacation_info': case_info.get('vacation_info', {}),
                    'other_benefits': case_info.get('other_benefits'),
                    'benefits_file': case_info.get('benefits_file')
                },
                
                # Metadata
                'metadata': {
                    'detail_url': case_info.get('detail_url'),
                    'url_id': case_info.get('url_id'),
                    'scraped_timestamp': datetime.now().isoformat(),
                    'file_created': datetime.now().isoformat()
                }
            }
            
            # Save to JSON file in case folder
            with open(case_path, 'w', encoding='utf-8') as f:
                json.dump(jd_data, f, ensure_ascii=False, indent=2)
                
            logger.info(f"Saved case JD info to {case_path}")
            logger.debug(f"Case JD file: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving case JD info for {case_id}: {e}")
            return False
            
    def save_consolidated_results(self, all_data: List[Dict[str, Any]], 
                                data_type: str = 'candidate') -> bool:
        """
        Save all data to consolidated JSON and CSV files
        
        Args:
            all_data: List of all information (candidate or case)
            data_type: Type of data being saved ('candidate' or 'case')
            
        Returns:
            True if successful
        """
        try:
            if data_type == 'case':
                # Handle case data
                summary = {
                    'total_cases': len(all_data),
                    'last_updated': datetime.now().isoformat(),
                    'cases': all_data
                }
                
                # Save to JSON
                with open(self.cases_json_path, 'w', encoding='utf-8') as f:
                    json.dump(summary, f, ensure_ascii=False, indent=2)
                    
                logger.info(f"Saved {len(all_data)} cases to {self.cases_json_path}")
                
                # Save to CSV
                if all_data:
                    self._save_cases_to_csv(all_data)
            else:
                # Handle candidate data (default)
                summary = {
                    'total_candidates': len(all_data),
                    'last_updated': datetime.now().isoformat(),
                    'candidates': all_data
                }
                
                # Save to JSON
                with open(self.candidates_json_path, 'w', encoding='utf-8') as f:
                    json.dump(summary, f, ensure_ascii=False, indent=2)
                    
                logger.info(f"Saved {len(all_data)} candidates to {self.candidates_json_path}")
                
                # Save to CSV
                if all_data:
                    self._save_to_csv(all_data)
                
            return True
            
        except Exception as e:
            logger.error(f"Error saving consolidated {data_type} results: {e}")
            return False

    def _save_cases_to_csv(self, cases: List[Dict[str, Any]]):
        """Save cases to CSV file"""
        try:
            # Use pandas for better CSV handling
            df = pd.DataFrame(cases)
            
            # Reorder columns for better readability
            column_order = [
                'jobcase_id', 'job_title', 'company_name', 'job_status',
                'assigned_team', 'drafter', 'client_id', 'total_connected_candidates',
                'created_date', 'updated_date', 'location', 'salary_range',
                'employment_type', 'detail_url'
            ]
            
            # Only include columns that exist
            columns = [col for col in column_order if col in df.columns]
            df = df[columns]
            
            # Convert candidate_ids list to comma-separated string for CSV
            if 'candidate_ids' in df.columns:
                df['candidate_ids'] = df['candidate_ids'].apply(
                    lambda x: ','.join(map(str, x)) if isinstance(x, list) else str(x)
                )
            
            # Save to CSV
            df.to_csv(self.cases_csv_path, index=False, encoding='utf-8-sig')
            logger.info(f"Saved cases to {self.cases_csv_path}")
            
        except ImportError:
            # Fallback if pandas not available
            self._save_cases_to_csv_basic(cases)
        except Exception as e:
            logger.error(f"Error saving cases to CSV: {e}")
            
    def _save_cases_to_csv_basic(self, cases: List[Dict[str, Any]]):
        """Basic CSV save for cases without pandas"""
        if not cases:
            return
            
        # Get all unique fields
        fieldnames = set()
        for case in cases:
            fieldnames.update(case.keys())
            
        # Define preferred order for cases
        field_order = [
            'jobcase_id', 'job_title', 'company_name', 'job_status',
            'assigned_team', 'drafter', 'client_id', 'created_date', 'updated_date'
        ]
        
        # Sort fields with preferred order first
        ordered_fields = []
        for field in field_order:
            if field in fieldnames:
                ordered_fields.append(field)
                
        # Add remaining fields
        for field in sorted(fieldnames):
            if field not in ordered_fields:
                ordered_fields.append(field)
                
        # Prepare data for CSV (convert lists to strings)
        csv_data = []
        for case in cases:
            row = {}
            for field in ordered_fields:
                value = case.get(field, '')
                if isinstance(value, list):
                    row[field] = ','.join(map(str, value))
                else:
                    row[field] = value
            csv_data.append(row)
                
        # Write CSV
        with open(self.cases_csv_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=ordered_fields)
            writer.writeheader()
            writer.writerows(csv_data)
            
    def _save_to_csv(self, candidates: List[Dict[str, Any]]):
        """Save candidates to CSV file"""
        try:
            # Use pandas for better CSV handling
            df = pd.DataFrame(candidates)
            
            # Reorder columns for better readability
            column_order = [
                'candidate_id', 'name', 'email', 'phone', 
                'position', 'status', 'created_date', 'updated_date',
                'pdf_downloaded', 'pdf_size_mb', 'resume_url', 'detail_url'
            ]
            
            # Only include columns that exist
            columns = [col for col in column_order if col in df.columns]
            df = df[columns]
            
            # Save to CSV
            df.to_csv(self.candidates_csv_path, index=False, encoding='utf-8-sig')
            logger.info(f"Saved candidates to {self.candidates_csv_path}")
            
        except ImportError:
            # Fallback if pandas not available
            self._save_to_csv_basic(candidates)
        except Exception as e:
            logger.error(f"Error saving to CSV: {e}")
            
    def _save_to_csv_basic(self, candidates: List[Dict[str, Any]]):
        """Basic CSV save without pandas"""
        if not candidates:
            return
            
        # Get all unique fields
        fieldnames = set()
        for candidate in candidates:
            fieldnames.update(candidate.keys())
            
        # Define preferred order
        field_order = [
            'candidate_id', 'name', 'email', 'phone', 
            'position', 'status', 'created_date', 'updated_date'
        ]
        
        # Sort fields with preferred order first
        ordered_fields = []
        for field in field_order:
            if field in fieldnames:
                ordered_fields.append(field)
                
        # Add remaining fields
        for field in sorted(fieldnames):
            if field not in ordered_fields:
                ordered_fields.append(field)
                
        # Write CSV
        with open(self.candidates_csv_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=ordered_fields)
            writer.writeheader()
            writer.writerows(candidates)
            
    def load_existing_metadata(self) -> Dict[str, Dict[str, Any]]:
        """
        Load all existing metadata files
        
        Returns:
            Dictionary mapping candidate_id to metadata
        """
        metadata_map = {}
        
        for json_file in self.metadata_dir.glob('*.meta.json'):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    candidate_id = data.get('candidate_id')
                    if candidate_id:
                        metadata_map[candidate_id] = data
            except Exception as e:
                logger.error(f"Error loading metadata from {json_file}: {e}")
                
        logger.info(f"Loaded {len(metadata_map)} existing metadata files")
        return metadata_map
        
    def update_metadata(self, candidate_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update existing metadata for a candidate
        
        Args:
            candidate_id: Candidate ID
            updates: Dictionary of fields to update
            
        Returns:
            True if successful
        """
        # Load existing metadata
        existing = self.load_existing_metadata()
        
        if candidate_id not in existing:
            logger.warning(f"No existing metadata found for candidate {candidate_id}")
            return False
            
        # Update fields
        metadata = existing[candidate_id]
        metadata.update(updates)
        metadata['last_updated'] = datetime.now().isoformat()
        
        # Save back
        return self.save_candidate_metadata(metadata)
        
    def generate_download_report(self, download_stats: Dict[str, Any]) -> Path:
        """
        Generate a comprehensive download and processing report
        
        Args:
            download_stats: Download statistics from PDFDownloader
            
        Returns:
            Path to report file
        """
        report_path = self.results_dir / f'processing_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
        
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write("ERP Resume Processing Report\n")
                f.write("=" * 60 + "\n\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                # Command Information Section
                f.write("📋 Command Information:\n")
                f.write("-" * 30 + "\n")
                f.write(f"Data Type: {self.command_info.get('data_type', 'N/A').upper()}\n")
                f.write(f"Execution Mode: {self.command_info.get('execution_mode', 'N/A')}\n")
                if self.command_info.get('target_range'):
                    f.write(f"Target Range: {self.command_info.get('target_range')}\n")
                if self.command_info.get('start_time'):
                    f.write(f"Started: {self.command_info.get('start_time')}\n")
                if self.command_info.get('end_time'):
                    f.write(f"Completed: {self.command_info.get('end_time')}\n")
                f.write("\n")
                
                # Processing Statistics Summary
                f.write("📊 Processing Statistics:\n")
                f.write("-" * 30 + "\n")
                f.write(f"Total candidates processed: {download_stats.get('total', 0)}\n")
                f.write(f"Successful downloads: {download_stats.get('successful', 0)}\n")
                f.write(f"Failed downloads: {download_stats.get('failed', 0)}\n")
                f.write(f"Skipped (existing): {download_stats.get('skipped', 0)}\n")
                f.write(f"Processing errors: {len(self.processing_errors)}\n")
                f.write(f"Warnings: {len(self.warnings)}\n")
                f.write(f"Success rate: {download_stats.get('success_rate', 0):.1f}%\n")
                f.write(f"Total size downloaded: {download_stats.get('total_size_mb', 0):.2f} MB\n\n")
                
                # Processing Errors Section
                if self.processing_errors:
                    f.write("🚨 PROCESSING ERRORS:\n")
                    f.write("=" * 50 + "\n")
                    for i, error in enumerate(self.processing_errors, 1):
                        f.write(f"{i:3d}. ERROR: {error['error_type']}\n")
                        f.write(f"     Candidate ID: {error['candidate_id']}\n")
                        f.write(f"     Name: {error['name']}\n")
                        f.write(f"     Detail URL: {error['detail_url']}\n")
                        f.write(f"     Error Message: {error['error_message']}\n")
                        f.write(f"     Timestamp: {error['timestamp']}\n")
                        f.write("-" * 50 + "\n")
                    f.write("\n")
                
                # Warnings Section
                if self.warnings:
                    f.write("⚠️  WARNINGS:\n")
                    f.write("=" * 50 + "\n")
                    for i, warning in enumerate(self.warnings, 1):
                        f.write(f"{i:3d}. WARNING: {warning['warning_type']}\n")
                        f.write(f"     Candidate ID: {warning['candidate_id']}\n")
                        f.write(f"     Name: {warning['name']}\n")
                        f.write(f"     Detail URL: {warning['detail_url']}\n")
                        f.write(f"     Warning Message: {warning['warning_message']}\n")
                        f.write(f"     Timestamp: {warning['timestamp']}\n")
                        f.write("-" * 50 + "\n")
                    f.write("\n")
                
                # Successfully Downloaded Candidates
                successful_list = download_stats.get('successful_candidates', [])
                if successful_list:
                    f.write("✅ Successfully Downloaded Candidates:\n")
                    f.write("-" * 40 + "\n")
                    for i, candidate in enumerate(successful_list, 1):
                        candidate_id = candidate.get('candidate_id', 'N/A')
                        name = candidate.get('name', 'Unknown')
                        size_mb = candidate.get('file_size_mb', 0)
                        f.write(f"{i:3d}. ID: {candidate_id} | {name} | {size_mb:.2f} MB\n")
                    f.write("\n")
                
                # Skipped Candidates
                skipped_list = download_stats.get('skipped_candidates', [])
                if skipped_list:
                    f.write("⏭️  Skipped Candidates (Already Downloaded):\n")
                    f.write("-" * 40 + "\n")
                    for i, candidate in enumerate(skipped_list, 1):
                        candidate_id = candidate.get('candidate_id', 'N/A')
                        name = candidate.get('name', 'Unknown')
                        f.write(f"{i:3d}. ID: {candidate_id} | {name}\n")
                    f.write("\n")
                
                # Failed Downloads from Downloader
                failed_list = download_stats.get('failed_candidates', [])
                if failed_list:
                    f.write("❌ Failed Downloads (Downloader Issues):\n")
                    f.write("-" * 45 + "\n")
                    for i, candidate in enumerate(failed_list, 1):
                        candidate_id = candidate.get('candidate_id', 'N/A')
                        name = candidate.get('name', 'Unknown')
                        error = candidate.get('error', 'Unknown error')
                        detail_url = candidate.get('detail_url', 'N/A')
                        f.write(f"{i:3d}. ID: {candidate_id} | {name}\n")
                        f.write(f"     URL: {detail_url}\n")
                        f.write(f"     Error: {error}\n")
                        f.write("-" * 45 + "\n")
                    f.write("\n")
                
                # Summary of All Processed IDs
                all_candidate_ids = []
                all_candidate_ids.extend([c.get('candidate_id') for c in successful_list if c.get('candidate_id')])
                all_candidate_ids.extend([c.get('candidate_id') for c in skipped_list if c.get('candidate_id')])
                all_candidate_ids.extend([c.get('candidate_id') for c in failed_list if c.get('candidate_id')])
                all_candidate_ids.extend([e.get('candidate_id') for e in self.processing_errors if e.get('candidate_id')])
                
                # Remove duplicates while preserving order
                unique_ids = []
                seen = set()
                for id in all_candidate_ids:
                    if id and id not in seen:
                        unique_ids.append(id)
                        seen.add(id)
                
                if unique_ids:
                    f.write(f"📋 All Processed Candidate IDs ({len(unique_ids)} total):\n")
                    f.write("-" * 40 + "\n")
                    # Sort IDs numerically if possible
                    try:
                        sorted_ids = sorted(unique_ids, key=lambda x: int(x) if x.isdigit() else float('inf'))
                    except:
                        sorted_ids = sorted(unique_ids)
                    
                    # Print IDs in rows of 10
                    for i in range(0, len(sorted_ids), 10):
                        row_ids = sorted_ids[i:i+10]
                        f.write(", ".join(row_ids) + "\n")
                
                # Add recommendations if there are issues
                if self.processing_errors or self.warnings or failed_list:
                    f.write("\n\n💡 RECOMMENDATIONS:\n")
                    f.write("-" * 30 + "\n")
                    if self.processing_errors:
                        f.write("• Review processing errors above for systematic issues\n")
                        f.write("• Check network connectivity for connection errors\n")
                        f.write("• Verify ERP credentials for authentication errors\n")
                    if self.warnings:
                        f.write("• Review warnings for data quality issues\n")
                        f.write("• Consider updating scraping logic for missing data\n")
                    if failed_list:
                        f.write("• Retry failed downloads with increased timeout\n")
                        f.write("• Check file format compatibility\n")
                        
            logger.info(f"Generated comprehensive processing report: {report_path}")
            return report_path
            
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return None
            
    def _sanitize_name(self, name: str) -> str:
        """Sanitize name for filename"""
        # Replace spaces with underscores
        name = name.replace(' ', '_')
        # Remove special characters
        name = ''.join(c for c in name if c.isalnum() or c in ('_', '-'))
        return name
        
    def _get_file_size_mb(self, file_path: Optional[Path]) -> Optional[float]:
        """Get file size in MB"""
        if file_path and file_path.exists():
            return file_path.stat().st_size / (1024 * 1024)
        return None
        
    def cleanup_orphaned_metadata(self, active_candidate_ids: List[str]):
        """
        Remove metadata files for candidates that no longer exist
        
        Args:
            active_candidate_ids: List of currently active candidate IDs
        """
        active_set = set(active_candidate_ids)
        removed_count = 0
        
        for json_file in self.metadata_dir.glob('*.meta.json'):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    candidate_id = data.get('candidate_id')
                    
                if candidate_id and candidate_id not in active_set:
                    json_file.unlink()
                    removed_count += 1
                    logger.info(f"Removed orphaned metadata for candidate {candidate_id}")
                    
            except Exception as e:
                logger.error(f"Error processing {json_file}: {e}")
                
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} orphaned metadata files") 