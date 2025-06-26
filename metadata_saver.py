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
            metadata_dir: Directory for individual metadata files
            results_dir: Directory for consolidated results
        """
        self.metadata_dir = metadata_dir
        self.results_dir = results_dir
        
        # Ensure directories exist
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Paths for consolidated files
        self.candidates_json_path = self.results_dir / 'candidates.json'
        self.candidates_csv_path = self.results_dir / 'candidates.csv'
        self.cases_json_path = self.results_dir / 'cases.json'
        self.cases_csv_path = self.results_dir / 'cases.csv'
        
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
            metadata_path = self.metadata_dir / metadata_filename
            
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
            
            # Use case naming pattern
            filename = f"{self._sanitize_name(company_name)}_{case_id}_{self._sanitize_name(job_title)}"
            metadata_filename = f"{filename}.case.meta.json"
            metadata_path = self.metadata_dir / metadata_filename
            
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
        Generate a download report
        
        Args:
            download_stats: Download statistics from PDFDownloader
            
        Returns:
            Path to report file
        """
        report_path = self.results_dir / f'download_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
        
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write("ERP Resume Download Report\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                f.write("Download Statistics:\n")
                f.write("-" * 30 + "\n")
                f.write(f"Total candidates: {download_stats.get('total', 0)}\n")
                f.write(f"Successful downloads: {download_stats.get('successful', 0)}\n")
                f.write(f"Failed downloads: {download_stats.get('failed', 0)}\n")
                f.write(f"Skipped (existing): {download_stats.get('skipped', 0)}\n")
                f.write(f"Success rate: {download_stats.get('success_rate', 0):.1f}%\n")
                f.write(f"Total size: {download_stats.get('total_size_mb', 0):.2f} MB\n")
                
                # Add successfully downloaded candidates list
                successful_list = download_stats.get('successful_candidates', [])
                if successful_list:
                    f.write("\n\nSuccessfully Downloaded Candidates:\n")
                    f.write("-" * 40 + "\n")
                    for i, candidate in enumerate(successful_list, 1):
                        candidate_id = candidate.get('candidate_id', 'N/A')
                        name = candidate.get('name', 'Unknown')
                        size_mb = candidate.get('file_size_mb', 0)
                        f.write(f"{i:3d}. ID: {candidate_id} | {name} | {size_mb:.2f} MB\n")
                
                # Add skipped candidates list
                skipped_list = download_stats.get('skipped_candidates', [])
                if skipped_list:
                    f.write("\n\nSkipped Candidates (Already Downloaded):\n")
                    f.write("-" * 40 + "\n")
                    for i, candidate in enumerate(skipped_list, 1):
                        candidate_id = candidate.get('candidate_id', 'N/A')
                        name = candidate.get('name', 'Unknown')
                        f.write(f"{i:3d}. ID: {candidate_id} | {name}\n")
                
                # Add failed candidates if available
                failed_list = download_stats.get('failed_candidates', [])
                if failed_list:
                    f.write("\n\nFailed Downloads:\n")
                    f.write("-" * 40 + "\n")
                    for i, candidate in enumerate(failed_list, 1):
                        candidate_id = candidate.get('candidate_id', 'N/A')
                        name = candidate.get('name', 'Unknown')
                        error = candidate.get('error', 'Unknown error')
                        f.write(f"{i:3d}. ID: {candidate_id} | {name} | Error: {error}\n")
                
                # Add summary by Candidate ID only
                all_candidate_ids = []
                all_candidate_ids.extend([c.get('candidate_id') for c in successful_list if c.get('candidate_id')])
                all_candidate_ids.extend([c.get('candidate_id') for c in skipped_list if c.get('candidate_id')])
                all_candidate_ids.extend([c.get('candidate_id') for c in failed_list if c.get('candidate_id')])
                
                if all_candidate_ids:
                    f.write(f"\n\nAll Processed Candidate IDs ({len(all_candidate_ids)} total):\n")
                    f.write("-" * 40 + "\n")
                    # Sort IDs numerically if possible
                    try:
                        sorted_ids = sorted(all_candidate_ids, key=lambda x: int(x) if x.isdigit() else float('inf'))
                    except:
                        sorted_ids = sorted(all_candidate_ids)
                    
                    # Print IDs in rows of 10
                    for i in range(0, len(sorted_ids), 10):
                        row_ids = sorted_ids[i:i+10]
                        f.write(", ".join(row_ids) + "\n")
                        
            logger.info(f"Generated download report: {report_path}")
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