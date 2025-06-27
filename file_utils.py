"""
File utilities module for managing directories and file operations
"""
import os
import re
from pathlib import Path
from typing import Tuple, Optional, Dict, List
import logging

logger = logging.getLogger(__name__)

# ID conversion constants
CANDIDATE_ID_OFFSET = 979174  # Real Candidate ID = URL ID + 979174
CASE_ID_OFFSET = 10000  # Real Case ID = URL ID + 10000 (패턴 발견!)

def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing or replacing invalid characters
    Support for bracket-based naming: [Type-ID] Name - Position.ext
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename safe for filesystem
    """
    # Keep brackets, hyphens, and spaces in specific positions
    # Only replace spaces within the main content (not between brackets and content)
    
    # Handle bracket pattern: [Type-ID] Content
    bracket_pattern = r'(\[[\w-]+\])\s*(.*)'
    match = re.match(bracket_pattern, filename)
    
    if match:
        bracket_part = match.group(1)  # [Type-ID] 
        content_part = match.group(2)  # Rest of the filename
        
        # Clean the content part while preserving meaningful separators
        # Replace multiple spaces with single space
        content_part = re.sub(r'\s+', ' ', content_part)
        
        # Remove or replace invalid characters (but keep hyphens and spaces)
        content_part = re.sub(r'[<>:"/\\|?*]', '', content_part)
        
        # Reconstruct filename
        filename = f"{bracket_part} {content_part}".strip()
    else:
        # Fallback to original logic for non-bracket filenames
        filename = filename.replace(' ', '_')
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        filename = re.sub(r'_+', '_', filename)
        filename = filename.strip('._')
    
    # Limit length (Windows has 255 char limit)
    if len(filename) > 200:
        filename = filename[:200]
        
    return filename


def generate_resume_filename(name: str, candidate_id: str, extension: str = 'pdf') -> str:
    """
    Generate resume filename using bracket format: [Resume-ID] Name.ext
    
    Args:
        name: Candidate name
        candidate_id: Real candidate ID 
        extension: File extension (pdf, doc, docx)
        
    Returns:
        Formatted filename
    """
    # Clean name
    clean_name = name.strip()
    
    # Generate filename
    filename = f"[Resume-{candidate_id}] {clean_name}.{extension}"
    
    # Sanitize for filesystem
    filename = sanitize_filename(filename)
    
    # If filename is too long, truncate name part
    if len(filename) > 200:
        max_name_length = 200 - len(f"[Resume-{candidate_id}] .{extension}")
        if max_name_length > 10:
            truncated_name = clean_name[:max_name_length].strip()
            filename = f"[Resume-{candidate_id}] {truncated_name}.{extension}"
        else:
            # Fallback for very long IDs
            filename = f"[Resume-{candidate_id}].{extension}"
            
    return filename


def generate_case_filename(company_name: str, job_title: str, case_id: str, extension: str = 'json') -> str:
    """
    Generate case filename using bracket format: [Case-ID] Company - Position.ext
    
    Args:
        company_name: Company name
        job_title: Job title/position  
        case_id: Case ID
        extension: File extension (json, txt)
        
    Returns:
        Formatted filename
    """
    # Clean inputs
    clean_company = company_name.strip()
    clean_title = job_title.strip()
    
    # Generate filename
    filename = f"[Case-{case_id}] {clean_company} - {clean_title}.{extension}"
    
    # Sanitize for filesystem  
    filename = sanitize_filename(filename)
    
    # If filename is too long, truncate
    if len(filename) > 200:
        # Calculate available space for company and title
        prefix_suffix_length = len(f"[Case-{case_id}]  - .{extension}")
        available_length = 200 - prefix_suffix_length
        
        # Split available space between company and title
        company_length = min(len(clean_company), available_length // 2)
        title_length = available_length - company_length - 3  # 3 for " - "
        
        if title_length > 10 and company_length > 10:
            truncated_company = clean_company[:company_length].strip()
            truncated_title = clean_title[:title_length].strip()
            filename = f"[Case-{case_id}] {truncated_company} - {truncated_title}.{extension}"
        else:
            # Fallback for very long IDs
            filename = f"[Case-{case_id}].{extension}"
            
    return filename


def generate_metadata_filename(base_filename: str, file_type: str = 'meta') -> str:
    """
    Generate metadata filename from base filename
    
    Args:
        base_filename: Base filename (e.g., "[Resume-123] John Doe.pdf")
        file_type: Type of metadata ('meta', 'report')
        
    Returns:
        Metadata filename (e.g., "[Resume-123] John Doe.meta.json")
    """
    # Remove extension from base filename
    if '.' in base_filename:
        base_name = base_filename.rsplit('.', 1)[0]
    else:
        base_name = base_filename
        
    return f"{base_name}.{file_type}.json"


def generate_unique_filename(base_path: Path, filename: str) -> str:
    """
    Generate a unique filename if the file already exists
    
    Args:
        base_path: Directory path
        filename: Desired filename
        
    Returns:
        Unique filename (may have _1, _2, etc. suffix)
    """
    if not (base_path / filename).exists():
        return filename
        
    # Split filename and extension
    name_parts = filename.rsplit('.', 1)
    if len(name_parts) == 2:
        base_name, extension = name_parts
    else:
        base_name = filename
        extension = ''
        
    # Try adding numbers until we find a unique name
    counter = 1
    while True:
        new_filename = f"{base_name}_{counter}"
        if extension:
            new_filename = f"{new_filename}.{extension}"
            
        if not (base_path / new_filename).exists():
            return new_filename
            
        counter += 1
        if counter > 100:  # Safety limit
            raise ValueError(f"Could not generate unique filename for {filename}")


def create_directory_structure(base_path: Path, year: str, month: str) -> Path:
    """
    Create directory structure for resume storage
    
    Args:
        base_path: Base directory path (e.g., resumes/)
        year: Year string (e.g., '2025')
        month: Month string (e.g., '01')
        
    Returns:
        Full path to the created directory
    """
    full_path = base_path / year / month
    full_path.mkdir(parents=True, exist_ok=True)
    
    logger.debug(f"Created directory structure: {full_path}")
    return full_path


def extract_date_parts(date_string: str) -> Tuple[str, str]:
    """
    Extract year and month from date string
    
    Args:
        date_string: Date in format YYYY-MM-DD or similar
        
    Returns:
        Tuple of (year, month) as strings
    """
    try:
        # Try to extract YYYY-MM pattern
        match = re.match(r'(\d{4})-(\d{2})', date_string)
        if match:
            year, month = match.groups()
            return year, month
    except Exception as e:
        logger.warning(f"Could not extract date from {date_string}: {e}")
        
    # Fallback to current date
    from datetime import datetime
    now = datetime.now()
    return str(now.year), f"{now.month:02d}"


def generate_filename_from_template(
    template: str, 
    name: str, 
    candidate_id: str,
    url_id: str = None,
    **kwargs
) -> str:
    """
    Generate filename from template with candidate information
    
    Args:
        template: Filename template (e.g., '{name}_{id}_resume')
        name: Candidate name
        candidate_id: Real candidate ID (e.g., 1044760)
        url_id: URL ID (e.g., 65586) - optional
        **kwargs: Additional template variables
        
    Returns:
        Safe filename string
    """
    # Clean name for filename
    safe_name = sanitize_filename(name)
    
    # Prepare template variables
    template_vars = {
        'name': safe_name,
        'id': candidate_id,  # Use real candidate ID
        'candidate_id': candidate_id,
        'url_id': url_id or candidate_id,  # Fallback to candidate_id if no url_id
        **kwargs
    }
    
    try:
        # Apply template
        filename = template.format(**template_vars)
        
        # Ensure it ends with .pdf
        if not filename.lower().endswith('.pdf'):
            filename += '.pdf'
            
        # Final sanitization
        filename = sanitize_filename(filename)
        
        # If filename is too long, truncate
        if len(filename) > 200:
            name_part = safe_name[:50]
            filename = f"{name_part}_{candidate_id}_resume.pdf"
            
        return filename
        
    except KeyError as e:
        logger.warning(f"Template variable missing: {e}, using fallback")
        # Fallback to simple format
        return f"{safe_name}_{candidate_id}_resume.pdf"


def ensure_file_permissions(file_path: Path):
    """
    Ensure file has appropriate permissions
    
    Args:
        file_path: Path to file
    """
    try:
        # Make file readable and writable by owner
        os.chmod(file_path, 0o644)
    except Exception as e:
        logger.warning(f"Could not set file permissions for {file_path}: {e}")


def get_file_size_mb(file_path: Path) -> float:
    """
    Get file size in megabytes
    
    Args:
        file_path: Path to file
        
    Returns:
        File size in MB
    """
    try:
        size_bytes = file_path.stat().st_size
        return size_bytes / (1024 * 1024)
    except Exception:
        return 0.0


def cleanup_empty_directories(base_path: Path):
    """
    Remove empty directories in the tree
    
    Args:
        base_path: Base directory to clean
    """
    try:
        for dirpath, dirnames, filenames in os.walk(base_path, topdown=False):
            if not dirnames and not filenames:
                Path(dirpath).rmdir()
                logger.debug(f"Removed empty directory: {dirpath}")
    except Exception as e:
        logger.error(f"Error during directory cleanup: {e}")


def validate_pdf_file(file_path: Path) -> bool:
    """
    Basic validation to check if file is likely a PDF
    
    Args:
        file_path: Path to file
        
    Returns:
        True if file appears to be a valid PDF
    """
    try:
        # Check file exists and has content
        if not file_path.exists() or file_path.stat().st_size == 0:
            return False
            
        # Check PDF header
        with open(file_path, 'rb') as f:
            header = f.read(4)
            return header == b'%PDF'
            
    except Exception as e:
        logger.error(f"Error validating PDF {file_path}: {e}")
        return False


def predict_real_candidate_id(url_id: int) -> int:
    """
    Predict real candidate ID from URL ID using discovered pattern
    
    Args:
        url_id: URL ID (e.g., 65586)
        
    Returns:
        Predicted real candidate ID (e.g., 1044760)
    """
    return url_id + CANDIDATE_ID_OFFSET


def predict_url_candidate_id(real_id: int) -> int:
    """
    Predict URL candidate ID from real ID using discovered pattern
    
    Args:
        real_id: Real candidate ID (e.g., 1044760)
        
    Returns:
        Predicted URL ID (e.g., 65586)
    """
    return real_id - CANDIDATE_ID_OFFSET


def verify_candidate_id_pattern(url_id: int, extracted_real_id: int) -> bool:
    """
    Verify if extracted real ID matches the expected pattern
    
    Args:
        url_id: URL ID
        extracted_real_id: Real ID extracted from HTML
        
    Returns:
        True if IDs match expected pattern (allowing small variance)
    """
    predicted_id = predict_real_candidate_id(url_id)
    return abs(extracted_real_id - predicted_id) <= 1  # Allow small variance


def convert_candidate_id(id_value: str, id_type: str = 'auto') -> Dict[str, int]:
    """
    Convert between URL ID and Real ID for candidates
    
    Args:
        id_value: ID value as string
        id_type: 'url', 'real', or 'auto' to detect automatically
        
    Returns:
        Dictionary with both 'url_id' and 'real_id'
    """
    try:
        id_num = int(id_value)
        
        if id_type == 'auto':
            # Auto-detect based on typical ranges
            # URL IDs are typically in 60000-70000 range
            # Real IDs are typically in 1040000+ range
            if 60000 <= id_num <= 70000:
                id_type = 'url'
            elif id_num >= 1000000:
                id_type = 'real'
            else:
                # Ambiguous range, assume URL ID by default
                id_type = 'url'
                logger.warning(f"Ambiguous ID range for {id_num}, assuming URL ID")
        
        if id_type == 'url':
            return {
                'url_id': id_num,
                'real_id': predict_real_candidate_id(id_num)
            }
        else:  # real
            return {
                'url_id': predict_url_candidate_id(id_num),
                'real_id': id_num
            }
            
    except ValueError:
        logger.error(f"Invalid ID value: {id_value}")
        raise ValueError(f"Invalid ID value: {id_value}")


def predict_real_case_id(url_id: int) -> int:
    """
    Predict real Case ID from URL ID using discovered pattern
    
    Args:
        url_id: URL ID (e.g., 3897)
        
    Returns:
        Predicted real Case ID (e.g., 13897)
    """
    return url_id + CASE_ID_OFFSET


def predict_url_case_id(real_id: int) -> int:
    """
    Predict URL Case ID from real ID using discovered pattern
    
    Args:
        real_id: Real Case ID (e.g., 13897)
        
    Returns:
        Predicted URL ID (e.g., 3897)
    """
    return real_id - CASE_ID_OFFSET


def verify_case_id_pattern(url_id: int, extracted_real_id: int) -> bool:
    """
    Verify if extracted real Case ID matches the expected pattern
    
    Args:
        url_id: URL ID
        extracted_real_id: Real Case ID extracted from HTML
        
    Returns:
        True if IDs match expected pattern (allowing small variance)
    """
    predicted_id = predict_real_case_id(url_id)
    return abs(extracted_real_id - predicted_id) <= 1  # Allow small variance


# Case ID conversion (pattern discovered!)
def convert_case_id(id_value: str, id_type: str = 'auto') -> Dict[str, str]:
    """
    Convert between URL ID and Real ID for cases
    Uses discovered pattern: Real ID = URL ID + 10,000
    
    Args:
        id_value: Case ID value as string
        id_type: 'url', 'real', or 'auto' to detect automatically
        
    Returns:
        Dictionary with both 'url_id' and 'real_id'
    """
    try:
        id_num = int(id_value)
        
        if id_type == 'auto':
            # Auto-detect based on typical ranges
            # URL IDs are typically in 3000-4000 range for cases
            # Real IDs are typically in 13000-14000 range for cases
            if 3000 <= id_num <= 5000:
                id_type = 'url'
            elif id_num >= 10000:
                id_type = 'real'
            else:
                # Ambiguous range, assume URL ID by default
                id_type = 'url'
                logger.warning(f"Ambiguous Case ID range for {id_num}, assuming URL ID")
        
        if id_type == 'url':
            return {
                'url_id': str(id_num),
                'real_id': str(predict_real_case_id(id_num))
            }
        else:  # real
            return {
                'url_id': str(predict_url_case_id(id_num)),
                'real_id': str(id_num)
            }
            
    except ValueError:
        logger.error(f"Invalid Case ID value: {id_value}")
        raise ValueError(f"Invalid Case ID value: {id_value}")


def parse_candidate_id_range(id_range: str, id_type: str = 'url') -> List[int]:
    """
    Parse Candidate ID range string and convert to list of IDs
    
    Args:
        id_range: Range specification like "65585-65580" or "1044759-1044754"
        id_type: 'url' or 'real' - type of IDs in the range
        
    Returns:
        List of IDs (always returns URL IDs for compatibility)
    """
    ids = []
    
    if '-' in id_range:
        # Range format: "65585-65580" or "1044759-1044754"
        try:
            parts = id_range.split('-')
            if len(parts) == 2:
                start_id = int(parts[0])
                end_id = int(parts[1])
                
                # Ensure we go from high to low or low to high
                if start_id > end_id:
                    ids = list(range(start_id, end_id - 1, -1))  # Descending
                else:
                    ids = list(range(start_id, end_id + 1))  # Ascending
            else:
                raise ValueError("Invalid range format")
        except ValueError:
            raise ValueError(f"Invalid Candidate range format: {id_range}")
            
    elif ',' in id_range:
        # Comma-separated format: "65580,65581,65582" or "1044754,1044755,1044756"
        try:
            ids = [int(id_str.strip()) for id_str in id_range.split(',')]
        except ValueError:
            raise ValueError(f"Invalid comma-separated Candidate format: {id_range}")
    else:
        raise ValueError(f"Invalid Candidate ID range format: {id_range}")
    
    # Convert to URL IDs if input was real IDs
    if id_type == 'real':
        ids = [predict_url_candidate_id(real_id) for real_id in ids]
    
    return ids


# Legacy alias for backward compatibility
parse_id_range = parse_candidate_id_range


def collect_case_id_mappings(url_id: str, actual_case_id: str) -> None:
    """
    Collect Case ID mappings for pattern analysis
    This function should be called whenever we discover a URL ID -> Real Case ID mapping
    
    Args:
        url_id: URL ID used in case page URL
        actual_case_id: Real Case ID extracted from HTML
    """
    try:
        # Convert to integers for analysis
        url_id_num = int(url_id)
        actual_case_id_num = int(actual_case_id)
        
        # Calculate difference
        difference = actual_case_id_num - url_id_num
        
        # Log the mapping for pattern analysis
        logger.info(f"CASE ID MAPPING: URL {url_id} → Real {actual_case_id} (차이: {difference})")
        
        # Could store in a file for later analysis
        # For now, just log it
        
    except ValueError:
        logger.warning(f"Non-numeric Case IDs: URL {url_id}, Real {actual_case_id}")


def analyze_case_id_pattern(mappings: List[Tuple[int, int]]) -> Optional[int]:
    """
    Analyze collected Case ID mappings to find pattern
    
    Args:
        mappings: List of (url_id, real_id) tuples
        
    Returns:
        Offset value if consistent pattern found, None otherwise
    """
    if not mappings:
        return None
        
    differences = [real_id - url_id for url_id, real_id in mappings]
    
    # Check if all differences are the same
    if len(set(differences)) == 1:
        offset = differences[0]
        logger.info(f"Case ID pattern found: Real ID = URL ID + {offset}")
        return offset
    else:
        logger.warning(f"Inconsistent Case ID pattern: differences = {differences}")
        return None


def predict_case_id_if_pattern_exists(url_id: int, known_offset: Optional[int] = None) -> Optional[int]:
    """
    Predict real Case ID if pattern is known
    
    Args:
        url_id: URL ID
        known_offset: Known offset if pattern discovered
        
    Returns:
        Predicted real Case ID or None if no pattern
    """
    if known_offset is not None:
        return url_id + known_offset
    return None


def parse_case_id_range(id_range: str, id_type: str = 'url') -> List[int]:
    """
    Parse Case ID range string and convert to list of IDs
    
    Args:
        id_range: Range specification like "3897-3890" or "13897-13890"
        id_type: 'url' or 'real' - type of IDs in the range
        
    Returns:
        List of IDs (always returns URL IDs for compatibility)
    """
    ids = []
    
    if '-' in id_range:
        # Range format: "3897-3890" or "13897-13890"
        try:
            parts = id_range.split('-')
            if len(parts) == 2:
                start_id = int(parts[0])
                end_id = int(parts[1])
                
                # Ensure we go from high to low or low to high
                if start_id > end_id:
                    ids = list(range(start_id, end_id - 1, -1))  # Descending
                else:
                    ids = list(range(start_id, end_id + 1))  # Ascending
            else:
                raise ValueError("Invalid range format")
        except ValueError:
            raise ValueError(f"Invalid Case range format: {id_range}")
            
    elif ',' in id_range:
        # Comma-separated format: "3897,3896,3895" or "13897,13896,13895"
        try:
            ids = [int(id_str.strip()) for id_str in id_range.split(',')]
        except ValueError:
            raise ValueError(f"Invalid comma-separated Case format: {id_range}")
    else:
        raise ValueError(f"Invalid Case ID range format: {id_range}")
    
    # Convert to URL IDs if input was real IDs
    if id_type == 'real':
        ids = [predict_url_case_id(real_id) for real_id in ids]
    
    return ids 