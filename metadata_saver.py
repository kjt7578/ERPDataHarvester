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
            
    def save_consolidated_results(self, all_candidates: List[Dict[str, Any]]) -> bool:
        """
        Save all candidate data to consolidated JSON and CSV files
        
        Args:
            all_candidates: List of all candidate information
            
        Returns:
            True if successful
        """
        try:
            # Add summary statistics
            summary = {
                'total_candidates': len(all_candidates),
                'last_updated': datetime.now().isoformat(),
                'candidates': all_candidates
            }
            
            # Save to JSON
            with open(self.candidates_json_path, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
                
            logger.info(f"Saved {len(all_candidates)} candidates to {self.candidates_json_path}")
            
            # Save to CSV
            if all_candidates:
                self._save_to_csv(all_candidates)
                
            return True
            
        except Exception as e:
            logger.error(f"Error saving consolidated results: {e}")
            return False
            
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
                
                # Add failed candidates if available
                failed_list = download_stats.get('failed_candidates', [])
                if failed_list:
                    f.write("\n\nFailed Downloads:\n")
                    f.write("-" * 30 + "\n")
                    for candidate in failed_list:
                        f.write(f"- {candidate.get('name', 'Unknown')} (ID: {candidate.get('candidate_id', 'N/A')})\n")
                        
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