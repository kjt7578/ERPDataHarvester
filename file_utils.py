"""
File utilities module for managing directories and file operations
"""
import os
import re
from pathlib import Path
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing or replacing invalid characters
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename safe for filesystem
    """
    # Replace spaces with underscores
    filename = filename.replace(' ', '_')
    
    # Remove or replace invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    
    # Remove multiple underscores
    filename = re.sub(r'_+', '_', filename)
    
    # Remove leading/trailing underscores and dots
    filename = filename.strip('._')
    
    # Limit length (Windows has 255 char limit)
    if len(filename) > 200:
        filename = filename[:200]
        
    return filename


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